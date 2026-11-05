"""Polymarket wallet rankings (Nov 5, 2026; pre-registration sharp/POLY_WALLETS_PREREG_2026-11-05.md).

python sharp/wallet_rankings.py DATA_DIR OUT_DIR [--before 2026-01-01]
  DATA_DIR holds {series}_markets.csv.gz and {series}_trades_{YYYY-MM}.csv.gz from sharp/exchange_history.py poly.
  Uses PRE-GAME fills only (timestamp before the market's game start). Only resolved markets (final price 1 / 0).
  Every fill is one wallet buying or selling one outcome token at a price p for `size` shares:
    BUY  profit = size * (won - p)       money at risk = size * p
    SELL profit = size * (p - won)       money at risk = size * (1 - p)
  Close = last pre-game fill price of that token (the other token's close = 1 - it when it has no fills).
    CLV per fill: BUY close - p, SELL p - close (in probability points), weighted by money at risk.
  Per wallet and league: markets, fills, money at risk, profit, ROI, accuracy (share of markets where the wallet's net
  pre-game position was on the winner), CLV, CLV t-stat across markets, median hours before start of its money.
  --before splits the ranking period (games before the date) from the test period; without it all games are ranked.
Writes OUT_DIR/wallets_{league}_{period}.csv.gz and prints the top wallets by each measure.
"""
import os, sys, glob
import numpy as np, pandas as pd

DATA, OUT = sys.argv[1], sys.argv[2]
BEFORE = sys.argv[sys.argv.index("--before") + 1] if "--before" in sys.argv else None
LEAGUE = {"10345": "nba", "10346": "nhl", "10470": "ncaab", "39": "ncaa_old", "10187": "nfl", "12185": "nfl", "12756": "ncaaf"}
os.makedirs(OUT, exist_ok=True)


def load():
    mk, tr = [], []
    for f in glob.glob(os.path.join(DATA, "*_markets.csv.gz")):
        ser = os.path.basename(f).split("_")[0]
        m = pd.read_csv(f, dtype=str); m["series"] = ser; m["league"] = LEAGUE.get(ser, ser); mk.append(m)
        for t in glob.glob(os.path.join(DATA, f"{ser}_trades_*.csv.gz")):
            tr.append(pd.read_csv(t, dtype={"condition_id": str, "wallet": str, "side": str}))
    mk = pd.concat(mk).drop_duplicates("condition_id")
    tr = pd.concat(tr, ignore_index=True)
    for c in ("outcome_index", "size", "price", "ts"): tr[c] = pd.to_numeric(tr[c], errors="coerce")
    return mk, tr.dropna(subset=["outcome_index", "size", "price", "ts"])


def per_fill(mk, tr):
    fp = mk.final_prices.fillna("").str.split("|", expand=True)
    mk = mk.assign(win0=pd.to_numeric(fp[0], errors="coerce"), start_ts=pd.to_datetime(mk.game_start, utc=True, errors="coerce", format="mixed"))
    mk = mk[mk.win0.isin([0.0, 1.0]) & mk.start_ts.notna()]
    mk["start_ts"] = (mk.start_ts - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    t = tr.merge(mk[["condition_id", "league", "market_type", "win0", "start_ts", "game_start"]], on="condition_id")
    t = t[t.ts < t.start_ts].copy()  # pre-game only
    t["won"] = np.where(t.outcome_index == 0, t.win0, 1 - t.win0)
    # close: last pre-game fill price per token; complement for a token with no fills
    last = t.sort_values("ts").groupby(["condition_id", "outcome_index"]).price.last().unstack()
    for a, b in ((0, 1), (1, 0)):
        if a not in last: last[a] = np.nan
    last[0] = last[0].fillna(1 - last.get(1)); last[1] = last[1].fillna(1 - last[0])
    t["close"] = np.where(t.outcome_index == 0, t.condition_id.map(last[0]), t.condition_id.map(last[1]))
    buy = t.side.eq("BUY")
    t["risk"] = np.where(buy, t["size"] * t.price, t["size"] * (1 - t.price))
    t["profit"] = np.where(buy, t["size"] * (t.won - t.price), t["size"] * (t.price - t.won))
    t["clv"] = np.where(buy, t.close - t.price, t.price - t.close)
    # net shares on outcome 0 (buying outcome 1 = short outcome 0)
    sgn = np.where(buy, 1, -1) * np.where(t.outcome_index == 0, 1, -1)
    t["net0"] = sgn * t["size"]
    t["hours_before"] = (t.start_ts - t.ts) / 3600
    return t


def rank(t):
    g = t.assign(rclv=t.risk * t.clv).groupby(["wallet", "condition_id"]).agg(
        league=("league", "first"), risk=("risk", "sum"), profit=("profit", "sum"), rclv=("rclv", "sum"),
        net0=("net0", "sum"), win0=("win0", "first"), fills=("price", "size"), hours=("hours_before", "median"))
    g["correct"] = np.where(g.net0.abs() < 1e-9, np.nan, ((g.net0 > 0) == (g.win0 == 1)).astype(float))
    g["mclv"] = g.rclv / g.risk.where(g.risk > 0)
    w = g.reset_index().groupby(["league", "wallet"]).agg(
        markets=("condition_id", "size"), fills=("fills", "sum"), risk=("risk", "sum"), profit=("profit", "sum"),
        rclv=("rclv", "sum"), accuracy=("correct", "mean"), clv_sd=("mclv", "std"), hours=("hours", "median"))
    w["roi"] = w.profit / w.risk
    w["clv"] = w.rclv / w.risk
    w["clv_t"] = w.clv / (w.clv_sd / np.sqrt(w.markets))
    return w.drop(columns="rclv").reset_index()


mk, tr = load()
t = per_fill(mk, tr)
periods = {"all": t} if not BEFORE else {"rank": t[t.game_start < BEFORE], "test": t[t.game_start >= BEFORE]}
for name, part in periods.items():
    w = rank(part)
    for lg, x in w.groupby("league"):
        x.sort_values("profit", ascending=False).to_csv(os.path.join(OUT, f"wallets_{lg}_{name}.csv.gz"), index=False, compression="gzip")
        q = x[x.markets >= 20]
        print(f"\n== {lg} {name}: wallets {len(x)}, with 20+ markets {len(q)}, pre-game money ${x.risk.sum():,.0f}, markets {part[part.league == lg].condition_id.nunique()}")
        cols = ["wallet", "markets", "risk", "profit", "roi", "accuracy", "clv", "clv_t", "hours"]
        for by in ("profit", "roi", "accuracy", "clv_t"):
            print(f"-- top 5 by {by} (20+ markets)"); print(q.sort_values(by, ascending=False)[cols].head(5).round(3).to_string(index=False))
