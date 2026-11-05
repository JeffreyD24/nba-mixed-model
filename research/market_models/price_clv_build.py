"""Build per-game first-seen and closing DK/Pinnacle totals and spreads with both prices (same snapshot).
python research/market_models/price_clv_build.py -> research/market_models/price_lines.csv.gz"""
import glob, os, pandas as pd, numpy as np
fs = sorted(glob.glob("data/odds_history/nba/*.csv.gz"))
keep = []
for f in fs:
    d = pd.read_csv(f, usecols=["snapshot_utc","event_id","commence_et","home","away","book","market","outcome","price","point"])
    d = d[d.book.isin(["draftkings","pinnacle"]) & d.market.isin(["totals","spreads"])]
    keep.append(d)
D = pd.concat(keep, ignore_index=True)
D["snap"] = pd.to_datetime(D.snapshot_utc, utc=True)
D["tip"] = pd.to_datetime(D.commence_et).dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
D = D[D.snap <= D.tip]
def side(r):
    if r.market == "totals": return "a" if r.outcome == "Over" else "b"
    return "a" if r.outcome == r.home else "b"
D["s"] = np.where(D.market == "totals", np.where(D.outcome == "Over", "a", "b"), np.where(D.outcome == D.home, "a", "b"))
W = D.pivot_table(index=["event_id","commence_et","home","away","book","market","snap"], columns="s", values=["price","point"], aggfunc="first")
W.columns = [f"{a}_{b}" for a, b in W.columns]; W = W.reset_index().dropna(subset=["price_a","price_b","point_a"])
def dec(a): return np.where(a > 0, 1 + a/100, 1 + 100/np.abs(a))
qa, qb = 1/dec(W.price_a), 1/dec(W.price_b)
W["p_a"] = qa/(qa+qb)                         # no-vig prob of over / home side
W = W.sort_values("snap")
g = W.groupby(["event_id","book","market"])
first, last = g.first().add_suffix("_open"), g.last().add_suffix("_close")
L = first.join(last).reset_index()
L = L.rename(columns={"commence_et_open":"commence_et","home_open":"home","away_open":"away"}).drop(columns=["commence_et_close","home_close","away_close"])
L.to_csv("research/market_models/price_lines.csv.gz", index=False)
print(L.shape); print(L.groupby(["book","market"]).size())
