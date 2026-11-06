"""NBA spread live filters on 2013-14..2021-22 at SBR OPENERS (Nov 6, 2026).

Pre-registered: betting-goals/models/tests/NBA_SPREAD_FILTERS_SBR_PREREG.md (pushed 655f304 before grading).
Bets: analysis/old_seasons_sbr_bets.csv (Model 1 without injuries, one-day lag, walk-forward, edge 3+ at the SBR opener, -110),
spread, trusted rows. Filters: early (Oct-Jan) drop home underdogs; late (Feb-season end) drop bets ON a tanking team and AGAINST a
5-10 team. The "recent arrival" trap is left out (no transaction data). Both teams 10+ games.
  python analysis/spread_filters_sbr.py .  -> analysis/spread_filters_sbr_output.txt, analysis/spread_filters_sbr_bets.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
sys.argv = [sys.argv[0], W, "none"]
sys.path.insert(0, os.path.join(W, "analysis"))
import old_seasons_sbr as osb  # noqa: E402
BOOT, SEED = 10000, 20261106
EAST = {"atl", "bos", "bkn", "cha", "chi", "cle", "det", "ind", "mia", "mil", "ny", "orl", "phi", "tor", "wsh"}
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

D, _ = osb.build()
B = pd.read_csv(os.path.join(W, "analysis", "old_seasons_sbr_bets.csv"))
B = B[(B.market == "spread") & (B.trusted == 1)].merge(D[["date", "home", "away", "open_spread"]], on=["date", "home", "away"], how="left")
assert B.open_spread.notna().all()

# ---- games played and standings category on each date (games before it), as in old_seasons_traps.py
cat, ngames = {}, {}
for s, S in D.groupby("season"):
    S = S.sort_values("date")
    for d in sorted(S.date.unique()):
        past = S[S.date < d]
        rec = {}
        for r in past.itertuples():
            for t, w in ((r.home, r.home_pts > r.away_pts), (r.away, r.away_pts > r.home_pts)):
                a, b = rec.get(t, (0, 0)); rec[t] = (a + int(w), b + int(not w))
        for t, (a, b) in rec.items(): ngames[(d, t)] = a + b
        if len(past) < 150: continue
        for conf in (True, False):
            c = sorted([(t, a, b) for t, (a, b) in rec.items() if (t in EAST) == conf], key=lambda x: -x[1] / max(x[1] + x[2], 1))
            if len(c) < 10: continue
            w10, l10 = c[9][1], c[9][2]
            for i, (t, a, b) in enumerate(c, 1):
                gb = ((w10 - l10) - (a - b)) / 2
                cat[(d, t)] = "top" if i <= 4 else "middle" if i <= 10 else "bubble" if (i <= 12 and gb <= 4) else "tanking"

B["hn"] = [ngames.get((d, t), 0) for d, t in zip(B.date, B.home)]; B["an"] = [ngames.get((d, t), 0) for d, t in zip(B.date, B.away)]
n0 = len(B); B = B[(B.hn >= 10) & (B.an >= 10)].copy()
hb = B.side == "home"
B["our"] = [cat.get((d, t)) for d, t in zip(B.date, np.where(hb, B.home, B.away))]
B["opp"] = [cat.get((d, t)) for d, t in zip(B.date, np.where(hb, B.away, B.home))]
B["late"] = pd.to_datetime(B.date).dt.month.isin([2, 3, 4, 5, 6, 7, 8])
B["home_dog"] = hb & (B.open_spread > 0)
B["drop_hd"] = ~B.late & B.home_dog
B["drop_tank"] = B.late & (B.our == "tanking")
B["drop_mid"] = B.late & (B.opp == "middle")
B["kept"] = ~(B.drop_hd | B.drop_tank | B.drop_mid)
B["units"] = np.where(B.result > 0, 100 / 110, np.where(B.result < 0, -1.0, 0.0))

say("NBA spread live filters at SBR openers, 2013-14..2021-22 (Model 1 no injuries, one-day lag, walk-forward, edge 3+, -110, trusted)")
say(f"spread bets {n0}; both teams 10+ games: {len(B)}; late-period bets with a standings category: {B[B.late].our.notna().mean():.0%}")
SEAS = sorted(B.season.unique())
def row(G, lab):
    w, l = int((G.result > 0).sum()), int((G.result < 0).sum())
    by = " ".join(f"{s % 100}:{G[G.season == s].units.sum():+.0f}" for s in SEAS)
    say(f"  {lab:44s} {w + l:5d} bets {w / max(w + l, 1):6.1%} {G.units.sum():+7.1f}u ({G.units.mean() * 100:+5.1f}/100)  [{by}]")
say("\nAll / Kept / Removed")
row(B, "all bets (ready)"); row(B[B.kept], "KEPT by the live filters"); row(B[~B.kept], "REMOVED by the live filters")
say("\nEach filter piece (bets it removes vs the rest of its period)")
row(B[B.drop_hd], "early: home underdogs (removed)"); row(B[~B.late & ~B.home_dog], "early: everything else")
row(B[B.drop_tank], "late: bet ON a tanking team (removed)"); row(B[B.drop_mid], "late: bet AGAINST a 5-10 team (removed)")
row(B[B.late & B.kept], "late: kept")
say("\nKept by period")
row(B[B.kept & ~B.late], "Oct-Jan kept"); row(B[B.kept & B.late], "Feb-end kept")

rng = np.random.default_rng(SEED)
K = {s: B[(B.season == s) & B.kept].units.values for s in SEAS}; R = {s: B[(B.season == s) & ~B.kept].units.values for s in SEAS}
diffs = np.empty(BOOT)
for i in range(BOOT):
    k = np.concatenate([rng.choice(K[s], len(K[s])) for s in SEAS if len(K[s])])
    r = np.concatenate([rng.choice(R[s], len(R[s])) for s in SEAS if len(R[s])])
    diffs[i] = k.mean() - r.mean()
d = B[B.kept].units.mean() - B[~B.kept].units.mean()
wins = sum(K[s].mean() > R[s].mean() for s in SEAS if len(K[s]) and len(R[s]))
say("\nPRIMARY TEST: ROI per bet, Kept minus Removed (pooled)")
say(f"  difference {d * 100:+.1f}/100; bootstrap 10th percentile {np.percentile(diffs, 10) * 100:+.1f}; 90% range "
    f"{np.percentile(diffs, 5) * 100:+.1f} to {np.percentile(diffs, 95) * 100:+.1f}; Kept beats Removed in {wins} of {len(SEAS)} seasons")
v = "REJECTED" if d <= 0 else ("CONFIRMED" if np.percentile(diffs, 10) > 0 and wins >= 6 else "INCONCLUSIVE")
say(f"  VERDICT (pre-registered rule): {v}")
B.to_csv(os.path.join(W, "analysis", "spread_filters_sbr_bets.csv"), index=False)
open(os.path.join(W, "analysis", "spread_filters_sbr_output.txt"), "w").write("\n".join(out) + "\n")
