"""NFL player-based strength (nfl-mixed-model dev/player_features.py: expected starting QB's EPA/dropback, team rushing,
pass/rush defense, pace from play-by-play, no lookahead) vs the current team model, graded at DK openers 2020-2025, edge 3+.
Each test season's weights are fit only on earlier seasons (2018+), walk-forward.
  A. player model alone       B. current model + player features (fit on the current model's misses)
  C. market + player features (fit on the opener's misses: does it find what the line misses?)
  python analysis/nfl_player_model.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
src = open(os.path.join(W, "analysis", "nfl_autopsy.py")).read().split("def u(s)")[0].split("W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])")[1]
exec(src)
P = P.drop_duplicates(["date", "home", "away"]).reset_index(drop=True)
F = pd.read_csv(os.path.join(N, "data", "player_team_games.csv")); F["date"] = pd.to_datetime(F.date).dt.strftime("%Y-%m-%d")
F = F[F.stype == "REG"]
k = ["qb_epa", "rush_off", "pass_def", "rush_def", "plays", "qb_change", "pass_off_team", "n_prev"]
H = F[F.is_home == 1][["game_id", "date", "team", "opp"] + k].rename(columns={"team": "home", "opp": "away", **{c: "h_" + c for c in k}})
A = F[F.is_home == 0][["game_id"] + k].rename(columns={c: "a_" + c for c in k})
G = H.merge(A, on="game_id")
# all regular-season games with results (for training years before 2020 too)
res = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))
ab = {"LA": "lar", "LV": "lv", "OAK": "lv", "SD": "lac", "STL": "lar", "WAS": "wsh"}
res["home"] = res.home_team.map(lambda t: ab.get(t, str(t).lower())); res["away"] = res.away_team.map(lambda t: ab.get(t, str(t).lower()))
res = res[res.game_type == "REG"].rename(columns={"gameday": "date"})
res["outdoor"] = res.roof.isin(["outdoors", "open"])
res["wind_x"] = np.where(res.outdoor, res.wind.fillna(res.wind.median()), 0.0); res["cold_x"] = np.where(res.outdoor, (40 - res.temp.fillna(60)).clip(lower=0), 0.0)
G = G.merge(res[["date", "home", "away", "season", "week", "home_score", "away_score", "spread_line", "total_line", "wind_x", "cold_x", "div_game"]], on=["date", "home", "away"])
G["margin_y"] = G.home_score - G.away_score; G["total_y"] = G.home_score + G.away_score
# matchup features
G["pass_edge"] = (G.h_qb_epa + G.a_pass_def) - (G.a_qb_epa + G.h_pass_def)    # fixed Nov 2: defense = EPA allowed, so it adds        # home passing advantage, EPA/play
G["rush_edge"] = (G.h_rush_off + G.a_rush_def) - (G.a_rush_off + G.h_rush_def)
G["pass_sum"] = (G.h_qb_epa + G.a_pass_def) + (G.a_qb_epa + G.h_pass_def)
G["rush_sum"] = (G.h_rush_off + G.a_rush_def) + (G.a_rush_off + G.h_rush_def)
G["pace"] = G.h_plays + G.a_plays
G["qbchg_d"] = G.h_qb_change - G.a_qb_change; G["qbchg_s"] = G.h_qb_change + G.a_qb_change
G["one"] = 1.0
MF = ["one", "pass_edge", "rush_edge", "qbchg_d"]; TF = ["one", "pass_sum", "rush_sum", "pace", "qbchg_s", "wind_x", "cold_x"]
G = G.merge(P[["date", "home", "away", "o_sp", "o_tot", "c_sp", "c_tot", "pm", "pt"]], on=["date", "home", "away"], how="left")
print("games:", len(G), "| with DK/backtest opener 2020-25:", G.o_sp.notna().sum())
def fit(tr, X, y): return np.linalg.lstsq(tr[X].values, tr[y].values, rcond=None)[0]
out = []
for s in range(2020, 2026):
    tr = G[(G.season < s) & (G.season >= 2018)]; te = G[G.season == s].copy()
    te["A_m"] = te[MF].values @ fit(tr, MF, "margin_y"); te["A_t"] = te[TF].values @ fit(tr, TF, "total_y")
    trp = tr.dropna(subset=["pm"])
    if len(trp) > 200:
        trp = trp.assign(rm=trp.margin_y - trp.pm, rt=trp.total_y - trp.pt)
        te["B_m"] = te.pm + te[MF].values @ fit(trp, MF, "rm"); te["B_t"] = te.pt + te[TF].values @ fit(trp, TF, "rt")
    # market residual: use the nflverse closing-ish line for training years (spread_line = home favored by), opener for test
    trm = tr.assign(rm=tr.margin_y - tr.spread_line, rt=tr.total_y - tr.total_line)
    te["C_m"] = -te.o_sp + te[MF].values @ fit(trm, MF, "rm"); te["C_t"] = te.o_tot + te[TF].values @ fit(trm, TF, "rt")
    out.append(te)
T = pd.concat(out); T = T.dropna(subset=["o_sp", "o_tot", "pm"])
def grade(pred, line_home_minus, y, thr=3):
    e = pred - line_home_minus; m = e.abs() >= thr; r = np.sign(e[m]) * (y[m] - line_home_minus[m])
    w, l = (r > 0).sum(), (r < 0).sum(); return w, l, w * 100 / 110 - l
def row(lab, col, mk, thr=3):
    line = -T.o_sp if mk == "m" else T.o_tot; y = T.margin_y if mk == "m" else T.total_y
    per = []; W_ = L_ = 0
    for s in range(2020, 2026):
        x = T.season == s; w, l, u = grade(T.loc[x, col], line[x], y[x], thr); per.append(f"{s % 100}:{u:+5.1f}"); W_ += w; L_ += l
    mae = np.abs(T[col] - y).mean()
    print(f"  {lab:40s} MAE {mae:6.3f} | {W_ + L_:4d} bets {W_ / max(W_ + L_, 1):.1%} {W_ * 100 / 110 - L_:+6.1f}u  [{' '.join(per)}]")
T["mkt_m"] = -T.o_sp; T["mkt_t"] = T.o_tot
print("\nSPREADS (home margin)")
row("DK opener (reference)", "mkt_m", "m"); row("current team model", "pm", "m"); row("A. player model alone", "A_m", "m")
row("B. current model + player features", "B_m", "m"); row("C. opener + player features", "C_m", "m"); row("C at edge 1.5+", "C_m", "m", 1.5)
T["AB_m"] = (T.pm + T.A_m) / 2; row("average of current + player model", "AB_m", "m")
print("\nTOTALS")
row("DK opener (reference)", "mkt_t", "t"); row("current team model", "pt", "t"); row("A. player model alone (+weather)", "A_t", "t")
row("B. current model + player features", "B_t", "t"); row("C. opener + player features", "C_t", "t"); row("C at edge 1.5+", "C_t", "t", 1.5)
T["AB_t"] = (T.pt + T.A_t) / 2; row("average of current + player model", "AB_t", "t")
s = 2025; tr = G[(G.season < s) & (G.season >= 2018)]
print("\nweights (fit 2018-24):  margin", dict(zip(MF, fit(tr, MF, "margin_y").round(2))), "\n  total", dict(zip(TF, fit(tr, TF, "total_y").round(2))))
T.to_csv(os.path.join(W, "analysis", "nfl_player_model_preds.csv"), index=False)
