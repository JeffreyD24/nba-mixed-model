"""
Fetch NFL timestamped information data from nflverse (free, public) and write compact combined files.

    python3 -I fetch_nfl.py            # run from anywhere; writes next to this script, in ./nfl/

Outputs (gzip CSV, in nfl/):
  injuries_2009_2026.csv.gz   one row per player-week: final game-status (report_status) and the last practice status
                              (practice_status), plus date_modified (UTC) and snapshot_et / snapshot_weekday (our addition).
                              NOT a Wed/Thu/Fri practice log: one snapshot per player-week, mostly stamped Friday afternoon.
  snap_counts_2013_2026.csv.gz  per player-game offense/defense/special-teams snaps (after the game; use LAST week's only)
  games_2009_2026.csv.gz      schedule, scores, closing-ish lines (spread_line/total_line), roof, surface and ACTUAL game-time
                              temp/wind (do not use as opener-time weather: that is the leak found in the Nov 3 audit)
  rosters_2009_2026.csv.gz    season rosters (gsis_id, position, team, status)
  players.csv.gz              player id map
"""
import io, os, sys, time, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "nfl"); os.makedirs(OUT, exist_ok=True)
B = "https://github.com/nflverse/nflverse-data/releases/download"


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sports-research-fetch"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            if k == tries - 1:
                print("FAILED", url, type(e).__name__, str(e)[:80]); return None
            time.sleep(3 * (k + 1))


def csv(url):
    b = get(url)
    if b is None or len(b) < 400:           # nflverse answers tiny stubs for seasons that do not exist
        return None
    return pd.read_csv(io.BytesIO(b), low_memory=False)


def combine(name, folder, fname, years, post=None):
    frames = []
    for y in years:
        d = csv(f"{B}/{folder}/{fname.format(y=y)}")
        if d is None:
            print(f"  {name} {y}: not available"); continue
        if "season" not in d.columns:
            d["season"] = y
        frames.append(d)
        print(f"  {name} {y}: {len(d):,} rows")
    out = pd.concat(frames, ignore_index=True)
    if post: out = post(out)
    out.to_csv(os.path.join(OUT, f"{name}.csv.gz"), index=False, compression="gzip")
    print(f"{name}: {len(out):,} rows -> {name}.csv.gz")
    return out


def add_snapshot(d):
    if "date_modified" in d:
        t = pd.to_datetime(d["date_modified"], utc=True, errors="coerce").dt.tz_convert("America/New_York")
        d["snapshot_et"] = t.dt.strftime("%Y-%m-%d %H:%M")
        d["snapshot_weekday"] = t.dt.day_name()
    return d


if __name__ == "__main__":
    this_year = 2026
    combine("injuries_2009_2026", "injuries", "injuries_{y}.csv", range(2009, this_year + 1), add_snapshot)
    combine("snap_counts_2013_2026", "snap_counts", "snap_counts_{y}.csv", range(2012, this_year + 1))
    combine("rosters_2009_2026", "rosters", "roster_{y}.csv", range(2009, this_year + 1))
    g = csv(f"{B}/schedules/games.csv")
    g = g[g.season >= 2009]; g.to_csv(os.path.join(OUT, "games_2009_2026.csv.gz"), index=False, compression="gzip")
    print(f"games: {len(g):,} rows")
    p = csv(f"{B}/players/players.csv")
    p.to_csv(os.path.join(OUT, "players.csv.gz"), index=False, compression="gzip")
    print(f"players: {len(p):,} rows")
