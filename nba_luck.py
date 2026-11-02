"""
NBA shooting luck for the live totals (adopted Nov 1, 2026; see analysis/FINDINGS.md "Predicting the closing line").

Shot quality: chance each field-goal attempt goes in, from distance, corner/deep three, quarter, late clock and ESPN's shot
type (logistic regression on 2021-22 to 2025-26, data/shot_quality_model.json). A team-game's "luck" = actual FG points -
expected FG points. For each team, season to date: its own luck, and the luck of the teams it played ("luck allowed").
In the backtests the model total minus LUCK_WEIGHT x (both teams' luck + luck allowed, minus the league's average luck so
far) was better at the opener in both 2024-25 and 2025-26. alert.py applies it once both teams have MIN_GAMES games.

  python nba_luck.py WORKDIR          download shots for finished games of this season, write state/nba_luck.json
  python nba_luck.py WORKDIR --fit    refit the shot-quality model from data/nba_shots_hist.csv.gz
"""
import os, sys, json, glob
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
from scipy.optimize import minimize

W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.getcwd()
sys.path.insert(0, W)
STATE = os.path.join(W, "state")
MODEL = os.path.join(W, "data", "shot_quality_model.json")
SHOTS = os.path.join(STATE, "nba_shots_2026_27.csv.gz")
OUT = os.path.join(STATE, "nba_luck.json")
SEASON_START = "2026-10-01"
LUCK_WEIGHT = 0.5
MIN_GAMES = 5
# recent form (adopted Nov 2, 2026; analysis/form_adjust.py): a team's last 10 games minus its season-to-date average.
# Weights fit on 2023-24..2025-26 Model 1 predictions; out-of-season tests improved totals in all three seasons (+35.8u).
FORM_GAMES, FORM_MIN = 10, 10
FORM_W_TOTAL = 0.20       # pts added to the model total per pt of (home + away) recent game-total form
FORM_W_SPREAD = 0.11      # pts added to the home margin per pt of (home - away) recent margin form (spreads are test-only)
FLAGS = {"dunk": "dunk", "layup": "layup|finger roll", "hook": "hook", "pullup": "pullup", "stepback": "step back",
         "fade": "fade|turnaround", "float": "float", "driving": "driving", "cutting": "cutting", "running": "running",
         "putback": "putback|tip", "alleyoop": "alley oop", "heave": "heave", "bank": "bank"}


def prep(S):
    S = S.copy()
    S["value"] = np.where(S.value.fillna(0) > 0, S.value, np.where(S.text.fillna("").str.contains("three point", case=False), 3, 2))
    S["d"] = S.dist.fillna(np.hypot(S.x - 25, S.y - 5.25)).clip(0, 60)
    return S


def design(D):
    d = D.d.values; is3 = (D.value == 3).values
    cols = [np.ones(len(D)), d / 10, (d / 10) ** 2, np.log1p(d), is3.astype(float),
            (is3 & (D.y.fillna(99).values <= 14)).astype(float), (is3 & (d >= 28)).astype(float),
            (D.period.values >= 4).astype(float), (D.sec_left.fillna(99).values <= 4).astype(float)]
    s_ = D.shot_type.fillna("").str.lower()
    cols += [s_.str.contains(p).values.astype(float) for p in FLAGS.values()]
    return np.column_stack(cols)


def fit():
    S = prep(pd.read_csv(os.path.join(W, "data", "nba_shots_hist.csv.gz")))
    X, y = design(S), S.made.values.astype(float)
    def f(b):
        z = X @ b; p = 1 / (1 + np.exp(-z))
        return -(y * z - np.logaddexp(0, z)).sum() + 1e-3 * b @ b, -(X.T @ (y - p)) + 2e-3 * b
    b = minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B").x
    json.dump(dict(coef=b.tolist(), shots=int(len(S)), seasons=sorted(int(s) for s in S.season.unique())), open(MODEL, "w"))
    print(f"shot-quality model fit on {len(S)} shots")


def recent_form():
    """per team: last FORM_GAMES games' average game total and margin, minus its season-to-date average (finished games)"""
    p = os.path.join(STATE, "picks_log.csv")
    if not os.path.exists(p): return {}
    G = pd.read_csv(p).dropna(subset=["home_pts", "away_pts"]).drop_duplicates("game_id")
    G = G[G.date >= SEASON_START]
    rows = []
    for r in G.itertuples():
        rows += [dict(team=r.home, date=r.date, tp=r.home_pts + r.away_pts, mg=r.home_pts - r.away_pts),
                 dict(team=r.away, date=r.date, tp=r.home_pts + r.away_pts, mg=r.away_pts - r.home_pts)]
    if not rows: return {}
    L = pd.DataFrame(rows).sort_values("date"); out = {}
    for t, g in L.groupby("team"):
        n = len(g)
        out[t] = dict(form_games=n, form_total=round(float(g.tp.tail(FORM_GAMES).mean() - g.tp.mean()), 3),
                      form_margin=round(float(g.mg.tail(FORM_GAMES).mean() - g.mg.mean()), 3))
    return out


def main():
    if "--fit" in sys.argv or not os.path.exists(MODEL): fit()
    import nba_shots
    files = [f for f in glob.glob(os.path.join(W, "research", "minutes", "*.csv")) if os.path.basename(f)[:10] >= SEASON_START]
    if not files: print("No games of this season recorded yet."); return
    Mn = pd.concat([pd.read_csv(f) for f in files])
    games = Mn.drop_duplicates("espn_event_id")[["espn_event_id", "date", "away", "home"]]
    team_of = {str(int(t)): c for t, c in Mn.drop_duplicates("team_id")[["team_id", "team"]].dropna().values}
    S = pd.read_csv(SHOTS) if os.path.exists(SHOTS) else pd.DataFrame(columns=["espn_event_id"])
    need = sorted(set(games.espn_event_id) - set(S.espn_event_id))
    if need:
        with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda e: nba_shots.game_shots(e, team_of), need))
        rows = []
        info = games.set_index("espn_event_id")
        for e, r in zip(need, res):
            if not r: continue
            for x in r[0]: x.update(date=info.at[e, "date"], away=info.at[e, "away"], home=info.at[e, "home"]); rows.append(x)
        if rows:
            S = pd.concat([S, pd.DataFrame(rows)], ignore_index=True) if len(S) else pd.DataFrame(rows)
            S.to_csv(SHOTS, index=False, compression="gzip")
    if not len(S): print("No shots yet."); return
    S = prep(S)
    b = np.array(json.load(open(MODEL))["coef"])
    S["xpts"] = S.value / (1 + np.exp(-(design(S) @ b))); S["pts"] = S.made * S.value
    TG = S.groupby(["espn_event_id", "date", "home", "away", "team"]).agg(pts=("pts", "sum"), xpts=("xpts", "sum")).reset_index()
    TG["luck"] = TG.pts - TG.xpts
    opp = TG[["espn_event_id", "team", "luck"]].rename(columns={"team": "opp", "luck": "opp_luck"})
    TG = TG.merge(TG[["espn_event_id", "team"]].rename(columns={"team": "opp"}), on="espn_event_id")
    TG = TG[TG.team != TG.opp].merge(opp, on=["espn_event_id", "opp"])
    out = {t: dict(games=int(len(g)), luck=round(float(g.luck.mean()), 3), luck_allowed=round(float(g.opp_luck.mean()), 3),
                   through=str(g.date.max())) for t, g in TG.groupby("team")}
    form = recent_form()
    for t, v in form.items(): out.setdefault(t, dict(games=0, luck=0.0, luck_allowed=0.0, through=None)).update(v)
    # league-wide shift this season (every team shooting below/above the shot model): measured so it can be taken out,
    # so the correction only moves games whose teams were luckier or unluckier than the league (backtested Nov 1, 2026)
    league = round(float(TG.luck.mean()), 3)
    json.dump(dict(made_at=str(pd.Timestamp.now(tz="America/New_York"))[:16], weight=LUCK_WEIGHT, min_games=MIN_GAMES,
                   form_weight_total=FORM_W_TOTAL, form_weight_spread=FORM_W_SPREAD, form_min_games=FORM_MIN,
                   league_luck_per_team_game=league, teams=out),
              open(OUT, "w"), indent=1)
    top = sorted(out.items(), key=lambda kv: -(kv[1]["luck"] + kv[1]["luck_allowed"] - 2 * league))
    print(f"Shooting luck: {len(TG) // 2} games, {len(out)} teams. Luckiest (own + allowed, pts/game): " +
          ", ".join(f"{t.upper()} {v['luck'] + v['luck_allowed']:+.1f}" for t, v in top[:3]) +
          "; unluckiest: " + ", ".join(f"{t.upper()} {v['luck'] + v['luck_allowed']:+.1f}" for t, v in top[-3:]) +
          f" (league average {league:+.1f} per team-game, taken out)")


if __name__ == "__main__":
    main()
