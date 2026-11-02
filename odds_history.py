"""
Historical odds from The Odds API (paid; key in the GitHub secret ODDS_API_KEY, never printed or saved).
For every game date in data/odds_history/schedule.csv: snapshots of moneyline, spread and total at 10 books (DraftKings,
FanDuel, BetMGM, Caesars, BetRivers, Bovada, BetOnline, LowVig, MyBookie, and Pinnacle as the sharp benchmark) from before the
lines open until each game starts:
  - hourly from the day before (NBA, NHL) or every 3 hours from 8 days before (NFL), hourly on game day
  - each batch of new lines is pinned down to about 10 minutes after it first appears (the opener), then snapshots at
    +15, +30 and +60 minutes (how fast the edge disappears)
  - one snapshot just before each start time (the close)
Each request returns every game of that sport at that moment, so one request covers a whole slate.
Cost: 10 credits per market per request -> 30 per snapshot. --dry-run prints the plan and the estimated credits only.

  python odds_history.py WORKDIR --sport nba --from 2021-10-19 --to 2022-04-10 [--dry-run] [--min-credits 200000] [--max-dates N]
  python odds_history.py WORKDIR --check        (free: confirms the key and shows credits left)
Writes data/odds_history/{sport}/{date}.csv.gz (one row per snapshot x game x book x outcome) and skips dates already saved.
"""
import os, sys, json, gzip, time, urllib.request, urllib.parse, urllib.error
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1])
ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SPORT = ARG("--sport", "nba")
KEYS = {"nba": "basketball_nba", "nhl": "icehockey_nhl", "nfl": "americanfootball_nfl"}
BOOKS = "draftkings,fanduel,betmgm,williamhill_us,betrivers,bovada,betonlineag,lowvig,mybookieag,pinnacle"
MARKETS = "h2h,spreads,totals"
COST = 10 * 3
ET, UTC = ZoneInfo("America/New_York"), dt.timezone.utc
OUT = os.path.join(W, "data", "odds_history", SPORT); os.makedirs(OUT, exist_ok=True)
DRY = "--dry-run" in sys.argv
MIN_CREDITS = int(ARG("--min-credits", "200000"))       # stop before the plan runs low
API = "https://api.the-odds-api.com/v4"
state = dict(remaining=None, used=0, calls=0)


def get(path, params):
    key = os.environ.get("ODDS_API_KEY")
    if not key: sys.exit("ODDS_API_KEY is not set (add it as a GitHub repository secret).")
    url = f"{API}{path}?" + urllib.parse.urlencode(dict(params, apiKey=key))
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                state["remaining"] = int(r.headers.get("x-requests-remaining", state["remaining"] or 0))
                state["used"] += int(r.headers.get("x-requests-last", 0) or 0); state["calls"] += 1
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): sys.exit(f"The Odds API refused the key (HTTP {e.code}).")
            if e.code == 422: return None                      # no snapshot at that time
            time.sleep(5 * (i + 1))
        except Exception:
            time.sleep(5 * (i + 1))
    return None


def snapshot(t):
    """all games and prices at UTC time t (the API returns the latest snapshot at or before t)"""
    if DRY: state["calls"] += 1; return {"timestamp": t.isoformat(), "data": []}
    if state["remaining"] is not None and state["remaining"] < MIN_CREDITS:
        sys.exit(f"Stopping: {state['remaining']} credits left (floor {MIN_CREDITS}).")
    return get(f"/historical/sports/{KEYS[SPORT]}/odds", dict(regions="us", bookmakers=BOOKS, markets=MARKETS, oddsFormat="american",
                                                            dateFormat="iso", date=t.strftime("%Y-%m-%dT%H:%M:%SZ")))


def rows_of(js, day):
    out = []
    ts = js.get("timestamp")
    for ev in js.get("data", []) or []:
        ct = pd.Timestamp(ev["commence_time"]).tz_convert(ET)
        if str(ct.date()) != day: continue
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                for o in mk.get("outcomes", []):
                    out.append(dict(snapshot_utc=ts, event_id=ev["id"], commence_et=str(ct.tz_localize(None)), home=ev["home_team"],
                                    away=ev["away_team"], book=bk["key"], market=mk["key"], outcome=o.get("name"), price=o.get("price"),
                                    point=o.get("point"), book_last_update=mk.get("last_update")))
    return out


def plan_day(day):
    d = pd.Timestamp(day).tz_localize(ET)
    if SPORT == "nfl":
        a = [d - pd.Timedelta(days=8) + pd.Timedelta(hours=h) for h in range(10, 8 * 24, 3)]
    else:
        a = [d - pd.Timedelta(days=1) + pd.Timedelta(hours=h) for h in range(8, 24)]
    a += [d + pd.Timedelta(hours=h) for h in range(0, 24)]
    return sorted(set(x.tz_convert(UTC) for x in a if x <= d + pd.Timedelta(hours=23, minutes=30)))


def do_day(day):
    path = os.path.join(OUT, f"{day}.csv.gz")
    if os.path.exists(path): return 0
    snaps, seen = {}, {}                                      # time -> rows; event -> first snapshot time it appeared
    for t in plan_day(day):
        js = snapshot(t)
        if js is None: continue
        r = rows_of(js, day); snaps[t] = r
        for x in r: seen.setdefault(x["event_id"], t)
    if not DRY:
        # pin each batch of openers down to ~10 minutes: bisect between the last snapshot without them and the first with
        times = sorted(snaps)
        for first in sorted(set(seen.values())):
            i = times.index(first)
            if i == 0: continue
            lo, hi = times[i - 1], first
            ids = {e for e, t in seen.items() if t == first}
            while (hi - lo) > pd.Timedelta(minutes=12):
                mid = lo + (hi - lo) / 2; js = snapshot(mid)
                if js is None: break
                r = rows_of(js, day); snaps[mid] = r
                if ids & {x["event_id"] for x in r}: hi = mid
                else: lo = mid
            for k in (15, 30, 60):                           # how fast the opener moves
                t = hi + pd.Timedelta(minutes=k)
                if not any(abs((t - s).total_seconds()) < 300 for s in snaps):
                    js = snapshot(t)
                    if js is not None: snaps[t] = rows_of(js, day)
        # the close: just before each start time
        starts = sorted({pd.Timestamp(x["commence_et"]).tz_localize(ET).tz_convert(UTC) for r in snaps.values() for x in r})
        for s in starts:
            t = s - pd.Timedelta(minutes=3)
            if not any(abs((t - u).total_seconds()) < 180 for u in snaps):
                js = snapshot(t)
                if js is not None: snaps[t] = rows_of(js, day)
        R = pd.DataFrame([x for r in snaps.values() for x in r]).drop_duplicates()
        if len(R): R.to_csv(path, index=False, compression="gzip")
        else: open(path + ".empty", "w").close()
    return len(snaps)


def check():
    """free request: confirms the key works and shows the credits left"""
    js = get("/sports", {})
    print(f"Key works: {len(js or [])} sports listed, {state['remaining']:,} credits left this month.")


def main():
    if "--check" in sys.argv: check(); return
    S = pd.read_csv(os.path.join(W, "data", "odds_history", "schedule.csv"))
    days = sorted(S[(S.sport == SPORT) & (S.date >= ARG("--from", "2000-01-01")) & (S.date <= ARG("--to", "2100-01-01"))].date)
    if DRY:
        n = sum(len(plan_day(d)) for d in days) + len(days) * (10 if SPORT != "nfl" else 12)   # + openers and closes (estimate)
        print(f"{SPORT} {days[0] if days else '-'} to {days[-1] if days else '-'}: {len(days)} game dates, about {n} snapshots, "
              f"about {n * COST:,} credits"); return
    t0 = time.time()
    todo = [d for d in days if not (os.path.exists(os.path.join(OUT, f"{d}.csv.gz")) or os.path.exists(os.path.join(OUT, f"{d}.csv.gz.empty")))]
    todo = todo[:int(ARG("--max-dates", "100000"))]
    if not todo: print(f"{SPORT}: all {len(days)} dates already saved."); return
    for i, d in enumerate(todo):
        do_day(d)
        if i % 10 == 0:
            print(f"{d}: {i + 1}/{len(todo)} dates, {state['calls']} requests, {state['used']:,} credits used, "
                  f"{state['remaining']:,} left, {time.time() - t0:.0f}s", flush=True)
        if time.time() - t0 > 5 * 3600: print("Time limit for this run; the next run continues."); break
    print(f"Done: {state['calls']} requests, {state['used']:,} credits used, {state['remaining']} left.")


if __name__ == "__main__":
    main()
