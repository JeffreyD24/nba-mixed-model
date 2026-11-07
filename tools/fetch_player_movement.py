"""NBA player movement (trades, signings, waivers) from NBA.com's own JSON (Nov 7, 2026; RULE 13 collector).

Source: the file NBA.com's transactions page loads, stats.nba.com/js/data/playermovement/NBA_Player_Movement.json (every transaction
since ~2015: date, type, team, player, description). stats.nba.com refuses some cloud IPs, so this runs on GitHub Actions
(.github/workflows/nba-player-movement.yml) and tries a few addresses with browser headers; it logs which one answered.
Writes data/external/nba_player_movement/{NBA_Player_Movement.json, transactions.csv, fetch_log.csv}; files change only when
the data changes (sorted, no timestamps inside), so quiet days make no commit except the one-line log.
  python tools/fetch_player_movement.py <repo_root>"""
import os, sys, json, time, urllib.request, csv, io, gzip
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
OUT = os.path.join(ROOT, "data", "external", "nba_player_movement"); os.makedirs(OUT, exist_ok=True)
URLS = ["https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json",
        "https://www.nba.com/stats/js/data/playermovement/NBA_Player_Movement.json"]
HEAD = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip",
        "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com"}


def get(url):
    req = urllib.request.Request(url, headers=HEAD)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip": raw = gzip.decompress(raw)
        return r.status, raw


def rows_of(d):
    """find the list of transaction rows wherever it sits; returns (columns, list of dicts)"""
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict) and "columns" in v and "rows" in v:
                return list(v["columns"]), [dict(zip(v["columns"], r)) if isinstance(r, list) else r for r in v["rows"]]
            if isinstance(v, list) and v and isinstance(v[0], dict): return list(v[0].keys()), v
            got = rows_of(v)
            if got[1]: return got
    return [], []


log, data, used = [], None, None
for url in URLS:
    for attempt in range(3):
        try:
            st, raw = get(url); d = json.loads(raw)
            cols, rows = rows_of(d)
            log.append((url, st, len(rows), ""));
            if rows: data, used = (cols, rows, d), url
            break
        except Exception as e:
            log.append((url, None, 0, f"{type(e).__name__}: {str(e)[:120]}")); time.sleep(5 * (attempt + 1))
    if data: break

now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
lp = os.path.join(OUT, "fetch_log.csv"); new_log = not os.path.exists(lp)
with open(lp, "a", newline="") as f:
    w = csv.writer(f)
    if new_log: w.writerow(["fetched_at_utc", "url", "http_status", "rows", "error"])
    for r in log: w.writerow([now, *r])
for r in log: print(r)
if not data: sys.exit("no address returned transaction rows (see fetch_log.csv)")

cols, rows, d = data
json.dump(d, open(os.path.join(OUT, "NBA_Player_Movement.json"), "w"), sort_keys=True, indent=0)
keys = cols or sorted({k for r in rows for k in r})
rows = sorted(rows, key=lambda r: tuple(str(r.get(k, "")) for k in keys))
buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
open(os.path.join(OUT, "transactions.csv"), "w").write(buf.getvalue())
print(f"saved {len(rows)} transactions from {used}; columns {keys}")
