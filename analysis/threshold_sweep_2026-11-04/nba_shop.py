# Run from the repo root: python analysis/threshold_sweep_2026-11-04/nba_v4_preds.py . (writes nba_v4_preds.csv here, then run nba_sweep.py and nba_shop.py from this folder)
import numpy as np, pandas as pd
B = pd.read_csv("nba_v4_bets3.csv"); B["date"] = pd.to_datetime(B.date).dt.strftime("%Y-%m-%d")
S = pd.read_csv("../../data/odds_history/nba_snapshots.csv.gz")
S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True)
S = S[(S.t < S.groupby("event_id").tip.transform("min")) & S.tot.notna() & S.ov_px.notna()]
key = ["date", "home", "away"]
S = S.merge(B[key + ["v4", "sg", "home_pts", "away_pts"]], on=key)
def pay(px, won, push):
    if push: return 0.0
    w = px/100 if px > 0 else 100/abs(px)
    return w if won else -1.0
GROUPS = {"DK only": ["draftkings"], "CT: DK + FanDuel": ["draftkings", "fanduel"],
          "5 US books": ["draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers"]}
rows = []
for (d, h, a), g in S.groupby(key):
    dk = g[g.book == "draftkings"]
    if not len(dk): continue
    t0 = dk.t.min(); sg = g.sg.iloc[0]; T = g.home_pts.iloc[0] + g.away_pts.iloc[0]
    rec = dict(date=d, home=h, sg=sg)
    for lab, books in GROUPS.items():
        q = g[g.book.isin(books) & (g.t <= t0 + pd.Timedelta(minutes=60))]
        q = q.sort_values("t").groupby("book").tail(1) if lab != "DK only" else dk[dk.t == t0]
        if lab != "DK only": q = pd.concat([q[q.book != "draftkings"], dk[dk.t == t0]])
        px = np.where(sg > 0, q.ov_px, q.un_px)
        # best = better number first (lower total for overs, higher for unders), then better price; value via ~2.5% per half point
        score = -sg*q.tot.values*0.05 + np.array([ (p/100 if p > 0 else 100/abs(p)) for p in px])
        i = int(np.argmax(score)); line, p = q.tot.values[i], px[i]
        won = (T > line) if sg > 0 else (T < line)
        rec[lab] = pay(p, won, T == line); rec[lab + " line"] = line; rec[lab + " px"] = p
    rows.append(rec)
R = pd.DataFrame(rows)
R["season"] = pd.to_datetime(R.date).dt.year.where(pd.to_datetime(R.date).dt.month < 8, pd.to_datetime(R.date).dt.year + 1)
print(f"{len(R)} of {len(B)} NBA v4 bets (edge 3+, 2023-26) matched to multi-book snapshots at DK's opener (+60 min for other books)")
for lab in GROUPS:
    u = R[lab]; bys = " ".join(f"{str(s)[2:]}:{u[R.season == s].sum():+.1f}" for s in sorted(R.season.unique()))
    better = (R[lab + " line"] != R["DK only line"]) | (R[lab + " px"] != R["DK only px"])
    print(f"  {lab:18s} {u.sum():+7.1f}u  ROI {u.mean():+.1%}  better than DK on {better.mean():.0%} of bets   {bys}")
print(f"  gain per season from DK+FD shopping: {(R['CT: DK + FanDuel'].sum() - R['DK only'].sum())/3:+.1f}u; 5 books: {(R['5 US books'].sum() - R['DK only'].sum())/3:+.1f}u")
