"""
Models 2 and 3, run live beside Model 1 for 2026-27.

  Model 1  team-strength mixed model + injury reports (nba_mixed_model.py; drives the phone alerts)
  Model 2  player-based team strength: projected lineups from the injury report x last season's EPM,
           plus player and team deviations learned this season (models_v2.PlayerModel, lineups.py)
  Model 3  pace x efficiency, with referee crews (models_v2.PaceModel)

All three were fit on 2021-22..2025-26. Models 2 and 3 load their fitted settings from
data/models_v2_params.json (made by fit_live_params.py) and only walk forward through 2026-27, so no refit
is needed each run. Like Model 1, each game is predicted from the night-before (8 PM) injury report and
earlier results only, and the prediction is LOCKED the first time it's made. Referee crews aren't known
the night before, so they're not used for the locked number.

Outputs:  state/picks_log_models.csv  one row per game per model, locked, then graded at the opening and
          closing lines (same lines and rules as picks_log.csv); and a "Model Comparison" sheet in
          NBA_Live_Tracker.xlsx.
"""
import os, json
import numpy as np, pandas as pd

import models_v2 as mv
from lineups import prepare_box, LineupBuilder
from build_report_features import key
from nba_mixed_model import add_rest

EDGES = (3.0, 4.0, 5.0)


def _season_inputs(W, games, raw, reports_path, season):
    """games: tracker schedule (game_id, date, home, away, home_pts, away_pts, *_miss_* features).
    raw: dict of Kaggle frames for this season: players (PlayerStatistics), teams (TeamStatistics), games (Games)."""
    codes = pd.read_csv(os.path.join(W, "data", "team_codes.csv"), index_col=0).code.to_dict()
    code2tid = {c: int(t) for t, c in codes.items()}
    G = games.copy().reset_index(drop=True)
    G["season"] = season
    # ---- possessions and game length for finished games
    T = raw["teams"].copy()
    T["poss"] = T.fieldGoalsAttempted - T.reboundsOffensive + T.turnovers + 0.44 * T.freeThrowsAttempted
    T = T.set_index(["gameId", "teamId"])
    tid_h = G.home.map(code2tid); tid_a = G.away.map(code2tid)
    ph = [T.poss.get((g, t), np.nan) for g, t in zip(G.game_id, tid_h)]
    pa = [T.poss.get((g, t), np.nan) for g, t in zip(G.game_id, tid_a)]
    gm = [T.numMinutes.get((g, t), np.nan) for g, t in zip(G.game_id, tid_h)]
    gmin = pd.to_numeric(pd.Series(gm), errors="coerce")
    G["game_min"] = gmin.where(gmin >= 240, 240.0).values      # a few stat lines lack minutes: assume regulation
    pace = (np.array(ph, float) + np.array(pa, float)) / 2 * 240 / G.game_min
    G["pace48"] = np.where(pace > 50, pace, np.nan)             # incomplete stat lines -> skipped by the model
    # ---- referee crews (finished games)
    offs = raw["games"].set_index("gameId").officials if "officials" in raw["games"] else pd.Series(dtype=str)
    G["officials"] = [("|".join(x.strip() for x in str(offs.get(g, "")).split(",") if x.strip())
                       if isinstance(offs.get(g, None), str) else "") for g in G.game_id]
    G = add_rest(G)
    G["lu_key"] = G.index
    # ---- projected lineups
    rep = pd.read_csv(reports_path)
    P = raw["players"].copy()
    box = prepare_box(P, rep, code2tid)
    epm = pd.read_csv(os.path.join(W, "data", "player_epm_2025_26.csv")).sort_values("game_dt").groupby(["nba_player_id", "season"]).tail(1)
    rating = {(int(r.nba_player_id), int(r.season)): (r.epm_off, r.epm_def) for r in epm.itertuples()}
    lm = pd.read_csv(os.path.join(W, "data", "last_season_minutes_2025_26.csv"))
    last_mpg = {(int(p), season - 1): m for p, m in zip(lm.personId, lm.mpg)}
    p_miss = pd.read_csv(os.path.join(W, "data", "p_miss.csv"), index_col=0).iloc[:, 0].dropna().to_dict()
    p_miss = {k: v for k, v in p_miss.items() if isinstance(k, str)}
    LB = LineupBuilder(box, rep, rating, p_miss, code2tid, extra_last_mpg=last_mpg)
    for k, p in zip(lm.name, lm.personId):            # last season's names, for players who haven't played yet
        if isinstance(k, str): LB.ids_any.setdefault(k, int(p))
    lu = LB.build(G)
    return G, lu


def predict(W, games, raw, reports_path, season, target):
    """open-line predictions (night-before report, no referees) for every game through `target`,
    each made from earlier games only."""
    params = json.load(open(os.path.join(W, "data", "models_v2_params.json")))
    G, lu = _season_inputs(W, games, raw, reports_path, season)
    out = []
    for mid in ("2", "3"):
        M = mv.import_params(params[mid], G, lu)
        hl = params[mid]["half_life"]
        P = M.walk(season, None if hl in (None, "None") else int(hl), "open", use_refs=False)
        P["model"] = mid
        out.append(P[["game_id", "date", "home", "away", "model", "pred_margin", "pred_total"]])
    return pd.concat(out, ignore_index=True)


def lock_and_grade(W, state, preds, model1_log, now, target, say=print):
    """lock new model 2/3 predictions (plus a copy of Model 1's locked numbers), then grade all three
    at the opening and closing lines already pulled into picks_log.csv."""
    path = os.path.join(state, "picks_log_models.csv")
    L = pd.read_csv(path, parse_dates=["date", "locked_at_et"]) if os.path.exists(path) else pd.DataFrame()
    have = set(zip(L.game_id, L.model.astype(str))) if len(L) else set()
    m1 = model1_log[["game_id", "date", "home", "away", "pick_type", "locked_at_et", "pred_margin", "pred_total"]].copy()
    m1["model"] = "1"
    tips = model1_log.set_index("game_id").tip_et
    new2 = preds.copy()
    new2["pick_type"] = np.where((pd.to_datetime(new2.date) == target) & (new2.game_id.map(tips) > now), "live", "backfilled")
    new2["locked_at_et"] = now
    finished = set(model1_log.game_id[model1_log.home_pts.notna()]) if "home_pts" in model1_log else set()
    new2 = new2[(new2.pick_type == "live") | new2.game_id.isin(finished)]       # never lock an unfinished past game
    new = pd.concat([m1, new2], ignore_index=True)
    new["model"] = new.model.astype(str)
    new = new[[(g, m) not in have for g, m in zip(new.game_id, new.model)]]
    new = new[new.game_id.isin(set(model1_log.game_id))]
    keep = ["game_id", "date", "home", "away", "model", "pick_type", "locked_at_et", "pred_margin", "pred_total"]
    L = pd.concat([L[keep], new[keep]], ignore_index=True) if len(L) else new[keep]
    say(f"Model comparison: locked {int(((new.model != '1') & (new.pick_type == 'live')).sum())} live and "
        f"{int(((new.model != '1') & (new.pick_type == 'backfilled')).sum())} backfilled Model 2/3 predictions.")
    # ---- grade with the same lines as Model 1
    lines = model1_log.set_index("game_id")
    for c in ("home_pts", "away_pts", "open_spread", "open_total", "close_spread", "close_total"):
        L[c] = L.game_id.map(lines[c]) if c in lines else np.nan
    m = L.home_pts - L.away_pts; t = L.home_pts + L.away_pts
    for line in ("open", "close"):
        for mk, pred, truth in (("spread", "pred_margin", m), ("total", "pred_total", t)):
            ln = L[f"{line}_{mk}"]
            e = (L[pred] + ln) if mk == "spread" else (L[pred] - ln)
            v = (truth + ln) * np.sign(e) if mk == "spread" else (truth - ln) * np.sign(e)
            L[f"{line}_{mk}_edge"] = e.abs().round(2)
            L[f"{line}_{mk}_bet"] = np.where(e.isna(), None, np.where(e > 0, "home" if mk == "spread" else "over",
                                                                     "away" if mk == "spread" else "under"))
            L[f"{line}_{mk}_result"] = np.select([truth.isna() | e.isna(), v > 0, v < 0], [None, "W", "L"], "P")
    L.sort_values(["date", "game_id", "model"]).to_csv(path, index=False)
    return L


def summary_table(L):
    rows = []
    for mdl in ("1", "2", "3"):
        x = L[L.model == mdl]
        done = x[x.home_pts.notna()]
        rec = {"Model": {"1": "1 - team strength", "2": "2 - player-based", "3": "3 - pace x efficiency"}[mdl],
               "Games graded": len(done),
               "Margin error (avg pts)": round((done.pred_margin - (done.home_pts - done.away_pts)).abs().mean(), 2) if len(done) else None,
               "Total error (avg pts)": round((done.pred_total - (done.home_pts + done.away_pts)).abs().mean(), 2) if len(done) else None}
        for line in ("open", "close"):
            for mk in ("spread", "total"):
                for ed in EDGES:
                    s = done[done[f"{line}_{mk}_edge"] >= ed]
                    w, l = int((s[f"{line}_{mk}_result"] == "W").sum()), int((s[f"{line}_{mk}_result"] == "L").sum())
                    rec[f"{line.title()} {mk} {ed:.0f}+ W-L"] = f"{w}-{l}"
                    rec[f"{line.title()} {mk} {ed:.0f}+ win %"] = round(w / (w + l), 3) if w + l else None
        rows.append(rec)
    return pd.DataFrame(rows)


def add_sheet(xlsx, L):
    """add the Model Comparison sheet to the tracker workbook"""
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = load_workbook(xlsx)
    if "Model Comparison" in wb.sheetnames: del wb["Model Comparison"]
    ws = wb.create_sheet("Model Comparison", 2)
    bold = Font(bold=True); hdr = PatternFill("solid", fgColor="1F3864"); white = Font(bold=True, color="FFFFFF")
    ws["A1"] = "Three models, same games, same lines (2026-27)"; ws["A1"].font = Font(bold=True, size=14)
    notes = [
        "Model 1: team offense/defense strength + injury reports (drives the phone alerts).",
        "Model 2: builds each team from its players: projected minutes from the injury report x last season's EPM, plus what each player shows this season.",
        "Model 3: predicts possessions (pace) and points per possession separately, then multiplies; also learns referee crews (not used for the locked number, since crews are announced the morning of the game).",
        "Every number is locked from the night-before injury report, before most opening lines. 'Backfilled' rows were made after the fact for games before Models 2 and 3 went live, from earlier data only.",
        "Break-even at -110 is 52.4%. Wait for about 150 bets per model and market before reading anything into the win rates.",
    ]
    for i, n in enumerate(notes):
        ws.cell(row=2 + i, column=1, value=n).alignment = Alignment(wrap_text=False)
    S = summary_table(L)
    r0 = 2 + len(notes) + 1
    for j, c in enumerate(S.columns, 1):
        cell = ws.cell(row=r0, column=j, value=c); cell.font = white; cell.fill = hdr
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for i, rec in enumerate(S.itertuples(index=False), 1):
        for j, v in enumerate(rec, 1):
            ws.cell(row=r0 + i, column=j, value=v)
    ws.row_dimensions[r0].height = 45
    ws.column_dimensions["A"].width = 24
    for j in range(2, len(S.columns) + 1):
        ws.column_dimensions[ws.cell(row=r0, column=j).column_letter].width = 11
    # backtest reference
    b0 = r0 + len(S) + 2
    ws.cell(row=b0, column=1, value="Backtest reference (opening lines, edge 3+): win % in 2025-26 test / 2024-25 check").font = bold
    ref = [("Model 1", "52.4% / 54.3%", "55.9% / 53.5%"), ("Model 2", "52.8% / 60.6%", "54.1% / 54.7%"),
           ("Model 3", "51.3% / 53.7%", "56.6% / 56.0%")]
    ws.cell(row=b0 + 1, column=1, value="Model").font = bold
    ws.cell(row=b0 + 1, column=2, value="Spread").font = bold
    ws.cell(row=b0 + 1, column=3, value="Total").font = bold
    for i, (a, b, c) in enumerate(ref, 2):
        ws.cell(row=b0 + i, column=1, value=a); ws.cell(row=b0 + i, column=2, value=b); ws.cell(row=b0 + i, column=3, value=c)
    # per-game rows
    g0 = b0 + len(ref) + 3
    ws.cell(row=g0, column=1, value="Every locked prediction").font = bold
    cols = ["date", "home", "away", "model", "pick_type", "pred_margin", "pred_total", "open_spread", "open_total",
            "close_spread", "close_total", "home_pts", "away_pts", "open_spread_bet", "open_spread_edge", "open_spread_result",
            "open_total_bet", "open_total_edge", "open_total_result"]
    D = L.sort_values(["date", "game_id", "model"], ascending=[False, True, True])[cols]
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=g0 + 1, column=j, value=c); cell.font = white; cell.fill = hdr
    for i, rec in enumerate(D.itertuples(index=False), 2):
        for j, v in enumerate(rec, 1):
            if isinstance(v, float) and np.isnan(v): v = None
            if isinstance(v, pd.Timestamp): v = v.date()
            if isinstance(v, float): v = round(v, 1)
            ws.cell(row=g0 + i, column=j, value=v)
    wb.save(xlsx)
