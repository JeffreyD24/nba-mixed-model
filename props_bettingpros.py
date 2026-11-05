"""
Past NBA player-prop lines from BettingPros' public web API (the same calls their site makes; free, no account). Personal research use,
paced politely (about 1 request per 1.5 s).
For every NBA date in data/odds_history/schedule.csv plus 2026-27 to yesterday: every game's points, rebounds, assists and threes props,
per book (DraftKings, FanDuel, BetMGM, Caesars, BetRivers, bet365, Fanatics, ... and the BettingPros consensus):
  - each book's last line + price before the game (with its update time) = the close
  - the opening line + price + which book + when it was first posted
Probe (Nov 5, 2026): coverage from Dec 2021 (DraftKings only then), many books from 2023-24.
  python props_bettingpros.py WORKDIR [--from 2021-12-01] [--to 2026-04-12] [--max-dates 40] [--newest-first]
Writes data/props_history/bettingpros/{date}.csv.gz (one row per game x market x player x side x book); dates saved are skipped.
"""
import os, sys, json, time, random, urllib.request, urllib.parse, urllib.error
import datetime as dt
import pandas as pd

W = os.path.abspath(sys.argv[1])
ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = os.path.join(W, "data", "props_history", "bettingpros"); os.makedirs(OUT, exist_ok=True)
KEY = "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh"      # BettingPros' public web-client key (what bettingpros.com itself sends)
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "application/json",
       "x-api-key": KEY, "Origin": "https://www.bettingpros.com", "Referer": "https://www.bettingpros.com/"}
MARKETS = {156: "pts", 157: "reb", 151: "ast", 162: "fg3m"}
BOOKS = {0: "consensus", 12: "draftkings", 10: "fanduel", 19: "betmgm", 13: "caesars", 18: "betrivers", 24: "bet365", 14: "fanatics",
         33: "thescore", 49: "hardrock", 15: "sugarhouse", 27: "partycasino", 2: "pinnacle", 36: "underdog", 37: "prizepicks", 63: "sleeper"}


def get(path, params):
    url = f"https://api.bettingpros.com/v3/{path}?" + urllib.parse.urlencode(params)
    for i in range(5):
        time.sleep(1.2 + random.random() * 0.6)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=40) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504): time.sleep(20 * (i + 1)); continue
            raise
        except Exception:
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"gave up on {path}")


def one_date(day):
    ev = get("events", dict(sport="NBA", date=day)).get("events", [])
    if not ev: return pd.DataFrame(), 0
    info = {e["id"]: e for e in ev}
    rows = []
    for k in range(0, len(ev), 3):
        ids = ":".join(str(e["id"]) for e in ev[k:k + 3]); page = 1
        while True:
            d = get("offers", dict(sport="NBA", market_id=":".join(map(str, MARKETS)), event_id=ids, location="ALL", limit=50, page=page))
            for o in d.get("offers", []):
                e = info.get(o.get("event_id"), {}); p = (o.get("participants") or [{}])[0]
                for s in o.get("selections", []):
                    op = s.get("opening_line") or {}
                    for b in s.get("books", []):
                        for ln in b.get("lines", []):
                            if not ln.get("main", True): continue
                            rows.append(dict(date=day, event_id=o.get("event_id"), home=e.get("home"), away=e.get("visitor"),
                                             scheduled=e.get("scheduled"), stat=MARKETS.get(o.get("market_id")), bp_player_id=o.get("player_id"),
                                             player=p.get("name"), team=(p.get("player") or {}).get("team"), side=s.get("selection"),
                                             book=BOOKS.get(b.get("id"), str(b.get("id"))), line=ln.get("line"), price=ln.get("cost"),
                                             updated=ln.get("updated"), open_line=op.get("line"), open_price=op.get("cost"),
                                             open_book=BOOKS.get(op.get("book_id"), str(op.get("book_id"))), open_time=op.get("created")))
            pg = d.get("_pagination") or {}
            if page >= (pg.get("total_pages") or 1): break
            page += 1
    return pd.DataFrame(rows), len(ev)


def main():
    S = pd.read_csv(os.path.join(W, "data", "odds_history", "schedule.csv"))
    dates = sorted(set(S[S.sport == "nba"].date))
    y = (dt.date.today() - dt.timedelta(days=1)); d0 = dt.date(2026, 10, 20)
    while d0 <= y: dates.append(str(d0)); d0 += dt.timedelta(days=1)
    lo, hi = ARG("--from", "2021-12-01"), ARG("--to", str(y))
    todo = [d for d in sorted(set(dates)) if lo <= d <= hi and not os.path.exists(os.path.join(OUT, f"{d}.csv.gz"))]
    if "--newest-first" in sys.argv: todo = todo[::-1]
    todo = todo[: int(ARG("--max-dates", "40"))]
    if not todo: print("all dates already saved"); return
    for d in todo:
        try:
            R, n = one_date(d)
        except Exception as e:
            print(f"{d}: failed ({e}); will retry next run", flush=True); continue
        R.to_csv(os.path.join(OUT, f"{d}.csv.gz"), index=False)
        print(f"{d}: {n} games, {len(R)} rows, {R.bp_player_id.nunique() if len(R) else 0} players, books {sorted(R.book.unique()) if len(R) else []}", flush=True)


if __name__ == "__main__":
    main()
