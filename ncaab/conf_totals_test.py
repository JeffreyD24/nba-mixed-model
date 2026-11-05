"""NCAAM conference-game totals test on unseen 2021-23 at the consensus close (ncaab/research/CONF_TOTALS_PREREG_2026-11-05.md).
  python ncaab/conf_totals_test.py WORKDIR -> ncaab/research/conf_totals_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
P = pd.read_csv(os.path.join(W, "ncaab", "data", "preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})]).sort_values("date")
long["n"] = long.groupby(["season", "t"]).cumcount(); first = long.groupby(["season", "t", "date"]).n.min()
P["hn"] = [first.get((s, t, d), 0) for s, t, d in zip(P.season, P.hk, P.date)]; P["an"] = [first.get((s, t, d), 0) for s, t, d in zip(P.season, P.ak, P.date)]
ok = P.home_d1 & P.away_d1 & P.neutral_ok & (np.minimum(P.hn, P.an) >= 3) & P.cons_total.notna()
conf = P.conf_game.astype(str) == "True"
e = P.pred_total - P.cons_total; r = np.sign(e) * (P.home_pts + P.away_pts - P.cons_total)
def rec(k, lab):
    k = k & (r != 0); n = int(k.sum())
    if not n: say(f"  {lab:46s} no bets"); return 0, 0
    w = int((r[k] > 0).sum()); u = w * 100 / 110 - (n - w)
    lo = w / n - 1.2816 * np.sqrt(w / n * (1 - w / n) / n)
    bys = " ".join(f"{s % 100:02d}:{((r[k & (P.season == s)] > 0).sum() * 100 / 110 - (r[k & (P.season == s)] < 0).sum()):+.1f}" for s in sorted(P.season[k].unique()))
    say(f"  {lab:46s} {n:5d} bets {w}-{n - w} {w / n:.1%} (90% low {lo:.1%}) {u:+7.1f}u  by season {bys}"); return n, u
old = P.season.isin([2022, 2023])
say("PRE-REGISTERED TEST: conference games, total edge 6+ vs the consensus close, 2021-22 + 2022-23 (unseen), -110")
k = ok & old & conf & (e.abs() >= 6); n, u = rec(k, "conference totals 6+ (THE TEST)")
kk = k & (r != 0); w = (r[kk] > 0).mean(); su = [((r[kk & (P.season == s)] > 0).sum() * 100 / 110 - (r[kk & (P.season == s)] < 0).sum()) for s in (2022, 2023)]
passed = u > 0 and w > 0.5238 and min(su) >= -5
say(f"  DECISION: {'PASS' if passed else 'FAIL'} (units {u:+.1f} > 0: {u > 0}; win% {w:.1%} > 52.4%: {w > 0.5238}; worst season {min(su):+.1f}u >= -5: {min(su) >= -5})")
say("\nDescriptive only (decides nothing):")
for thr in (4, 5): rec(ok & old & conf & (e.abs() >= thr), f"conference totals {thr}+ 2021-23")
rec(ok & old & conf & (e >= 6), "  overs only"); rec(ok & old & conf & (e <= -6), "  unders only")
late = P.date.dt.month.isin([1, 2, 3, 4])
rec(ok & old & ~conf & late & (e.abs() >= 6), "NON-conference Jan-Apr 6+ 2021-23")
rec(ok & old & ~conf & ~late & (e.abs() >= 6), "NON-conference Nov-Dec 6+ 2021-23")
rec(ok & old & conf & (P.type == "post") & (e.abs() >= 6), "conference tournaments 6+ 2021-23")
rec(ok & old & conf & (P.type != "post") & (e.abs() >= 6), "conference regular season 6+ 2021-23")
say("\nSame grading (consensus close) on the seasons where the idea was found, for comparison:")
rec(ok & P.season.isin([2024, 2025, 2026]) & conf & (e.abs() >= 6), "conference totals 6+ 2023-26 (seen)")
rec(ok & P.season.isin([2024, 2025, 2026]) & ~conf & late & (e.abs() >= 6), "NON-conference Jan-Apr 6+ 2023-26 (seen)")
open(os.path.join(W, "ncaab", "research", "conf_totals_output.txt"), "w").write("\n".join(out) + "\n")
