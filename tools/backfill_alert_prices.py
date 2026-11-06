"""Backfill the DraftKings price at alert time into state/alerts.csv (Nov 6, 2026; Jeffrey: grade alerts at their real price, not -110).
New alerts store `price` themselves (alert.py, Nov 6). For older rows: the last DraftKings odds snapshot at or before the alert time
(research/odds/<date>.csv, ESPN's DraftKings feed, logged on every change) whose line equals the alerted line. Rows with no matching
snapshot stay blank (graded at -110 and labeled so).   python tools/backfill_alert_prices.py .
"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); p = os.path.join(W, "state", "alerts.csv")
A = pd.read_csv(p)
if "price" not in A: A["price"] = np.nan
O = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(W, "research", "odds", "*.csv")))], ignore_index=True)
O = O[O.book.astype(str).str.replace(" ", "") == "DraftKings"].copy(); O["seen"] = pd.to_datetime(O.seen_at_et); O["game_id"] = O.game_id.astype(str)
filled = 0
for i, r in A[A.price.isna()].iterrows():
    q = O[(O.game_id == str(r.game_id)) & (O.seen <= pd.Timestamp(r.alerted_at_et) + pd.Timedelta(minutes=2))].sort_values("seen")
    if r.market == "spread":
        q = q[q.home_spread == float(r.line)]; col = "home_spread_odds" if r.side == "home" else "away_spread_odds"
    else:
        q = q[q.total == float(r.line)]; col = "over_odds" if r.side == "over" else "under_odds"
    if len(q) and pd.notna(q.iloc[-1][col]):
        A.at[i, "price"] = float(q.iloc[-1][col]); filled += 1
A.to_csv(p, index=False)
print(f"alerts {len(A)}: price filled for {filled} more, {int(A.price.notna().sum())} have a price, {int(A.price.isna().sum())} still blank")
