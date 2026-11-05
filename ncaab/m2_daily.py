"""NCAAM M2 totals TEST record (Nov 5, 2026). M2 = moving-scoring-level team model (ncaab/research/MODEL2_RESULTS_2026-11-05.md).
Fable review BLOCKED live use (DraftKings-only 2024-26: -3.6u), so this grades the rule on 2026-27 at DraftKings' OWN opener only:
totals with |M2 - DK opener| >= 6, both teams with a conference id and 3+ games. Re-review with Fable at ~300 DK bets.
Each morning: ESPN scoreboards for the last 3 days -> rebuild all_games.csv -> M2 walk-forward (pre-game-known team rule) -> grade.
  python ncaab/m2_daily.py WORKDIR -> ncaab/state/m2_totals_test.md, ncaab/state/m2_totals_test.csv"""
import os, sys, subprocess, importlib.util
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); PY = sys.executable; D = os.path.join(W, "ncaab", "data"); ST = os.path.join(W, "ncaab", "state")
spec = importlib.util.spec_from_file_location("em", os.path.join(W, "ncaab", "espn_meta.py")); em = importlib.util.module_from_spec(spec); sys.argv = ["x"]; spec.loader.exec_module(em)
MP = os.path.join(D, "espn_meta.csv"); M = pd.read_csv(MP, low_memory=False)
today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
new = [r for d in pd.date_range(today - pd.Timedelta(days=3), today - pd.Timedelta(days=1)) for r in em.day(d)]
if new:
    N = pd.DataFrame(new); M = pd.concat([M[~M.espn_id.astype(str).isin(N.espn_id.astype(str))], N], ignore_index=True); M.to_csv(MP, index=False)
subprocess.run([PY, os.path.join(W, "ncaab", "build_all_games.py"), W], check=True)
# M2 only, pre-game-known team rule
src = open(os.path.join(W, "ncaab", "model2_tournament.py")).read().split("SEAS = sorted")[0]
ns = {"__name__": "m2"}; sys.argv = ["x", W, "--live-rule"]; exec(src, ns)
G = ns["G"]; m, t = ns["walk"](sorted(G.season.unique()), level_half=14); G["M2_t"] = t
long = pd.concat([G[["season", "date", "hk"]].rename(columns={"hk": "k"}), G[["season", "date", "ak"]].rename(columns={"ak": "k"})]).sort_values("date")
long["n"] = long.groupby(["season", "k"]).cumcount(); fg = long.groupby(["season", "k", "date"]).n.min()
cur = G.season.max(); S = G[(G.season == cur) & (G.book == "DraftKings") & G.book_tot.notna()].copy()
S["hn"] = [fg.get((s, k, d), 0) for s, k, d in zip(S.season, S.hk, S.date)]; S["an"] = [fg.get((s, k, d), 0) for s, k, d in zip(S.season, S.ak, S.date)]
S = S[(S.hk != "OTHER") & (S.ak != "OTHER") & (np.minimum(S.hn, S.an) >= 3)]
e = S.M2_t - S.book_tot; B = S[e.abs() >= 6].copy(); sg = np.sign(e[B.index]); tot = B.home_pts + B.away_pts
B["side"] = np.where(sg > 0, "over", "under"); B["edge"] = e[B.index].abs().round(1)
r = sg * (tot - B.book_tot); B["result"] = np.where(r > 0, "W", np.where(r < 0, "L", "P")); B["units"] = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0))
B["clv"] = (sg * (B.close_tot - B.book_tot)).round(2)
B[["date", "home_name", "away_name", "side", "book_tot", "M2_t", "edge", "close_tot", "clv", "result", "units"]].to_csv(os.path.join(ST, "m2_totals_test.csv"), index=False)
w, l = (B.result == "W").sum(), (B.result == "L").sum()
txt = (f"# NCAAM M2 totals TEST record {cur - 1}-{str(cur)[2:]} (not bets), updated {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET\n\n"
       f"Rule: |M2 total - DraftKings' own opener| >= 6 (DraftKings rows only), both teams with a conference id and 3+ games, -110.\n"
       f"Fable review Nov 5 BLOCKED live use; re-review at ~300 DraftKings bets. Break-even CLV 1.02.\n\n"
       f"- {len(B)} test bets, {w}-{l}, {B.units.sum():+.2f}u, CLV {B.clv.mean():+.2f}, overs {(B.side == 'over').mean():.0%}\n")
open(os.path.join(ST, "m2_totals_test.md"), "w").write(txt); print(txt)
