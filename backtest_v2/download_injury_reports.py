"""
Download official NBA injury report PDFs for every game date (same snapshots as the earlier backtest).

For each game date D:
  - D-1 at 8 PM and 9 PM ET   (what was known around when opening lines are posted)
  - D at 11 AM, 1, 3, 5, 6, 7, 8, 9 PM ET   (pre-tip snapshots)
Old file names: Injury-Report_YYYY-MM-DD_HHPM.pdf. Newer: ..._HH_MMPM.pdf.
Usage: python3 download_injury_reports.py games.csv out_dir
"""
import os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_"
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SLOTS = ["11AM", "01PM", "03PM", "05PM", "06PM", "07PM", "08PM", "09PM"]


def name_variants(day, slot):
    hh, ap = slot[:2], slot[2:]
    return [f"{day}_{slot}", f"{day}_{hh}_30{ap}", f"{day}_{hh}_00{ap}"]


def fetch(day, slot):
    dest = os.path.join(OUT, f"{day}_{slot}.pdf")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return "cached"
    for v in name_variants(day, slot):
        r = subprocess.run(["curl", "-s", "-m", "40", "--retry", "2", "-o", dest, "-w", "%{http_code}", BASE + v + ".pdf"],
                           capture_output=True, text=True)
        if r.stdout == "200" and os.path.getsize(dest) > 1000:
            return "ok"
    if os.path.exists(dest): os.remove(dest)
    return "missing"


g = pd.read_csv(sys.argv[1], parse_dates=["date"])
days = sorted(set(g.date.dt.date))
jobs = []
for d in days:
    prev = (d - pd.Timedelta(days=1)).isoformat()
    jobs += [(prev, "08PM"), (prev, "09PM")]
    jobs += [(d.isoformat(), s) for s in SLOTS]
jobs = sorted(set(jobs))
print("game days", len(days), "files to fetch", len(jobs), flush=True)
with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(lambda j: fetch(*j), jobs))
log = pd.DataFrame(jobs, columns=["day", "slot"]); log["status"] = res
log.to_csv(os.path.join(OUT, "_download_log.csv"), index=False)
print(log.status.value_counts().to_dict())
