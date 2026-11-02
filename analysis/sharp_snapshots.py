"""Every pre-game snapshot of every book's NBA/NHL main lines in one table (for the sharp-money analysis).
  python analysis/sharp_snapshots.py WORKDIR SPORT -> data/odds_history/{sport}_snapshots.csv.gz
Columns: date, home, away, tip, t, book, sp (home spread / puck line), sp_px_h, sp_px_a, tot, ov_px, un_px, ml_h, ml_a"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); SP = sys.argv[2]
if SP == "nba":
    exec(open(os.path.join(W, "analysis", "odds_openers.py")).read().split("rows = []")[0].split("W = os.path.abspath(sys.argv[1])")[1])
else:
    exec(open(os.path.join(W, "analysis", "nhl_odds_table.py")).read().split("rows, unk")[0].split("W = os.path.abspath(sys.argv[1])")[1])
out = []
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", SP, "*.csv.gz"))):
    d = pd.read_csv(f)
    d["t"] = pd.to_datetime(d.snapshot_utc); d["tip"] = pd.to_datetime(d.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    d = d[(d.t < d.tip) & d.home.isin(NAME) & d.away.isin(NAME)]
    d["oc"] = np.where(d.market == "totals", d.outcome, np.where(d.outcome == d.home, "h", "a"))
    pv = d.pivot_table(index=["event_id", "home", "away", "tip", "t", "book"], columns=["market", "oc"], values=["price", "point"], aggfunc="first")
    g = lambda v, mk, oc: pv[(v, mk, oc)] if (v, mk, oc) in pv.columns else np.nan
    o = pd.DataFrame(dict(sp=g("point", "spreads", "h"), sp_px_h=g("price", "spreads", "h"), sp_px_a=g("price", "spreads", "a"),
                          tot=g("point", "totals", "Over"), ov_px=g("price", "totals", "Over"), un_px=g("price", "totals", "Under"),
                          ml_h=g("price", "h2h", "h"), ml_a=g("price", "h2h", "a")), index=pv.index).reset_index()
    out.append(o)
O = pd.concat(out, ignore_index=True)
O["date"] = O.tip.dt.tz_convert("America/New_York").dt.date.astype(str); O["home"] = O.home.map(NAME); O["away"] = O.away.map(NAME)
O.to_csv(os.path.join(W, "data", "odds_history", f"{SP}_snapshots.csv.gz"), index=False, compression="gzip")
print(SP, len(O), "rows,", O.event_id.nunique(), "games,", O.groupby("book").size().to_dict())
