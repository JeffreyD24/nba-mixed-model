"""
College football: DraftKings' (and FanDuel's, Pinnacle's) FIRST line for every FBS game, 2024-25 weeks 4+, from The Odds API
historical snapshots (paid; key = GitHub secret ODDS_API_KEY, never printed). Answers the question the NCAAF Model 1 backtest left
open: is DraftKings' own first line as beatable as Action Network's Open book? (nfl-mixed-model ncaaf/research/NCAAF_RESULTS_2026-11-05.md)
Per week (data/odds_history/ncaaf/plan.csv): snapshots every 3 h from Saturday 6 PM to Monday 2 PM ET before the week; each batch of
newly posted DraftKings lines is pinned to ~20 minutes by bisection; games already posted at the window start are traced back
12 h at a time (up to 6 steps). Spreads + totals only (20 credits per snapshot).
  python ncaaf_openers.py WORKDIR [--max-weeks N] [--dry-run]       (python ncaaf_openers.py WORKDIR --check: free key check)
Writes data/odds_history/ncaaf/{season}_{week}.csv.gz: one row per game x book x market x outcome at the first snapshot DraftKings
had the game, plus the time each book first had it."""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
import pandas as pd
W = os.path.abspath(sys.argv[1]); ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = os.path.join(W, "data", "odds_history", "ncaaf"); PLAN = os.path.join(OUT, "plan.csv")
API = "https://api.the-odds-api.com/v4"; DRY = "--dry-run" in sys.argv; FLOOR = int(ARG("--min-credits", "150000"))
st = dict(remaining=None, used=0, calls=0)


def get(path, params):
    key = os.environ.get("ODDS_API_KEY")
    if not key: sys.exit("ODDS_API_KEY is not set.")
    url = f"{API}{path}?" + urllib.parse.urlencode(dict(params, apiKey=key))
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                st["remaining"] = int(r.headers.get("x-requests-remaining", st["remaining"] or 0))
                st["used"] += int(r.headers.get("x-requests-last", 0) or 0); st["calls"] += 1
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): sys.exit(f"The Odds API refused the key (HTTP {e.code}).")
            if e.code == 422: return None
            time.sleep(5 * (i + 1))
        except Exception:
            time.sleep(5 * (i + 1))
    return None


def snap(t, lo, hi):
    """{event_id: {book: {market: [outcomes]}}, plus meta} for games starting in [lo, hi]"""
    if DRY: st["calls"] += 1; return {}
    if st["remaining"] is not None and st["remaining"] < FLOOR: sys.exit(f"Stopping: {st['remaining']} credits left (floor {FLOOR}).")
    js = get("/historical/sports/americanfootball_ncaaf/odds", dict(regions="us", bookmakers="draftkings,fanduel,pinnacle",
             markets="spreads,totals", oddsFormat="american", dateFormat="iso", date=t.strftime("%Y-%m-%dT%H:%M:%SZ")))
    out = {}
    for ev in (js or {}).get("data", []) or []:
        ct = pd.Timestamp(ev["commence_time"])
        if not (lo <= ct <= hi): continue
        out[ev["id"]] = dict(home=ev["home_team"], away=ev["away_team"], commence=ev["commence_time"],
                             books={b["key"]: {m["key"]: m["outcomes"] for m in b.get("markets", [])} for b in ev.get("bookmakers", [])})
    return out


def has_dk(e): return "spreads" in e["books"].get("draftkings", {}) or "totals" in e["books"].get("draftkings", {})


def do_week(r):
    path = os.path.join(OUT, f"{r.season}_{r.week}.csv.gz")
    if os.path.exists(path): return False
    ET = "America/New_York"
    lo = pd.Timestamp(r.games_from).tz_localize(ET).tz_convert("UTC"); hi = (pd.Timestamp(r.games_to) + pd.Timedelta(days=1)).tz_localize(ET).tz_convert("UTC")
    a, b = pd.Timestamp(r.win_start).tz_convert("UTC"), pd.Timestamp(r.win_end).tz_convert("UTC")
    S = {}
    t = a
    while t <= b: S[t] = snap(t, lo, hi); t += pd.Timedelta(hours=3)
    if DRY: return True
    first = {}
    for tt in sorted(S):
        for e, v in S[tt].items():
            if has_dk(v): first.setdefault(e, tt)
    # games already posted at the window start: step back 12 h at a time
    early = {e for e, tt in first.items() if tt == a}; t = a; steps = 0
    while early and steps < 6:
        t -= pd.Timedelta(hours=12); steps += 1; S[t] = snap(t, lo, hi)
        still = {e for e in early if e in S[t] and has_dk(S[t][e])}
        for e in still: first[e] = t
        early = still
    # bisect each batch of new DraftKings lines to ~20 minutes
    times = sorted(S)
    for f in sorted(set(first.values())):
        i = times.index(f)
        if i == 0: continue
        ids = {e for e, tt in first.items() if tt == f}; L, H = times[i - 1], f
        while H - L > pd.Timedelta(minutes=22):
            m = L + (H - L) / 2; S[m] = snap(m, lo, hi); got = {e for e in ids if e in S[m] and has_dk(S[m][e])}
            if got:
                for e in got: first[e] = m
                ids2 = ids - got
                H = m if not ids2 else H
                if ids2: L = m; ids = ids2
            else: L = m
    rows = []
    for e, tt in first.items():
        v = S[tt][e]
        firsts = {bk: min((x for x in S if e in S[x] and bk in S[x][e]["books"]), default=None) for bk in ("draftkings", "fanduel", "pinnacle")}
        for bk, mk in v["books"].items():
            for m, outs in mk.items():
                for o in outs:
                    rows.append(dict(season=r.season, week=r.week, event_id=e, home=v["home"], away=v["away"], commence=v["commence"],
                                     dk_first_seen_utc=str(tt), book=bk, book_first_seen_utc=str(firsts.get(bk)), market=m,
                                     outcome=o.get("name"), point=o.get("point"), price=o.get("price")))
    pd.DataFrame(rows).to_csv(path, index=False, compression="gzip")
    print(f"{r.season} week {r.week}: {len(first)} games with a DraftKings first line; credits used so far {st['used']}, left {st['remaining']}", flush=True)
    return True


if __name__ == "__main__":
    if "--check" in sys.argv:
        get("/sports", {}); print("key OK; credits left", st["remaining"]); sys.exit(0)
    P = pd.read_csv(PLAN); n = 0
    for r in P.itertuples():
        if do_week(r): n += 1
        if n >= int(ARG("--max-weeks", "99")): break
    if DRY: print(f"dry run: {st['calls']} base snapshots ~ {st['calls'] * 20} credits before bisection/back-steps (~x2 total)")
    print("done" if n == 0 else f"{n} weeks processed")
