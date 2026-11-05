"""
Quick check, run every minute by alert_loop.sh between full checks: has DraftKings posted a line for any game we have a
model for (today, tomorrow) since the last look? Exits with code 10 if so, so the loop runs a full alert check at once.
DraftKings posts NBA lines around 8:30 PM ET the night before (seen in research/timeline). Ported from nhl-mixed-model.

  python opener_watch.py WORKDIR
"""
import os, sys, json, datetime as dt
from zoneinfo import ZoneInfo
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
import actionnet

STATE = os.path.join(W, "state")
today = dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
days = sorted({f[6:16] for f in os.listdir(STATE) if f.startswith("model_") and f.endswith(".json") and f[6:16] >= today})
path = os.path.join(STATE, "openers_seen.json")
seen = set(json.load(open(path))) if os.path.exists(path) else set()
new = []
direct = None
try:                                                    # Nov 5, 2026: DraftKings' own feed first (Action Network showed lines DraftKings had not posted)
    import dk_direct
    D = dk_direct.now("nba", max_age=0)
    if len(D): direct = D[D.market == "Total"]
except Exception as e:
    print("DraftKings direct unavailable:", type(e).__name__)
if direct is not None:
    for r in direct.drop_duplicates("event_id").itertuples():
        if r.date in days:
            k = f"{r.date}|{r.away}@{r.home}"
            if k not in seen: new.append(k); seen.add(k)
    days = []                                           # skip the Action Network loop below
for d in days:
    try:
        L = actionnet.lines(d)
    except Exception as e:
        print("Action Network unavailable:", type(e).__name__); continue
    for r in L.itertuples():
        if r.an_spread == r.an_spread or r.an_total == r.an_total:          # DraftKings has a spread or total up
            k = f"{d}|{r.away}@{r.home}"
            if k not in seen: new.append(k); seen.add(k)
json.dump(sorted(k for k in seen if k[:10] >= today), open(path, "w"))
if new:
    print("New DraftKings lines:", ", ".join(new)); sys.exit(10)
print("No new DraftKings lines.")
