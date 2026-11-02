"""Current DraftKings lines from Action Network (refreshed about every 30 seconds; ESPN's copy is about 12 minutes old)."""
import json, urllib.request
import numpy as np, pandas as pd
import espn

DK = 68   # Action Network's DraftKings book id


def _get(url, tries=3):
    """fetch JSON, retrying a dropped connection twice (a few seconds apart)"""
    import time
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))


def _num(x):
    try: return float(x)
    except Exception: return np.nan


def games(day, book_ids=(DK,)):
    """raw Action Network games for one date"""
    d = _get(f"https://api.actionnetwork.com/web/v2/scoreboard/nba?bookIds={','.join(map(str, book_ids))}"
             f"&date={pd.Timestamp(day):%Y%m%d}")
    return d.get("games", [])


def lines(day, book=DK):
    """one row per game: home, away, an_status, an_spread (home perspective), an_total, an_inserted (when the book last changed)"""
    out = []
    for g in games(day, (book,)):
        t = {x["id"]: espn.ESPN2.get(x.get("abbr")) for x in g.get("teams", [])}
        ev = ((g.get("markets") or {}).get(str(book)) or {}).get("event") or {}
        side = lambda mk, s: next((o for o in ev.get(mk, []) if o.get("side") == s), {}) or {}
        hs, ov = side("spread", "home"), side("total", "over")
        aws, un = side("spread", "away"), side("total", "under")
        tot = _num(ov.get("value")); okt = (not np.isnan(tot)) and tot > 150          # full-game total (not a team or half total)
        out.append(dict(home=t.get(g["home_team_id"]), away=t.get(g["away_team_id"]), an_status=g.get("status"),
                        an_spread=_num(hs.get("value")), an_total=tot if (np.isnan(tot) or tot > 150) else np.nan,
                        an_home_spread_odds=_num(hs.get("odds")), an_away_spread_odds=_num(aws.get("odds")),
                        an_over_odds=_num(ov.get("odds")) if okt else np.nan, an_under_odds=_num(un.get("odds")) if okt else np.nan,
                        an_game_id=g.get("id")))
    return pd.DataFrame(out)


def merge_current(L, day):
    """Replace ESPN's current spread/total with Action Network's DraftKings numbers where available.
    Keeps ESPN's opening line. Adds line_source ('actionnetwork' or 'espn') and marks games Action Network says have started."""
    L = L.copy()
    L["line_source"] = "espn"
    try:
        A = lines(day)
    except Exception as e:
        print("Action Network unavailable, using ESPN lines:", type(e).__name__, str(e)[:100])
        return L
    if not len(A) or not len(L): return L
    m = L.merge(A, on=["home", "away"], how="left")
    for mk in ("spread", "total"):
        ok = m[f"an_{mk}"].notna()
        m.loc[ok, f"current_{mk}"] = m.loc[ok, f"an_{mk}"]
    for c in ("home_spread_odds", "away_spread_odds", "over_odds", "under_odds"):      # DraftKings prices
        m[f"current_{c}"] = m[f"an_{c}"]
    m.loc[m.an_spread.notna() | m.an_total.notna(), "line_source"] = "actionnetwork"
    started = m.an_status.notna() & ~m.an_status.isin(["scheduled"])
    m.loc[started, "state"] = "in"      # Action Network sees tip-off before ESPN's cached copy does
    return m.drop(columns=["an_spread", "an_total", "an_home_spread_odds", "an_away_spread_odds", "an_over_odds", "an_under_odds"])
