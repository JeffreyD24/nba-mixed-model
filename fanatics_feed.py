"""Fanatics CT game-line feed, every sport (Nov 6, 2026; Jeffrey has a Fanatics account, the third CT sportsbook).
Fanatics' own site refuses cloud/out-of-state clients (Akamai "Access Denied"), so the lines come from Action Network's
Fanatics CT book (id 2821, same feed fanduel.py uses for FanDuel CT, book 741). Spreads, totals and moneylines, full game.

  python fanatics_feed.py WORKDIR        one tick (feed_loop.sh, about once a minute)

Only CHANGES are saved (a new line/price, or a market that disappeared = status "off"), one small file per 5 minutes:
research/feed/fanatics/<sport>/<YYYY-MM-DD>/<HHMM>.csv.gz, the same layout as research/feed/{dk,fd}/ (opener = first row seen,
close = last row before the start). Memory between ticks: WORKDIR/_tmp/fanatics_state.json (not committed).
Dates polled: today and tomorrow every minute; NFL/NCAAF also the next 8 days every 10 minutes. Never raises.
Player props (Nov 6, 2026, RULE 12): RotoWire's free props page carries every book's prop lines (Fanatics, DraftKings, FanDuel, BetMGM,
Caesars, ...). Every 10 minutes the NFL and NBA pages are read and every book's line/price CHANGES are saved to
research/feed/rotowire_props/<sport>/<YYYY-MM-DD>/<HHMM>.csv.gz (first row seen = that book's opener as RotoWire showed it).
Game lines of every book (spread / total / moneyline; NBA, NHL, NFL) from RotoWire's games tables, also every 10 minutes, to
research/feed/rotowire_games/<sport>/... (track B: BetMGM, Caesars, Hard Rock, ... openers and closes for free).
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


RW_SPORTS = ("nfl", "nba", "nhl")          # NHL props page added Nov 6 (shots, points, goals, assists, saves...)
RW_COLS = ["snap_et", "sport", "game_id", "player_id", "player", "team", "opp", "book", "market", "line", "over", "under"]


def rotowire_props(S, snap):
    """every book's prop lines from RotoWire (free page), changes only; state in S['rw']"""
    import re as _re
    S.setdefault("rw", {}); S.setdefault("rw_due", 0)
    if time.time() < S["rw_due"]: return 0
    S["rw_due"] = time.time() + 590
    n = 0
    for sport in RW_SPORTS:
        try:
            req = urllib.request.Request(f"https://www.rotowire.com/betting/{sport}/player-props.php", headers={"User-Agent": H["User-Agent"], "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=60) as r: h = r.read().decode("utf-8", "ignore")
        except Exception as ex:
            print("RotoWire props fetch failed:", sport, type(ex).__name__); continue
        out = []
        for o in _re.findall(r'\{"gameID":"\d+","playerID"[^{}]*\}', h):
            try: r = json.loads(o)
            except Exception: continue
            for k, v in r.items():
                m = _re.match(r"^([a-z0-9]+)_([a-z]+)$", k)
                if not m or v in (None, "") or k in ("gameID", "playerID"): continue
                bk, mk = m.groups()
                ov, un = r.get(f"{k}Over"), r.get(f"{k}Under")
                key = f"{sport}|{r['gameID']}|{r['playerID']}|{bk}|{mk}"
                val = [v, ov, un]
                if S["rw"].get(key) != val:
                    S["rw"][key] = val
                    out.append(dict(snap_et=snap, sport=sport, game_id=r["gameID"], player_id=r["playerID"], player=r.get("name"),
                                    team=r.get("team"), opp=r.get("opp"), book=bk, market=mk, line=v, over=ov, under=un))
        if out:
            d = os.path.join(W, "research", "feed", "rotowire_props", sport, f"{NOW:%Y-%m-%d}"); os.makedirs(d, exist_ok=True)
            f = os.path.join(d, f"{NOW:%H}{NOW.minute // 5 * 5:02d}.csv.gz")
            old = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame(columns=RW_COLS)
            pd.concat([old, pd.DataFrame(out)[RW_COLS]], ignore_index=True).to_csv(f, index=False, compression="gzip")
        n += len(out)
    if len(S["rw"]) > 400000: S["rw"] = {}          # keep the state small (a fresh job re-logs everything once anyway)
    return n


RWG_COLS = ["snap_et", "sport", "game_id", "game_date", "team", "opp", "home_away", "book", "market", "line", "price"]


def rotowire_games(S, snap):
    """every book's full-game spread / total / moneyline from RotoWire's games tables (NBA, NHL, NFL), changes only (Nov 6, RULE 13)"""
    S.setdefault("rwg", {}); S.setdefault("rwg_due", 0)
    if time.time() < S["rwg_due"]: return 0
    S["rwg_due"] = time.time() + 590
    n = 0
    for sport in ("nba", "nhl", "nfl"):
        try: G = get_any(f"https://www.rotowire.com/betting/{sport}/tables/{sport}-games.php")
        except Exception as ex: print("RotoWire games fetch failed:", sport, type(ex).__name__); continue
        out = []
        for g in G if isinstance(G, list) else []:
            books = {k.split("_")[0] for k in g if k.endswith("_has_spread")}
            for bk in books:
                for mk, ln_k, px_k in (("spread", f"{bk}_spread", f"{bk}_spreadML"), ("total", f"{bk}_ou", f"{bk}_ouML"),
                                       ("moneyline", None, f"{bk}_moneyline")):
                    px = g.get(px_k); ln = g.get(ln_k) if ln_k else None
                    if px in (None, ""): continue
                    key = f"{sport}|{g['gameID']}|{g.get('abbr')}|{bk}|{mk}"
                    if S["rwg"].get(key) != [ln, px]:
                        S["rwg"][key] = [ln, px]
                        out.append(dict(snap_et=snap, sport=sport, game_id=g["gameID"], game_date=g.get("gameDate"), team=g.get("abbr"),
                                        opp=g.get("oppAbbr"), home_away=g.get("homeAway"), book=bk, market=mk, line=ln, price=px))
        if out:
            d = os.path.join(W, "research", "feed", "rotowire_games", sport, f"{NOW:%Y-%m-%d}"); os.makedirs(d, exist_ok=True)
            f = os.path.join(d, f"{NOW:%H}{NOW.minute // 5 * 5:02d}.csv.gz")
            old = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame(columns=RWG_COLS)
            pd.concat([old, pd.DataFrame(out)[RWG_COLS]], ignore_index=True).to_csv(f, index=False, compression="gzip")
        n += len(out)
    return n


def get_any(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": H["User-Agent"], "Accept": "application/json"}), timeout=40) as r:
        return json.loads(r.read())


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
    try: n_rw = rotowire_props(S, snap)
    except Exception as ex: n_rw = 0; print("RotoWire props failed:", type(ex).__name__, str(ex)[:120])
    try: n_rwg = rotowire_games(S, snap)
    except Exception as ex: n_rwg = 0; print("RotoWire games failed:", type(ex).__name__, str(ex)[:120])
    json.dump(S, open(SP, "w"))
    print(f"RotoWire game-line changes {n_rwg}")
    print(f"fanatics feed: {stats['req']} requests, {stats['err']} errors, {len(new)} changes; RotoWire props changes {n_rw}")


if __name__ == "__main__":
    try: main()
    except Exception as e: print("fanatics feed failed:", type(e).__name__, str(e)[:200])
