"""
Pre-game line recorder (every minute from alert_loop.sh): Action Network lines for every game that has NOT started yet, every book,
every period and market (full game, halves/quarters/periods, team totals). Action Network refreshes about every 30 seconds, so one
poll a minute catches nearly every move from the moment a line is first listed until the game starts (live.py takes over in-game).
Rows are written only when a value changed, so each row marks the first poll that saw it.

  python pregame.py WORKDIR

Writes research/pregame/YYYY-MM-DD.csv (game date, ET): seen_at_et, an_game_id, date, start_et, away, home, book, period, market,
side, value, odds, line_status.  Dates today and tomorrow every poll; the later dates (2-3 days ahead) only on every fifth minute.
"""
import os, sys, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
import espn                                                   # noqa: E402
import research                                               # noqa: E402

ET = ZoneInfo("America/New_York")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
AN_BOOKS = research.AN_BOOKS
AN_SPORT = "nba"
PERIOD_REQUESTS = ["event,firsthalf,secondhalf,firstquarter,secondquarter,thirdquarter,fourthquarter"]
FAR_DAYS = 3
TEAM = lambda x: espn.ESPN2.get(x.get("abbr"), str(x.get("abbr")).lower())


def fetch(day):
    """list of raw Action Network games for one date"""
    ds = day.strftime("%Y%m%d"); out = []
    for ps in PERIOD_REQUESTS:
        try:
            d = research._an_get(f"https://api.actionnetwork.com/web/v2/scoreboard/{AN_SPORT}?bookIds={','.join(map(str, AN_BOOKS))}"
                                 f"&periods={ps}&date={ds}")
        except Exception as e:
            print("Action Network unavailable:", ds, ps, type(e).__name__, str(e)[:60]); continue
        out += d.get("games", [])
    return out


def rows_for(games):
    rows, seen = [], set()
    for g in games:
        if g.get("status") not in ("scheduled", None): continue          # started games belong to live.py
        t = {x["id"]: TEAM(x) for x in g.get("teams", [])}
        home, away = t.get(g["home_team_id"]), t.get(g["away_team_id"])
        try: start = pd.to_datetime(g.get("start_time"), utc=True).tz_convert(ET).tz_localize(None)
        except Exception: continue
        day = str(start.date())
        for bid, m in (g.get("markets") or {}).items():
            for per, mk in (m or {}).items():
                for typ, outs in (mk or {}).items():
                    for o in outs or []:
                        side = o.get("side"); typ_ = typ
                        if typ == "core_bet_type_6_team_score":
                            typ_ = "team_total"; side = f"{'home' if o.get('team_id') == g['home_team_id'] else 'away'}_{side}"
                        k = (g["id"], bid, per, typ_, side)
                        if k in seen: continue
                        seen.add(k)
                        rows.append(dict(seen_at_et=str(NOW)[:19], an_game_id=g["id"], date=day, start_et=str(start)[:16], away=away, home=home,
                                         book=AN_BOOKS.get(int(bid), bid), period=per, market=typ_, side=side, value=o.get("value"),
                                         odds=o.get("odds"), line_status=o.get("line_status")))
    return rows


def main():
    days = list(range(0, 2)) + (list(range(2, FAR_DAYS + 1)) if NOW.minute % 5 == 0 else [])
    rows = []
    for k in days:
        rows += rows_for(fetch(NOW + pd.Timedelta(days=k)))
    by_day = {}
    for r in rows: by_day.setdefault(r["date"], []).append(r)
    research.init(W); n = 0
    d = os.path.join(W, "research", "pregame"); os.makedirs(d, exist_ok=True)
    for day, rr in by_day.items():
        n += research._append_changed(os.path.join(d, f"{day}.csv"), rr, ["an_game_id", "book", "period", "market", "side"],
                                      ["value", "odds", "line_status"])
    print(f"{NOW:%a %H:%M:%S} ET pregame: {len(rows)} prices seen, {n} new rows")


if __name__ == "__main__":
    main()
