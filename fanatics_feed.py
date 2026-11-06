"""Fanatics CT game-line feed, every sport (Nov 6, 2026; Jeffrey has a Fanatics account, the third CT sportsbook).
Fanatics' own site refuses cloud/out-of-state clients (Akamai "Access Denied"), so the lines come from Action Network's
Fanatics CT book (id 2821, same feed fanduel.py uses for FanDuel CT, book 741). Spreads, totals and moneylines, full game.

  python fanatics_feed.py WORKDIR        one tick (feed_loop.sh, about once a minute)

Only CHANGES are saved (a new line/price, or a market that disappeared = status "off"), one small file per 5 minutes:
research/feed/fanatics/<sport>/<YYYY-MM-DD>/<HHMM>.csv.gz, the same layout as research/feed/{dk,fd}/ (opener = first row seen,
close = last row before the start). Memory between ticks: WORKDIR/_tmp/fanatics_state.json (not committed).
Dates polled: today and tomorrow every minute; NFL/NCAAF also the next 8 days every 10 minutes. Never raises.
Player props: Action Network does not serve them publicly; Fanatics props come from BettingPros (book 14) in the props scripts.
"""
import os, sys, json, time, gzip, urllib.request
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1]); ET = ZoneInfo("America/New_York")
NOW = dt.datetime.now(ET).replace(tzinfo=None)
BOOK = 2821
SPORTS = {"nba": "nba", "nhl": "nhl", "nfl": "nfl", "ncaab": "ncaab", "ncaaf": "ncaaf"}
FAR = {"nfl", "ncaaf"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "application/json"}
SP = os.path.join(W, "_tmp", "fanatics_state.json"); os.makedirs(os.path.dirname(SP), exist_ok=True)
COLS = ["snap_et", "book", "sport", "event_id", "start_et", "away", "home", "market", "side", "points", "price", "status"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25) as r:
        return json.loads(r.read())


def rows_for(sport, day):
    j = get(f"https://api.actionnetwork.com/web/v2/scoreboard/{SPORTS[sport]}?bookIds={BOOK}&date={day:%Y%m%d}&periods=event")
    out = []
    for g in j.get("games", []):
        if g.get("status") not in ("scheduled", "pre_game", "pending", None) and g.get("real_status") not in ("scheduled",): continue
        teams = {t["id"]: t.get("full_name") or t.get("display_name") for t in g.get("teams", [])}
        start = pd.Timestamp(g["start_time"]).tz_convert(ET).tz_localize(None)
        m = ((g.get("markets") or {}).get(str(BOOK)) or {}).get("event") or {}
        for mk in ("spread", "total", "moneyline"):
            for o in m.get(mk) or []:
                if o.get("is_live"): continue
                out.append(dict(event_id=g["id"], start_et=f"{start:%Y-%m-%d %H:%M}", away=teams.get(g.get("away_team_id")),
                                home=teams.get(g.get("home_team_id")), market=mk, side=o.get("side"),
                                points=o.get("value"), price=o.get("odds")))
    return out


def main():
    try: S = json.load(open(SP))
    except Exception: S = {"last": {}, "due": {}}
    snap = f"{NOW:%Y-%m-%d %H:%M:%S}"; new = []; seen_now = set(); polled = set(); stats = dict(req=0, err=0)
    for sport in SPORTS:
        days = [(NOW + dt.timedelta(days=k)).date() for k in range(0, 9 if sport in FAR else 2)]
        for k, day in enumerate(days):
            key = f"{sport}|{day}"
            if time.time() < S["due"].get(key, 0): continue
            try:
                R = rows_for(sport, day); stats["req"] += 1
            except Exception:
                stats["err"] += 1; continue
            S["due"][key] = time.time() + (50 if k < 2 else 590)
            polled.add(key)
            for r in R:
                if pd.Timestamp(r["start_et"]) <= pd.Timestamp(NOW): continue
                sel = f"{sport}|{r['event_id']}|{r['market']}|{r['side']}"
                seen_now.add(sel)
                val = [r["points"], r["price"]]
                if S["last"].get(sel, {}).get("v") != val:
                    new.append(dict(snap_et=snap, book="fanatics", sport=sport, status="on", **r))
                S["last"][sel] = {"v": val, "day": f"{sport}|{day}", "row": r}
    # selections from a date just polled that vanished before their start = "off"
    for sel, d in list(S["last"].items()):
        r = d.get("row", {})
        if d.get("day") in polled and sel not in seen_now:
            if r and pd.Timestamp(r["start_et"]) > pd.Timestamp(NOW) and d.get("v") != "off":
                new.append(dict(snap_et=snap, book="fanatics", sport=sel.split("|")[0], status="off", **r)); d["v"] = "off"
        if r and pd.Timestamp(r["start_et"]) < pd.Timestamp(NOW) - pd.Timedelta(days=1): del S["last"][sel]
    if new:
        D = pd.DataFrame(new)[COLS]
        for sport, g in D.groupby("sport"):
            d = os.path.join(W, "research", "feed", "fanatics", sport, f"{NOW:%Y-%m-%d}"); os.makedirs(d, exist_ok=True)
            f = os.path.join(d, f"{NOW:%H}{NOW.minute // 5 * 5:02d}.csv.gz")
            old = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame(columns=COLS)
            pd.concat([old, g], ignore_index=True).to_csv(f, index=False, compression="gzip")
    json.dump(S, open(SP, "w"))
    print(f"fanatics feed: {stats['req']} requests, {stats['err']} errors, {len(new)} changes")


if __name__ == "__main__":
    try: main()
    except Exception as e: print("fanatics feed failed:", type(e).__name__, str(e)[:200])
