"""
Bet record by model version. Every logged bet (state/my_bets.csv) is tagged with the model version that was live when it was
placed (state/bet_versions.csv: one row per version and market, with the ET time it went live). Writes
  state/bet_record.csv          every bet with its version, result, profit ($) and units (profit / stake)
  state/record_by_version.csv   W-L-P, units, ROI per version (and per market), plus an OVERALL row
Add a row to bet_versions.csv whenever a model or betting rule changes; bets placed after that time start a new record.
  python bet_record.py WORKDIR
"""
import os, re, sys
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]); STATE = os.path.join(W, "state")
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def placed_at(r):
    """when the bet was placed (ET): 'placed Nov 2 11:35 AM' / 'placed 2:05 PM' in the notes, else when it was logged"""
    logged = pd.Timestamp(r.logged_at_et)
    m = re.search(r"placed (?:(\w{3}) (\d{1,2}) )?~?(\d{1,2}:\d{2}) ?([AP]M)", str(r.notes))
    if not m: return logged
    mon, day, hm, ap = m.groups()
    d = pd.Timestamp(logged.year, MON[mon], int(day)) if mon in MON else logged.normalize()
    t = pd.to_datetime(f"{hm} {ap}", format="%I:%M %p")
    ts = d + pd.Timedelta(hours=t.hour, minutes=t.minute)
    return ts - pd.Timedelta(days=1) if ts > logged + pd.Timedelta(minutes=5) else ts      # 'placed 11:47 PM' logged after midnight


def main():
    B = pd.read_csv(os.path.join(STATE, "my_bets.csv"))
    V = pd.read_csv(os.path.join(STATE, "bet_versions.csv"), parse_dates=["live_from_et"])
    B["placed_et"] = [placed_at(r) for r in B.itertuples()]
    def version(r):
        v = V[(V.market == r.market) & (V.live_from_et <= r.placed_et)].sort_values("live_from_et")
        return v.iloc[-1].version if len(v) else "before tracking"
    B["version"] = [version(r) for r in B.itertuples()]
    B.loc[B.notes.astype(str).str.contains("OFF-MODEL"), "version"] = "off-model (no alert)"      # bets the model did not call for
    B["status"] = np.where(B.result.isin(["W", "L", "P"]), B.result, "pending")
    B["units"] = np.where(B.status == "pending", np.nan, B.profit / B.stake)
    keep = ["placed_et", "issue", "date", "away", "home", "market", "pick", "line", "odds", "stake", "version", "status", "profit", "units"]
    B[keep].sort_values("placed_et").to_csv(os.path.join(STATE, "bet_record.csv"), index=False)
    rows = []
    def summ(g, label, market):
        d = g[g.status != "pending"]; w, l, p = (d.status == "W").sum(), (d.status == "L").sum(), (d.status == "P").sum()
        desc = V[V.version == label].description.iloc[0] if label in set(V.version) else ""
        rows.append(dict(version=label, market=market, bets=len(g), graded=len(d), wins=int(w), losses=int(l), pushes=int(p),
                         pending=int((g.status == "pending").sum()), units=round(d.units.sum(), 2),
                         roi=round(d.units.sum() / len(d), 4) if len(d) else None, description=desc))
    for (ver, mk), g in B.groupby(["version", "market"]): summ(g, ver, mk)
    summ(B, "OVERALL", "all")
    R = pd.DataFrame(rows); R.to_csv(os.path.join(STATE, "record_by_version.csv"), index=False)
    for r in R.itertuples():
        print(f"{r.version:28s} {r.market:10s} {r.wins}-{r.losses}-{r.pushes} ({r.pending} pending)  {r.units:+.2f}u")


if __name__ == "__main__":
    main()
