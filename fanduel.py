"""FanDuel (Connecticut) lines next to DraftKings in every bet alert (Nov 4, 2026, Jeffrey's request).
Lines come from Action Network's FanDuel CT feed (book 741), refreshed about every 30 seconds, one request per date per run.
compare() says which book has the better number for the bet: a better line wins first (more points on a spread, a lower total
for an over, a higher total for an under); on the same line, the better price. Line shopping DraftKings + FanDuel on the NBA
totals bets 2023-26 added about +3.3u a season (research: claude/threshold_sweep_shopping_roadmap_2026-11-04.md).
Never breaks an alert: any failure returns no FanDuel line and the alert goes out with DraftKings alone."""
import json, time, urllib.request, os, glob
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
_BOARD = {}
# Nov 6, 2026 (Jeffrey: "the FanDuel links don't link to the actual bet, just to the league"): a real FanDuel bet-slip link for the
# alerted bet, built from our own FanDuel feed (odds_feed.py -> research/feed/fd/<sport>/, sel_id = "<marketId>:<selectionId>").
# Same link format as nba-mixed-model props_shadow.py. Falls back to the league page when the feed doesn't have that exact line.
FD_MARKET = {"moneyline": ("Moneyline",), "spread": ("Spread",), "puck line": ("Puck Line",), "total": ("Total Points", "Total Goals")}


def _board(sport):
    """last known state of every FanDuel selection in the last 7 days of the feed (rows are written in time order)"""
    if sport in _BOARD: return _BOARD[sport]
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research", "feed", "fd", sport)
    fs = [f for d in sorted(glob.glob(os.path.join(root, "*")))[-7:] for f in sorted(glob.glob(os.path.join(d, "*.csv.gz")))]
    B = pd.DataFrame()
    if fs:
        B = pd.concat([pd.read_csv(f, dtype=str, low_memory=False) for f in fs], ignore_index=True)
        B = B.drop_duplicates("sel_id", keep="last")
        B = B[(B.status != "off") & B.market.isin([m for v in FD_MARKET.values() for m in v])]
    _BOARD[sport] = B
    return B


def bet_link(sport, day, home_name, away_name, market, side, line):
    """FanDuel bet-slip link for this exact bet (puts it on the slip), or None. line: the bet side's own line (None for moneyline)."""
    try:
        B = _board(sport)
        if not len(B) or not home_name or not away_name: return None
        g = B[(B.home == home_name) & (B.away == away_name) & B.market.isin(FD_MARKET[market])
              & (B.start_et.astype(str).str[:10] == str(pd.Timestamp(day).date()))]
        g = g[g.label.str.lower() == side] if side in ("over", "under") else g[g.label == (home_name if side == "home" else away_name)]
        if market != "moneyline" and line is not None:
            g = g[(pd.to_numeric(g.points, errors="coerce") - float(line)).abs() < 1e-6]
        if len(g) != 1: return None
        r = g.iloc[0]
        mid, sid = str(r.sel_id).split(":", 1)     # both ids from sel_id: the feed's market_id column can lose a trailing zero (read back as a number)
        return f"https://sportsbook.fanduel.com/addToBetslip?marketId[0]={mid}&selectionId[0]={sid}"
    except Exception as ex:
        print("FanDuel bet link failed:", type(ex).__name__, str(ex)[:100]); return None


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
            nm = {x["id"]: x.get("full_name") for x in g.get("teams", [])}
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
                ml_home=_num(hm.get("odds")), ml_away=_num(am.get("odds")),
                home_name=nm.get(g["home_team_id"]), away_name=nm.get(g["away_team_id"]))
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
        _q = lines(sport, day).get((home, away)) or {}
        link = (bet_link(sport, day, _q.get("home_name"), _q.get("away_name"), market, side, fl) if fp is not None else None) or FD_PAGE[sport]
        def fmt(ln, px):
            if ln is None or (isinstance(ln, float) and np.isnan(ln)): s = f"{lab}"
            elif market == "total": s = f"{lab} {float(ln):g}"
            else: s = f"{lab} {float(ln):+g}"
            return s + (f" ({float(px):+.0f})" if px is not None and not pd.isna(px) else "")
        dk_ok = dk_px is not None and not pd.isna(dk_px)
        dk_txt = "DraftKings: " + (fmt(dk_line, dk_px) if dk_ok or dk_line is not None else "no line")
        if fp is None:
            return f"LINES: {dk_txt} | FanDuel: no line posted yet", None, "DraftKings"     # Nov 5, 2026: no FanDuel button when FanDuel has no line
        fd_txt = "FanDuel: " + fmt(fl, fp)
        if not dk_ok and dk_line is None:
            return f"LINES: {fd_txt} | DraftKings: no line", link, "FanDuel"
        def value(ln, px):
            v = _dec(px if px is not None and not pd.isna(px) else -110)
            if ln is None or market == "moneyline": return v
            gain = float(ln) if market in ("spread", "puck line") else (-float(ln) if side == "over" else float(ln))
            return v + PER_POINT[sport] * gain
        vd, vf = value(dk_line, dk_px), value(fl, fp)
        if abs(vd - vf) < 1e-9:
            return f"LINES (same at both): {dk_txt} | {fd_txt}", link, "same"
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
        return f"BEST: {first} ({', '.join(why) or 'better'}) | {second}", link, best
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


# ---- short alerts (Nov 6, 2026, Jeffrey: "All I need to know is what bet to make, where to make it, and when I should stop") ----
import re as _re
_SKIP = ("INFO ONLY", "NO BET", "TEST", "[PASS]", "Line jump", "Market agrees", "Injury", "Key decision", "BAIL-OUT")


def compact_alert(title, body, best=None):
    """Short form of a game bet alert / reminder / back-in-range / DON'T BET: (title, body), or None to keep the original.
    Title: BET <side line price> at <book>. Body: Bet until <stop>, then the game. The long text (model numbers, goalies, record)
    is not sent; it stays in the repo's alert records. Anything it can't read is sent unchanged."""
    try:
        t = str(title).strip()
        if any(s in t for s in _SKIP): return None
        core = _re.sub(r"\s*\|\s*BEST AT FANDUEL\s*$", "", t)
        m = _re.search(r"(DON'T BET -|- BET|\bBet)\s+(.+?):\s+(.+)$", core)
        if not m: return None
        verb, what, game = m.group(1), m.group(2).strip(), m.group(3).strip()
        flags = [f for f in ("ALREADY BET", "YOU BET THE OTHER SIDE") if f in t]
        b = str(body)
        if verb.startswith("DON'T"):
            plain = _re.sub(r"\s*\(?[+-]\d{3,}\)?$|\s*EVEN$", "", what).strip()
            now = _re.search(r"\bat ([+-]\d{3,})\b", b)
            return (f"STOP: don't bet {plain}",
                    f"It moved past the bet-until price/line{' (now ' + now.group(1) + ')' if now else ''}. If you already bet it, just log it.\n{game}.")
        # where and at what price: the better book from the BEST/LINES line (fanduel.compare), else DraftKings
        book, bet = "DraftKings", what
        mb = _re.search(r"^(BEST|LINES(?: \(same at both\))?): (DraftKings|FanDuel): (.+?) \(([+-]\d+)\)", b, _re.M)
        if mb:
            book = "DraftKings or FanDuel" if "same" in mb.group(1) else mb.group(2)
            lab, px = mb.group(3).strip(), mb.group(4)
            lab = _re.sub(r"^(over|under)\b", lambda x: x.group(1).upper(), lab)
            if not _re.search(r"\d", lab): lab += " ML"
            bet = f"{lab} {px}"
        else:
            bet = _re.sub(r"\(([+-]\d+)\)", r"\1", what)
        # when to stop
        stop = None
        ms = _re.search(r"Bet only at ([+-]?\d+|EVEN) or better", b)
        if ms: stop = f"Bet until {ms.group(1)}."
        mr = _re.search(r"BET RANGE: (.+?) [+-]?[\d.]+ (?:down|up) to ([+-]?[\d.]+)\.", b)
        if mr and not stop:
            who = mr.group(1).upper() if mr.group(1) in ("over", "under") else mr.group(1)
            cap = _re.search(r"Price (-?\d+) or better", b)
            other = _re.search(r"(?:moves the other way to (.+?)|drops to ([\d.]+) or lower|rises to ([\d.]+) or higher) \(", b)
            o = next((x for x in (other.groups() if other else ()) if x), None)
            stop = (f"Bet until {who} {mr.group(2)}" + (f" at {cap.group(1)} or better" if cap else "") + "."
                    + (f" Also stop if DraftKings moves the other way to {o}." if o else ""))
        if not stop: return None
        verb_t = "REMINDER: BET" if "REMINDER" in t else "BET again" if "BACK IN RANGE" in t else "BET"
        head = (" / ".join(flags) + " - ") if flags else ""
        note = ""
        ma = _re.search(r"ALREADY BET: (you logged .+?)\.", b)
        if ma: note = f"Already bet: {ma.group(1)}.\n"
        mc = _re.search(r"CAUTION: (.+?)\.", b)
        if mc: note += f"Caution: {mc.group(1)}.\n"
        return f"{head}{verb_t} {bet} at {book}", f"{note}{stop}\n{game}."
    except Exception as e:
        print("compact_alert skipped:", type(e).__name__, str(e)[:80])
        return None
