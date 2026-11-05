"""
Past NBA player-prop lines from The Odds API (paid; key in the GitHub secret ODDS_API_KEY, never printed or saved), for the props backtest.
Approved budget (Nov 5, 2026): one season (2025-26), two snapshots per game, about 98k credits.
For every 2025-26 game date in data/odds_history/schedule.csv:
  - the events list at 11 AM ET (1 credit)
  - per game: points, rebounds, assists, threes at DraftKings, FanDuel, Pinnacle, BetMGM, Caesars, BetRivers
      'am'    = the snapshot at 11 AM ET (the bet line)
      'close' = the snapshot 10 minutes before tip (the close)
    40 credits per snapshot (4 markets x 1 region of up to 10 books)
Stops when credits left drop under --min-credits (default 98000, so the live recorder keeps the rest).
  python props_history.py WORKDIR [--from 2025-10-21] [--to 2026-04-12] [--max-dates 20] [--min-credits 98000] [--dry-run]
Writes data/props_history/nba/{date}.csv.gz; dates already saved are skipped.
"""
import os, sys, json, gzip, urllib.request, urllib.parse, urllib.error
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1])
ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = os.path.join(W, "data", "props_history", "nba"); os.makedirs(OUT, exist_ok=True)
API = "https://api.the-odds-api.com/v4"
BOOKS = "draftkings,fanduel,pinnacle,betmgm,williamhill_us,betrivers"
MARKETS = "player_points,player_rebounds,player_assists,player_threes"
ET, UTC = ZoneInfo("America/New_York"), dt.timezone.utc
MIN = int(ARG("--min-credits", "98000")); DRY = "--dry-run" in sys.argv
state = dict(left=None, used=0)


def get(path, params):
    key = os.environ.get("ODDS_API_KEY")
    if not key: sys.exit("ODDS_API_KEY is not set")
    url = f"{API}{path}?" + urllib.parse.urlencode(dict(params, apiKey=key))
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                state["left"] = int(r.headers.get("x-requests-remaining", 0) or 0); state["used"] += int(r.headers.get("x-requests-last", 0) or 0)
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (404, 422): return None
            if i == 2: raise
        except Exception:
            if i == 2: raise
    return None


def iso(t): return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def rows_from(od, snap, ev):
    out = []
    data = (od or {}).get("data") or {}
    for b in data.get("bookmakers", []):
        for m in b.get("markets", []):
            for o in m.get("outcomes", []):
                out.append(dict(snap=snap, snap_ts=od.get("timestamp"), event_id=ev["id"], commence=ev["commence_time"],
                                home=ev["home_team"], away=ev["away_team"], book=b["key"], market=m["key"],
                                player=o.get("description"), side=o.get("name"), point=o.get("point"), price=o.get("price"),
                                book_update=m.get("last_update")))
    return out


def main():
    S = pd.read_csv(os.path.join(W, "data", "odds_history", "schedule.csv"))
    lo, hi = ARG("--from", "2025-10-21"), ARG("--to", "2026-04-12")
    dates = sorted(d for d in S[S.sport == "nba"].date if lo <= d <= hi and not os.path.exists(os.path.join(OUT, f"{d}.csv.gz")))
    dates = dates[: int(ARG("--max-dates", "20"))]
    if not dates: print("all dates already saved"); return
    if DRY: print(f"{len(dates)} dates; about {len(dates) * 7 * 80 + len(dates)} credits"); return
    for d in dates:
        am = dt.datetime.fromisoformat(d).replace(hour=11, tzinfo=ET)
        evs = (get("/historical/sports/basketball_nba/events", dict(date=iso(am))) or {}).get("data", [])
        day = [e for e in evs if pd.Timestamp(e["commence_time"]).tz_convert(ET).strftime("%Y-%m-%d") == d]
        R = []
        for e in day:
            if state["left"] is not None and state["left"] < MIN + 100:
                print(f"stopping: {state['left']} credits left (floor {MIN})"); break
            tip = pd.Timestamp(e["commence_time"]).to_pydatetime()
            for snap, t in (("am", am), ("close", tip - dt.timedelta(minutes=10))):
                od = get(f"/historical/sports/basketball_nba/events/{e['id']}/odds",
                         dict(regions="us", markets=MARKETS, bookmakers=BOOKS, oddsFormat="american", date=iso(t)))
                R += rows_from(od, snap, e)
        if state["left"] is not None and state["left"] < MIN + 100 and len(R) == 0:
            print(f"{d}: not saved (credit floor)"); sys.exit(3)
        pd.DataFrame(R).to_csv(os.path.join(OUT, f"{d}.csv.gz"), index=False)
        print(f"{d}: {len(day)} games, {len(R)} rows; credits used this run {state['used']}, left {state['left']}", flush=True)
        if state["left"] is not None and state["left"] < MIN + 100: sys.exit(3)


if __name__ == "__main__":
    main()
