"""Same-game NBA spread + total bets (Nov 4, 2026): with totals bet at the opener and spreads after the 8 PM report, how often do both
fire on one game, and are their results correlated? Uses the rule-audit replay (2023-26)."""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "analysis", "rule_audit_spreads.py")).read().split('out = []')[0]
exec(src)
# totals: opener, previous-game report, edge 3+ (live v5)
et = R.tot_stale - R.open_total; tb = (et.abs() >= 3) & R.open_total.notna()
tr = np.sign(et) * (R.act - R.open_total)
# spreads: ~9 PM line after the report (fallback opener when no 9 PM line), live windows, not moved 0.5+ against
ln = R["sp-3.0"].fillna(R.open_spread); es = R.m8 + ln; mv = ln - R.open_spread
ag = (mv.abs() >= 0.5) & (np.sign(mv) != -np.sign(es))
e0 = R.m8 + R.open_spread
home_dog = (es > 0) & (ln > 0); late_ = R.d.dt.month.isin([2, 3, 4])
us_cat = np.where(es > 0, R.h_cat, R.a_cat); them_cat = np.where(es > 0, R.a_cat, R.h_cat); us_arr = pd.Series(np.where(es > 0, R.h_arr, R.a_arr)).fillna(0).values
trap = (us_cat == "tanking") | (them_cat == "middle") | (us_arr > 0)
sb = ready & (es.abs() >= 3) & ~ag & ((~late_ & ~home_dog) | (late_ & ~trap))
sr = np.sign(es) * (R.mg + ln)
both = tb & sb & (tr != 0) & (sr != 0)
tw, sw = (tr[both] > 0), (sr[both] > 0)
print(f"totals bets {int(tb.sum())}, spread bets {int(sb.sum())}, same game both {int(both.sum())} ({both.sum() / max(sb.sum(), 1):.0%} of spread bets)")
print(f"  total won {tw.mean():.1%}, spread won {sw.mean():.1%}, both won {(tw & sw).mean():.1%}, both lost {(~tw & ~sw).mean():.1%}, split {(tw != sw).mean():.1%}")
print(f"  correlation of the two results {np.corrcoef(tw, sw)[0, 1]:+.3f}")
side_t = np.where(et[both] > 0, "over", "under"); fav = np.where(es[both] > 0, ln[both] < 0, ln[both] > 0)
for st in ("over", "under"):
    for fv, nm in ((True, "favorite"), (False, "underdog")):
        k = (side_t == st) & (fav == fv)
        if k.sum() >= 10:
            print(f"  {st:5} + {nm:8}: {int(k.sum()):4} games, corr {np.corrcoef(tw.values[k], sw.values[k])[0, 1]:+.2f}, "
                  f"both won {(tw.values[k] & sw.values[k]).mean():.0%}, both lost {(~tw.values[k] & ~sw.values[k]).mean():.0%}")
u = lambda w: (w.sum() * 100 / 110 - (~w).sum())
print(f"  units on those games: totals {u(tw):+.1f}u, spreads {u(sw):+.1f}u")
