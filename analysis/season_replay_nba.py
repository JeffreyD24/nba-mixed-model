"""Replay the CURRENT NBA totals rules (Nov 2, 2026) on this season's finished games at the opening total: Model 1's locked
pick (state/picks_log.csv) + shooting-luck correction from games before that date (both teams 5+ games) + altitude; recent form
needs 10+ games (not active yet). Spreads need 10+ games for both teams, so no spread bets yet under the current rules.
  python analysis/season_replay_nba.py WORKDIR"""
import os, sys, json
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W); sys.argv = ["x", W]
import nba_luck as nl
P = pd.read_csv(os.path.join(W, "state", "picks_log.csv")); P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
P = P[P.home_pts.notna() & P.open_total.notna()].drop_duplicates("game_id").copy()
S = nl.prep(pd.read_csv(os.path.join(W, "state", "nba_shots_2026_27.csv.gz")))
b = np.array(json.load(open(os.path.join(W, "data", "shot_quality_model.json")))["coef"])
S["xpts"] = S.value / (1 + np.exp(-(nl.design(S) @ b))); S["pts"] = S.made * S.value
TG = S.groupby(["espn_event_id", "date", "team"]).agg(pts=("pts", "sum"), xpts=("xpts", "sum")).reset_index(); TG["luck"] = TG.pts - TG.xpts
opp = TG[["espn_event_id", "team", "luck"]].rename(columns={"team": "opp", "luck": "opp_luck"})
TG = TG.merge(TG[["espn_event_id", "team"]].rename(columns={"team": "opp"}), on="espn_event_id"); TG = TG[TG.team != TG.opp].merge(opp, on=["espn_event_id", "opp"])
TG["date"] = pd.to_datetime(TG.date).dt.strftime("%Y-%m-%d")
adj = []
for r in P.itertuples():
    before = TG[TG.date < r.date]; lg = before.luck.mean() if len(before) else 0.0
    th, ta = before[before.team == r.home], before[before.team == r.away]
    a = -0.5 * (th.luck.mean() + th.opp_luck.mean() + ta.luck.mean() + ta.opp_luck.mean() - 4 * lg) if min(len(th), len(ta)) >= 5 else 0.0
    adj.append(a)
P["luck_adj"] = adj; P["alt"] = np.where(P.home.isin(["den", "utah"]), 3.8, 0.0)
P["model_v3"] = P.pred_total + P.luck_adj + P.alt
tot = P.home_pts + P.away_pts
for lab, col in (("Model 1 alone (v1 rules)", "pred_total"), ("current totals model (v3)", "model_v3")):
    e = P[col] - P.open_total; k = e.abs() >= 3; r_ = np.sign(e[k]) * (tot[k] - P.open_total[k]); w, l = (r_ > 0).sum(), (r_ < 0).sum()
    print(f"  {lab:28s} {k.sum():3d} bets {w}-{l}  {w * 100 / 110 - l:+.2f}u at -110")
print(f"  {len(P)} finished games {P.date.min()} .. {P.date.max()}; luck correction active in {(P.luck_adj != 0).sum()} of them; altitude games {(P.alt > 0).sum()}")
for lab, k0 in (("altitude games", P.alt > 0), ("luck-adjusted games", P.luck_adj != 0)):
    d = P[k0]; e1 = d.pred_total - d.open_total; e3 = d.model_v3 - d.open_total; t = d.home_pts + d.away_pts
    for nm_, e in (("v1", e1), ("v3", e3)):
        k = e.abs() >= 3; r_ = np.sign(e[k]) * (t[k] - d.open_total[k]); print(f"    {lab:22s} {nm_}: {k.sum()} bets {(r_ > 0).sum()}-{(r_ < 0).sum()}")
