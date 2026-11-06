"""Fanatics (Connecticut) next to DraftKings / FanDuel: SHADOW ONLY (Nov 6, 2026).

Jeffrey has a Fanatics account (funding pending) and said: set it up, but do NOT put anything Fanatics-related in the alerts to his
phone until he explicitly says so. So, while SHOW_IN_ALERTS is False, every alert only LOGS what Fanatics offered for the same bet to
state/fanatics_shadow.csv (and whether Fanatics would have been the best book); no alert text, title or button changes.
To turn it on later (only on Jeffrey's word): set SHOW_IN_ALERTS = True here (same file in nba/nhl/nfl-mixed-model), then wire
alert_text() into the alert bodies, and add a FINDINGS.md [DECISION] entry.

Sources (Fanatics' own site refuses cloud clients):
  game lines: Action Network's Fanatics CT book (id 2821), through fanduel.py's Action Network code (same request shape as FanDuel CT 741);
  player props: BettingPros (book 14 = Fanatics), current offers. Never raises; any failure logs blanks.
"""
import os, re, json, time, urllib.request, urllib.parse, unicodedata
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
import fanduel

SHOW_IN_ALERTS = False          # Jeffrey, Nov 6, 2026: NOT in phone alerts until he says so
FAN_BOOK = 2821                 # Action Network: Fanatics CT
BP_BOOK = 14                    # BettingPros: Fanatics
BP_MARKETS = {("nfl", "receptions"): 104, ("nfl", "rec_yds"): 105,
              ("nba", "pts"): 156, ("nba", "reb"): 157, ("nba", "ast"): 151, ("nba", "fg3m"): 162}
BP_KEY = "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh"      # BettingPros' public web-client key (same as props_bettingpros*.py)
BP_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "application/json",
          "x-api-key": BP_KEY, "Origin": "https://www.bettingpros.com", "Referer": "https://www.bettingpros.com/"}
COLS = ["logged_at_et", "kind", "sport", "date", "home", "away", "market", "side", "player", "stat", "our_book", "our_line", "our_price",
        "fan_line", "fan_price", "fan_best", "note"]
_GAME_CACHE, _BP_CACHE = {}, {}
ET = ZoneInfo("America/New_York")


def _dec(px): px = float(px); return 1 + (px / 100 if px > 0 else 100 / abs(px))
def _nm(s): return re.sub(r"\s+", "", re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().replace("-", " "))))


def game_quote(sport, day, home, away, market, side):
    """Fanatics' (line, price) for this game bet, or (None, None); same conventions as fanduel.quote (a spread comes back as the
    bet side's own line)."""
    old_b, old_c = fanduel.FD_BOOK, fanduel._CACHE
    try:
        fanduel.FD_BOOK, fanduel._CACHE = FAN_BOOK, _GAME_CACHE
        return fanduel._quote(sport, day, home, away, market, side)
    except Exception as ex:
        print("Fanatics game quote failed:", type(ex).__name__, str(ex)[:100]); return None, None
    finally:
        fanduel.FD_BOOK, fanduel._CACHE = old_b, old_c


def _bp(path, params):
    url = f"https://api.bettingpros.com/v3/{path}?" + urllib.parse.urlencode(params)
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=BP_HDR), timeout=20) as r: return json.loads(r.read())
        except Exception:
            if i: raise
            time.sleep(2)


def prop_quote(sport, day, player, stat, side):
    """Fanatics' (line, price) for a player prop from BettingPros (main line), or (None, None)."""
    try:
        mid = BP_MARKETS.get((sport, stat))
        if mid is None: return None, None
        key = (sport, str(day), mid)
        if key not in _BP_CACHE:
            ev = _bp("events", dict(sport=sport.upper(), date=str(pd.Timestamp(day).date()))).get("events", [])
            offers = []
            for k in range(0, len(ev), 3):
                ids = ":".join(str(e["id"]) for e in ev[k:k + 3]); page = 1
                while True:
                    d = _bp("offers", dict(sport=sport.upper(), market_id=mid, event_id=ids, location="ALL", limit=50, page=page))
                    offers += d.get("offers", [])
                    if page >= ((d.get("_pagination") or {}).get("total_pages") or 1): break
                    page += 1
            _BP_CACHE[key] = offers
        for o in _BP_CACHE[key]:
            p = (o.get("participants") or [{}])[0]
            if _nm(p.get("name")) != _nm(player): continue
            for s in o.get("selections", []):
                if str(s.get("selection")).lower() != side: continue
                for b in s.get("books", []):
                    if b.get("id") != BP_BOOK: continue
                    for ln in b.get("lines", []):
                        if ln.get("main", True) and ln.get("active", True): return float(ln["line"]), float(ln["cost"])
        return None, None
    except Exception as ex:
        print("Fanatics prop quote failed:", type(ex).__name__, str(ex)[:100]); return None, None


def better(market, side, fan_line, fan_price, our_line, our_price):
    """True if Fanatics beats our book for this bet: a better line, or the same line at a better price (same rule as fanduel.compare,
    without its point-vs-price weighing)."""
    if fan_price is None or our_price is None or pd.isna(fan_price) or pd.isna(our_price): return None
    if market in ("moneyline",) or fan_line is None or our_line is None or pd.isna(fan_line) or pd.isna(our_line):
        return _dec(fan_price) > _dec(our_price)
    if market in ("spread", "puck line"): gain = float(fan_line) - float(our_line)          # more points is better
    elif side == "over": gain = float(our_line) - float(fan_line)                             # lower total / prop line is better for an over
    else: gain = float(fan_line) - float(our_line)                                            # higher line is better for an under
    return gain > 0 or (gain == 0 and _dec(fan_price) > _dec(our_price))


def shadow(state_dir, kind, sport, date, market, side, our_book, our_line, our_price, home="", away="", player="", stat=""):
    """Look up Fanatics for an alert that just went out and append one row to state/fanatics_shadow.csv. Never raises, never pushes."""
    try:
        if kind == "prop": fl, fp = prop_quote(sport, date, player, stat, side)
        else: fl, fp = game_quote(sport, date, home, away, market, side)
        row = dict(logged_at_et=dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S"), kind=kind, sport=sport, date=str(date), home=home,
                   away=away, market=market, side=side, player=player, stat=stat, our_book=our_book, our_line=our_line, our_price=our_price,
                   fan_line=fl, fan_price=fp, fan_best=better(market, side, fl, fp, our_line, our_price),
                   note="" if fp is not None else "Fanatics line not found")
        p = os.path.join(state_dir, "fanatics_shadow_props.csv" if kind == "prop" else "fanatics_shadow.csv")   # separate jobs, separate files
        pd.DataFrame([row])[COLS].to_csv(p, mode="a", header=not os.path.exists(p), index=False)
        return row
    except Exception as ex:
        print("Fanatics shadow log failed:", type(ex).__name__, str(ex)[:100]); return None


def alert_text(row):
    """The line an alert WOULD show once Jeffrey turns Fanatics on (unused while SHOW_IN_ALERTS is False)."""
    if not SHOW_IN_ALERTS or not row or row.get("fan_price") is None: return ""
    ln = "" if row.get("fan_line") is None else f"{row['fan_line']:g} "
    return f"Fanatics: {ln}{int(row['fan_price']):+d}" + (" (BEST)" if row.get("fan_best") else "")
