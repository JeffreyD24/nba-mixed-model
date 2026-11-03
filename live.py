"""
In-game (live) line recorder. One call = one poll of every NBA game in progress.

  python live.py WORKDIR [--include-final]

Records, for each game in progress, into research/live/YYYY-MM-DD/ (game date, ET):
  situation.csv   score, quarter, clock, last play, ESPN's live win probability (one row per poll when anything changed)
  espn_odds.csv   every odds feed ESPN lists for the game (pregame and any live provider): spread, total, moneylines, prices
  books.csv       Action Network: full game, each half and quarter spread / total / moneyline / team totals at
                  each book, with is_live (True = an in-game line)
Rows are written only when a value changed, so each row marks the first poll that saw it.

Exit code: 0 = recorded at least one game in progress; 2 = nothing in progress but a game starts within 45 minutes or
one just went to halftime/break; 3 = nothing in progress or about to start (the loop stops).
--include-final also records games that already finished (for testing the parsing when no game is on).
"""
import os, sys, json, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
import espn                                                   # noqa: E402
import research                                               # noqa: E402

ET = ZoneInfo("America/New_York")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
INCLUDE_FINAL = "--include-final" in sys.argv
AN_BOOKS = research.AN_BOOKS
AN_PERIODS = ("event", "firsthalf", "secondhalf", "firstquarter", "secondquarter", "thirdquarter", "fourthquarter")
ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"


def code(a):
    return espn.ESPN2.get(a, str(a).lower() if a else a)


def espn_games():
    """ESPN scoreboard events for yesterday and today (late games run past midnight)"""
    evs = []
    for d in (NOW - pd.Timedelta(days=1), NOW):
        try: evs += espn._get(f"{ESPN_SITE}/scoreboard?dates={d:%Y%m%d}&limit=50").get("events", [])
        except Exception as e: print("ESPN scoreboard unavailable:", type(e).__name__)
    seen, out = set(), []
    for ev in evs:
        if ev["id"] in seen: continue
        seen.add(ev["id"]); out.append(ev)
    return out


def situation_row(ev):
    comp = ev["competitions"][0]
    st = comp.get("status", {}); typ = st.get("type", {})
    teams = {c["homeAway"]: c for c in comp["competitors"]}
    lp = (comp.get("situation") or {}).get("lastPlay") or {}
    start = pd.to_datetime(comp.get("date"), utc=True).tz_convert(ET).tz_localize(None)
    return dict(seen_at_et=str(NOW)[:19], espn_event_id=int(ev["id"]), date=str(start.date()),
                away=code(teams["away"]["team"]["abbreviation"]), home=code(teams["home"]["team"]["abbreviation"]),
                state=typ.get("state"), detail=typ.get("shortDetail"), period=st.get("period"), clock=st.get("displayClock"),
                away_score=pd.to_numeric(teams["away"].get("score"), errors="coerce"), home_score=pd.to_numeric(teams["home"].get("score"), errors="coerce"),
                home_win_pct_espn=((lp.get("probability") or {}).get("homeWinPercentage")), last_play=(lp.get("text") or "")[:200])


def espn_odds_rows(ev, base):
    comp = ev["competitions"][0]; rows = []
    try:
        od = espn._get(f"{CORE}/events/{ev['id']}/competitions/{comp['id']}/odds?limit=50")
    except Exception as e:
        print("ESPN odds unavailable:", type(e).__name__); return rows
    a = lambda d, *ks: espn._num(((((d or {}).get(ks[0]) or {}).get(ks[1]) or {}).get("american")) if len(ks) == 2 else None)
    for it in od.get("items", []):
        h, w = it.get("homeTeamOdds") or {}, it.get("awayTeamOdds") or {}
        cur = it.get("current") or {}
        rows.append(dict(base, provider=it.get("provider", {}).get("name"), provider_id=it.get("provider", {}).get("id"),
                         home_spread=a(h, "current", "pointSpread") if h.get("current") else espn._num(it.get("spread")),
                         home_spread_odds=a(h, "current", "spread"), away_spread_odds=a(w, "current", "spread"),
                         total=espn._num(((cur.get("total") or {}).get("american"))) if cur else espn._num(it.get("overUnder")),
                         over_odds=espn._num(((cur.get("over") or {}).get("american"))) if cur else espn._num(it.get("overOdds")),
                         under_odds=espn._num(((cur.get("under") or {}).get("american"))) if cur else espn._num(it.get("underOdds")),
                         home_ml=a(h, "current", "moneyLine") if h.get("current") else espn._num(h.get("moneyLine")),
                         away_ml=a(w, "current", "moneyLine") if w.get("current") else espn._num(w.get("moneyLine"))))
    return rows


def an_rows(live_games):
    """Action Network markets for the live games, every book, period and market, flagged is_live"""
    rows = []
    for day in sorted({b["date"] for b in live_games.values()}):
        try:
            d = research._an_get(f"https://api.actionnetwork.com/web/v2/scoreboard/nba?bookIds={','.join(map(str, AN_BOOKS))}"
                                 f"&periods={','.join(AN_PERIODS)}&date={day.replace('-', '')}")
        except Exception as e:
            print("Action Network unavailable:", day, type(e).__name__, str(e)[:80]); continue
        rows += _an_day(d, live_games)
    return rows


def _an_day(d, live_games):
    rows = []
    for g in d.get("games", []):
        t = {x["id"]: code(x.get("abbr")) for x in g.get("teams", [])}
        home, away = t.get(g["home_team_id"]), t.get(g["away_team_id"])
        base = live_games.get((home, away))
        if base is None: continue
        for bid, m in (g.get("markets") or {}).items():
            for period, mk in (m or {}).items():
                for typ, outs in (mk or {}).items():
                    for o in outs or []:
                        side = o.get("side")
                        if typ == "core_bet_type_6_team_score":
                            typ_ = "team_total"; side = f"{'home' if o.get('team_id') == g['home_team_id'] else 'away'}_{side}"
                        else: typ_ = typ
                        rows.append(dict(base, book=AN_BOOKS.get(int(bid), bid), period=period, market=typ_, side=side,
                                         value=o.get("value"), odds=o.get("odds"), is_live=o.get("is_live"),
                                         line_status=o.get("line_status")))
    return rows


def main():
    evs = espn_games()
    live, soon = [], False
    for ev in evs:
        comp = ev["competitions"][0]; state = comp.get("status", {}).get("type", {}).get("state")
        start = pd.to_datetime(comp.get("date"), utc=True).tz_convert(ET).tz_localize(None)
        if state == "in" or (INCLUDE_FINAL and state == "post" and (NOW - start) < pd.Timedelta(hours=30)): live.append(ev)
        # still "pre" a few minutes after the scheduled kickoff is normal (ESPN flips to "in" late): keep the loop
        # alive from 45 minutes before until 45 minutes after the scheduled time (Nov 1: the 1 PM games were missed until 1:21)
        elif state == "pre" and pd.Timedelta(minutes=-45) <= start - NOW <= pd.Timedelta(minutes=45): soon = True
    if not live:
        print(f"{NOW:%a %H:%M} ET: no NBA game in progress" + ("; one starts soon." if soon else "."))
        return 2 if soon else 3
    research.init(W)
    sit, eo, keys = [], [], {}
    for ev in live:
        s = situation_row(ev); sit.append(s)
        base = dict(seen_at_et=s["seen_at_et"], espn_event_id=s["espn_event_id"], date=s["date"], away=s["away"], home=s["home"],
                    period=s["period"], clock=s["clock"], away_score=s["away_score"], home_score=s["home_score"])
        eo += espn_odds_rows(ev, base)
        keys[(s["home"], s["away"])] = base
    bk = an_rows(keys)
    n = {}
    for name, rows, key, vals in (
            ("situation", sit, ["espn_event_id"], ["state", "period", "clock", "away_score", "home_score", "home_win_pct_espn", "last_play"]),
            ("espn_odds", eo, ["espn_event_id", "provider"], ["home_spread", "home_spread_odds", "away_spread_odds", "total",
                                                              "over_odds", "under_odds", "home_ml", "away_ml"]),
            ("books", bk, ["espn_event_id", "book", "period", "market", "side"], ["value", "odds", "is_live", "line_status"])):
        by_day = {}
        for r in rows: by_day.setdefault(r["date"], []).append(r)
        n[name] = 0
        for day, rr in by_day.items():
            d = os.path.join(W, "research", "live", day); os.makedirs(d, exist_ok=True)
            n[name] += research._append_changed(os.path.join(d, f"{name}.csv"), rr, key, vals)
    n_live_lines = sum(1 for r in bk if r.get("is_live"))
    print(f"{NOW:%a %H:%M:%S} ET: {len(live)} games in progress; new rows: {n}; Action Network live outcomes this poll: {n_live_lines}; "
          f"ESPN providers: {sorted(set(r['provider'] for r in eo if r.get('provider')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
