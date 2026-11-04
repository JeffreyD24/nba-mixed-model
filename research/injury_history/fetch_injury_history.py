"""Backfill EVERY official NBA injury report posted on game days, 2021-22..2025-26, and parse them.
Runs in GitHub Actions (nba.com is not reachable from the Claude workspace). PDFs are not committed; only the parsed CSVs.

For each game date D: every report file from 10 AM to 10 PM ET on D, trying :00, :15, :30, :45 and the old "HHPM" name, plus the
night before (D-1) 5 PM to 10 PM. Each file that exists is saved under its own name; the report's own printed time ("Injury Report:
MM/DD/YY HH:MM PM") is parsed into `as_of`, so timing does not depend on the file name.
  python3 fetch_injury_history.py SEASON          (SEASON = year the season ends, e.g. 2024)
Writes reports_SEASON.csv.gz (one row per report file x listed player) and download_log_SEASON.csv."""
import os, sys, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from parse_injury_reports import parse
BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_"
season = int(sys.argv[1])
G = pd.read_csv(os.path.join(ROOT, "data", "training_games.csv"))
days = sorted(set(pd.to_datetime(G[G.season == season].date).dt.date))

def names(day, hour24):
    h12 = hour24 % 12 or 12; ap = "AM" if hour24 < 12 else "PM"; hh = f"{h12:02d}"
    return [f"{day}_{hh}{ap}"] + [f"{day}_{hh}_{mm}{ap}" for mm in ("00", "15", "30", "45")]
jobs = []
for d in days:
    prev = (pd.Timestamp(d) - pd.Timedelta(days=1)).date().isoformat()
    jobs += [n for h in range(17, 23) for n in names(prev, h)]
    jobs += [n for h in range(10, 23) for n in names(d.isoformat(), h)]
jobs = sorted(set(jobs))
tmp = tempfile.mkdtemp()

def fetch(n):
    dest = os.path.join(tmp, n + ".pdf")
    for attempt in range(3):
        r = subprocess.run(["curl", "-s", "-m", "30", "-o", dest, "-w", "%{http_code}", BASE + n + ".pdf"], capture_output=True, text=True)
        code = r.stdout.strip()
        if code == "200" and os.path.getsize(dest) > 1000: return n, "ok"
        if code in ("403", "404"): break
    if os.path.exists(dest): os.remove(dest)
    return n, f"missing:{code}"
print(f"season {season}: {len(days)} game days, {len(jobs)} names to try", flush=True)
with ThreadPoolExecutor(12) as ex: res = list(ex.map(fetch, jobs))
log = pd.DataFrame(res, columns=["name", "status"]); log.to_csv(os.path.join(HERE, f"download_log_{season}.csv"), index=False)
ok = [n for n, s in res if s == "ok"]
print("download:", log.status.value_counts().to_dict(), flush=True)
rows = []
for n in ok:
    for r in parse(os.path.join(tmp, n + ".pdf")): rows.append(r)
df = pd.DataFrame(rows, columns=["snapshot", "as_of", "game_date", "game_time_et", "matchup", "team", "player", "status"])
df.to_csv(os.path.join(HERE, f"reports_{season}.csv.gz"), index=False)
per_day = df.groupby(df.snapshot.str[:10]).snapshot.nunique()
print(f"parsed {len(ok)} files -> {len(df)} rows; files per calendar day median {per_day.median():.0f}; "
      f"as_of missing {df.as_of.isna().mean():.1%}; rows missing team/date/matchup {df[['team','game_date','matchup']].isna().any(axis=1).mean():.1%}")
print(df.status.value_counts().to_dict())
