"""Grader for the pre-registered Polymarket sharp-wallet follow test (sharp/POLY_WALLETS_PREREG_2026-11-05.md).
Written and pushed before it is run on the full data (Nov 6, 2026). Implements the pre-registration exactly:

python sharp/poly_follow_grade.py DATA_DIR OUT_DIR      (DATA_DIR = private repo exchange/poly)

Leagues and periods
  NBA 10345, NHL 10346, NCAAM 10470: RANK = games before 2026-01-15, TEST = 2026-01-15 .. 2026-06-30
  NFL 10187:                          RANK = games before 2025-11-15, TEST = 2025-11-15 .. 2026-02-15
Markets: moneyline, spreads, totals; resolved; pre-game fills only (sharp/wallet_rankings.per_fill).
Primary sharps (per league, RANK only): markets >= 30, money at risk >= $2,000, CLV t-stat >= 2.0.
Secondary lists: top 20 by profit (markets >= 30), top 20 by accuracy (markets >= 30).
Follow rule (TEST): each listed wallet with a non-zero net pre-game position signals its side. Same-side signals in one market
  = one bet; both sides signalled = no bet. Entry = the wallet's money-weighted pre-game price for that side + 0.01 (for a
  merged bet, the mean of the signalling wallets' entries; capped at 0.99). Also graded at the side's closing price.
  Profit per unit = won / entry - 1.
Reported: bets, units, ROI, CLV (close - entry), win rate; per league, per market type, pooled; 90% bootstrap interval by game.
Baseline (c): 200 draws of random wallets matched to each primary wallet on markets and money (same league, RANK period,
  within +/-50% on both, else nearest by log distance), pooled ROI at entry+1c.
PASS: pooled ROI > 0 AND CLV > 0 AND 90% lower bound of ROI > 0 AND primary ROI > 95th percentile of the random baseline.
  ROI > 0 without the rest = LEAD. Otherwise FAIL.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wallet_rankings import load, per_fill, rank

DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
PERIODS = {"10345": ("2026-01-15", "2026-06-30"), "10346": ("2026-01-15", "2026-06-30"),
           "10470": ("2026-01-15", "2026-06-30"), "10187": ("2025-11-15", "2026-02-15")}
TYPES = {"moneyline", "spreads", "totals"}
rng = np.random.default_rng(20261105)

mk, tr = load(DATA, series=set(PERIODS))
mk = mk[mk.market_type.isin(TYPES)]
t = per_fill(mk, tr)
t["series"] = t.condition_id.map(mk.set_index("condition_id").series)
t["day"] = t.game_start.str[:10]
cut = t.series.map(lambda s: PERIODS[s][0]); end = t.series.map(lambda s: PERIODS[s][1])
R, T = t[t.day < cut].copy(), t[(t.day >= cut) & (t.day <= end)].copy()
print(f"fills: rank {len(R):,}  test {len(T):,}; markets rank {R.condition_id.nunique():,} test {T.condition_id.nunique():,}")

W = rank(R)
W.to_csv(os.path.join(OUT, "rank_period_wallets.csv.gz"), index=False, compression="gzip")
q = W[W.markets >= 30]
lists = {"primary_clv": q[(q.risk >= 2000) & (q.clv_t >= 2.0)],
         "top20_profit": q.sort_values("profit", ascending=False).groupby("league").head(20),
         "top20_accuracy": q.sort_values("accuracy", ascending=False).groupby("league").head(20)}
for k, v in lists.items(): print(k, v.groupby("league").size().to_dict())

# per wallet x market in TEST: net position, side, own money-weighted price for that side
buy = T.side.eq("BUY")
T["side_of_fill"] = np.where(buy, T.outcome_index, 1 - T.outcome_index)   # selling outcome k = backing the other side
T["side_price"] = np.where(buy, T.price, 1 - T.price)
pos = T.groupby(["league", "wallet", "condition_id"]).net0.sum().rename("net0").reset_index()
pos = pos[pos.net0.abs() > 1e-9]; pos["side"] = np.where(pos.net0 > 0, 0, 1)
px = T.assign(w=T["size"]).groupby(["wallet", "condition_id", "side_of_fill"]).apply(
    lambda g: np.average(g.side_price, weights=g.w), include_groups=False).rename("own_px").reset_index().rename(columns={"side_of_fill": "side"})
pos = pos.merge(px, on=["wallet", "condition_id", "side"], how="left")
mi = T.groupby("condition_id").agg(event_id=("event_id", "first"), market_type=("market_type", "first"), win0=("win0", "first"))
close0 = T[T.outcome_index == 0].groupby("condition_id").close.first()
close1 = T[T.outcome_index == 1].groupby("condition_id").close.first()
mi["close0"] = close0; mi["close1"] = close1
mi["close0"] = mi.close0.fillna(1 - mi.close1); mi["close1"] = mi.close1.fillna(1 - mi.close0)


def follow(wallets):
    """wallets: DataFrame with league, wallet. Returns one row per bet."""
    s = pos.merge(wallets[["league", "wallet"]], on=["league", "wallet"])
    if s.empty: return pd.DataFrame()
    g = s.groupby("condition_id").agg(league=("league", "first"), sides=("side", "nunique"), side=("side", "first"),
                                      own_px=("own_px", "mean"), n_wallets=("wallet", "nunique"))
    g = g[g.sides == 1].join(mi, how="left")
    g["entry"] = np.minimum(g.own_px + 0.01, 0.99)
    g["close"] = np.where(g.side == 0, g.close0, g.close1)
    g["won"] = np.where(g.side == 0, g.win0, 1 - g.win0)
    g["units"] = g.won / g.entry - 1
    g["units_close"] = g.won / g.close.clip(0.01, 0.99) - 1
    g["clv"] = g.close - g.entry
    return g.reset_index()


def summ(b):
    return pd.Series(dict(bets=len(b), win=b.won.mean(), units=b.units.sum(), roi=b.units.mean(), clv=b.clv.mean(),
                          units_close=b.units_close.sum(), roi_close=b.units_close.mean()))


def boot(b, n=2000):
    ev = b.groupby("event_id").units.agg(["sum", "size"]); s, c = ev["sum"].to_numpy(), ev["size"].to_numpy()
    idx = rng.integers(0, len(ev), (n, len(ev)))
    r = s[idx].sum(1) / c[idx].sum(1)
    return np.percentile(r, [5, 95])


lines = []
res = {}
for name, wl in lists.items():
    b = follow(wl); res[name] = b
    if b.empty: lines.append(f"\n== {name}: no bets"); continue
    b.to_csv(os.path.join(OUT, f"bets_{name}.csv.gz"), index=False, compression="gzip")
    lo, hi = boot(b)
    lines.append(f"\n== {name}: pooled\n{summ(b).round(4).to_string()}\nROI 90% interval by game: {lo:.4f} .. {hi:.4f}")
    lines.append("-- by league\n" + b.groupby("league").apply(summ, include_groups=False).round(4).to_string())
    lines.append("-- by market type\n" + b.groupby("market_type").apply(summ, include_groups=False).round(4).to_string())

# random matched baseline for the primary list
P = lists["primary_clv"]; base = []
pool = q.copy()
for d in range(200):
    pick = []
    for _, w in P.iterrows():
        c = pool[(pool.league == w.league) & (pool.wallet != w.wallet) & pool.markets.between(w.markets * 0.5, w.markets * 1.5) & pool.risk.between(w.risk * 0.5, w.risk * 1.5)]
        if c.empty:
            c = pool[(pool.league == w.league) & (pool.wallet != w.wallet)]
            c = c.assign(dist=(np.log(c.markets / w.markets) ** 2 + np.log(c.risk.clip(1) / max(w.risk, 1)) ** 2)).nsmallest(5, "dist")
        pick.append(c.iloc[rng.integers(0, len(c))][["league", "wallet"]])
    b = follow(pd.DataFrame(pick))
    base.append(b.units.mean() if len(b) else np.nan)
base = np.array(base)
p95 = np.nanpercentile(base, 95) if np.isfinite(base).any() else np.nan
lines.append(f"\n== random matched baseline (200 draws): mean ROI {np.nanmean(base):.4f}, 95th pct {p95:.4f}")

b = res["primary_clv"]
if b is None or b.empty:
    verdict = "FAIL (no primary-list bets)"
else:
    roi, clv, (lo, _) = b.units.mean(), b.clv.mean(), boot(b)
    if roi > 0 and clv > 0 and lo > 0 and roi > p95: verdict = "PASS"
    elif roi > 0: verdict = "LEAD"
    else: verdict = "FAIL"
    verdict += f" (ROI {roi:.4f}, CLV {clv:.4f}, 90% lower {lo:.4f}, baseline p95 {p95:.4f})"
lines.append(f"\nVERDICT (pre-registered, primary list): {verdict}")
out = "\n".join(lines); print(out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "poly_follow_grade_output.txt"), "w").write(
    "Polymarket sharp-wallet follow test, graded per sharp/POLY_WALLETS_PREREG_2026-11-05.md\n" + out + "\n")
