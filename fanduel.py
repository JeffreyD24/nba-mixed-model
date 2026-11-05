"""FanDuel (Connecticut) lines next to DraftKings in every bet alert (Nov 4, 2026, Jeffrey's request).
Lines come from Action Network's FanDuel CT feed (book 741), refreshed about every 30 seconds, one request per date per run.
compare() says which book has the better number for the bet: a better line wins first (more points on a spread, a lower total
for an over, a higher total for an under); on the same line, the better price. Line shopping DraftKings + FanDuel on the NBA
totals bets 2023-26 added about +3.3u a season (research: claude/threshold_sweep_shopping_roadmap_2026-11-04.md).
Never breaks an alert: any failure returns no FanDuel line and the alert goes out with DraftKings alone."""
import json, time, urllib.request
import numpy as np, pandas as pd
import espn

FD_BOOK = 741                   # Action Network: FanDuel CT (69 = FanDuel NJ; same prices in spot checks)
SPORT_URL = {"nba": "nba", "nhl": "nhl", "nfl": "nfl"}
FD_PAGE = {"nba": "https://sportsbook.fanduel.com/navigation/nba", "nhl": "https://sportsbook.fanduel.com/navigation/nhl",
           "nfl": "https://sportsbook.fanduel.com/navigation/nfl"}
# decimal payout one point of line is worth, for weighing a better line against a worse price (approximate):
# a point in the NBA/NFL is worth about 4-5% win chance; at ~52% and -110 that equals ~0.16 of decimal payout
# (0.045 x 1.91 / 0.52). A goal in the NHL is worth ~18% win chance (~0.65). Fixed Nov 4, 2026: was 0.045 / 0.30 per point,
# which let a 1-pt worse line at a slightly better price count as best (caught in an NFL dry run).
PER_POINT = {"nba": 0.16, "nfl": 0.16, "nhl": 0.65}
_CACHE = {}


def _code(abbr):
    if not abbr: return None
    if hasattr(espn, "code"): return espn.code(abbr)
    return espn.ESPN2.get(abbr) or espn.ESPN2.get(str(abbr).upper())


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return np.nan


def lines(sport, day):
    """{(home, away): dict(spread=home spread, spread_home_odds, spread_away_odds, total, over_odds, under_odds, ml_home, ml_away)}"""
    key = (sport, str(pd.Timestamp(day).date()))
    if key in _CACHE: return _CACHE[key]
    out = {}
    try:
        url = (f"https://api.actionnetwork.com/web/v2/scoreboard/{SPORT_URL[sport]}?bookIds={FD_BOOK}"
               f"&date={pd.Timestamp(day):%Y%m%d}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        for i in range(2):
            try:
                with urllib.request.urlopen(req, timeout=20) as r: d = json.loads(r.read()); break
            except Exception:
                if i: raise
                time.sleep(3)
        for g in d.get("games", []):
            t = {x["id"]: _code(x.get("abbr")) for x in g.get("teams", [])}
            ev = ((g.get("markets") or {}).get(str(FD_BOOK)) or {}).get("event") or {}
            pick = lambda mk, s: next((o for o in ev.get(mk, []) if o.get("side") == s and not o.get("is_alt_market")), {}) or {}
            hs, as_, ov, un, hm, am = (pick("spread", "home"), pick("spread", "away"), pick("total", "over"), pick("total", "under"),
                                       pick("moneyline", "home"), pick("moneyline", "away"))
            tot = _num(ov.get("value"))
            if not np.isnan(tot) and tot < {"nba": 150, "nfl": 28, "nhl": 3}[sport]: tot = np.nan     # a half or team total
            out[(t.get(g["home_team_id"]), t.get(g["away_team_id"]))] = dict(
                spread=_num(hs.get("value")), spread_home_odds=_num(hs.get("odds")), spread_away_odds=_num(as_.get("odds")),
                total=tot, over_odds=_num(ov.get("odds")) if not np.isnan(tot) else np.nan,
                under_odds=_num(un.get("odds")) if not np.isnan(tot) else np.nan,
                ml_home=_num(hm.get("odds")), ml_away=_num(am.get("odds")))
    except Exception as ex:
        print("FanDuel lines unavailable:", type(ex).__name__, str(ex)[:100])
    _CACHE[key] = out
    return out


def _dec(px):
    px = float(px); return 1 + (px / 100 if px > 0 else 100 / abs(px))


def quote(sport, day, home, away, market, side):
    """FanDuel's (line, price) for this bet, or (None, None). market: spread / puck line / total / moneyline;
    side: home / away / over / under. A spread or puck line comes back as the bet side's own line."""
    try:
        return _quote(sport, day, home, away, market, side)
    except Exception as ex:
        print("FanDuel quote failed:", type(ex).__name__, str(ex)[:100]); return None, None


def _quote(sport, day, home, away, market, side):
    q = lines(sport, day).get((home, away))
    if not q: return None, None
    if market in ("spread", "puck line"):
        if np.isnan(q["spread"]): return None, None
        ln = q["spread"] if side == "home" else -q["spread"]
        px = q["spread_home_odds"] if side == "home" else q["spread_away_odds"]
    elif market == "total":
        if np.isnan(q["total"]): return None, None
        ln, px = q["total"], (q["over_odds"] if side == "over" else q["under_odds"])
    else:
        ln, px = None, (q["ml_home"] if side == "home" else q["ml_away"])
    if px is None or np.isnan(px): return None, None
    return ln, px


def compare(sport, day, home, away, market, side, dk_line, dk_px, label=None, edge=None, need=None):
    """(text for the alert, FanDuel link or None, best book 'FanDuel' / 'DraftKings' / 'same').
    dk_line: the bet side's own DraftKings line (spread: that team's line; total: the total; moneyline: None).
    label: how to name the bet in the text (e.g. 'BOS' or 'over'); defaults to the side.
    edge / need: the bet's edge at DraftKings' line and the rule's minimum (points or goals); a book whose line is worse never
    counts as best if that worse line would leave less edge than the rule needs."""
    try:
        fl, fp = quote(sport, day, home, away, market, side)
        lab = label or side
        def fmt(ln, px):
            if ln is None or (isinstance(ln, float) and np.isnan(ln)): s = f"{lab}"
            elif market == "total": s = f"{lab} {float(ln):g}"
            else: s = f"{lab} {float(ln):+g}"
            return s + (f" ({float(px):+.0f})" if px is not None and not pd.isna(px) else "")
        dk_ok = dk_px is not None and not pd.isna(dk_px)
        dk_txt = "DraftKings: " + (fmt(dk_line, dk_px) if dk_ok or dk_line is not None else "no line")
        if fp is None:
            return f"LINES: {dk_txt} | FanDuel: no line posted yet", FD_PAGE[sport], "DraftKings"
        fd_txt = "FanDuel: " + fmt(fl, fp)
        if not dk_ok and dk_line is None:
            return f"LINES: {fd_txt} | DraftKings: no line", FD_PAGE[sport], "FanDuel"
        def value(ln, px):
            v = _dec(px if px is not None and not pd.isna(px) else -110)
            if ln is None or market == "moneyline": return v
            gain = float(ln) if market in ("spread", "puck line") else (-float(ln) if side == "over" else float(ln))
            return v + PER_POINT[sport] * gain
        vd, vf = value(dk_line, dk_px), value(fl, fp)
        if abs(vd - vf) < 1e-9:
            return f"LINES (same at both): {dk_txt} | {fd_txt}", FD_PAGE[sport], "same"
        best = "FanDuel" if vf > vd else "DraftKings"
        if (best == "FanDuel" and fl is not None and dk_line is not None
                and market in ("spread", "total", "puck line")):
            gain = (float(fl) - float(dk_line)) if market != "total" else ((float(dk_line) - float(fl)) if side == "over" else (float(fl) - float(dk_line)))
            if gain < 0 and (edge is None or need is None or float(edge) + gain < float(need) - 1e-9):
                best = "DraftKings"
        why = []
        bl, wl = (fl, dk_line) if best == "FanDuel" else (dk_line, fl)
        if bl is not None and wl is not None and abs(float(bl) - float(wl)) > 1e-9:
            d = abs(float(bl) - float(wl)); pts = f"{d:g} pt{'s' if d != 1 else ''}"
            gain = (float(bl) - float(wl)) if market in ("spread", "puck line") else ((float(wl) - float(bl)) if side == "over" else (float(bl) - float(wl)))
            why.append(f"{pts} better line" if gain > 0 else
                       f"better price, but the line is {pts} worse there, so the edge is {pts} smaller")
        else:
            why.append("better price")
        first, second = (fd_txt, dk_txt) if best == "FanDuel" else (dk_txt, fd_txt)
        return f"BEST: {first} ({', '.join(why) or 'better'}) | {second}", FD_PAGE[sport], best
    except Exception as ex:
        print("FanDuel compare failed:", type(ex).__name__, str(ex)[:100])
        return "", None, "DraftKings"


def actions(dk, fd, best):
    """ntfy action buttons: the better book first; no 'Log this bet' button (removed Nov 4, 2026)"""
    a = []
    if dk: a.append(("DraftKings", dk))
    if fd: a.append(("FanDuel", fd))
    if best == "FanDuel": a.reverse()
    return "; ".join(f"view, {('Bet on ' + n + (' (best)' if n == best else ''))}, {u}" for n, u in a)


def same_or_better(sport, day, home, away, market, side, dk_line, cap):
    """FanDuel's price when FanDuel has the same or a better line than DraftKings' dk_line at cap or better, else None
    (lets a bet over DraftKings' price cap be placed at FanDuel; used by the first alert and by reminders / back-in-range)."""
    fl, fp = quote(sport, day, home, away, market, side)
    if fp is None or float(fp) < cap: return None
    if market == "moneyline": return fp
    if fl is None or dk_line is None: return None
    ok = (float(fl) >= float(dk_line) if market in ("spread", "puck line") else
          float(fl) <= float(dk_line) if side == "over" else float(fl) >= float(dk_line))
    return fp if ok else None
