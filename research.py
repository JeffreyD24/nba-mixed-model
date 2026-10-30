"""
Research database: records market data that can't be recovered later.

Everything lands in research/ as append-only CSVs, keyed by game_id. See research/DATA_DICTIONARY.md.
Called at the end of every alert check; any failure here is caught and never blocks alerts.
"""
import os, json, hashlib
import numpy as np, pandas as pd
import espn

R = None  # set by init()


def init(workdir):
    global R
    R = os.path.join(workdir, "research"); os.makedirs(os.path.join(R, "odds"), exist_ok=True)
    os.makedirs(os.path.join(R, "model"), exist_ok=True)


def _same(a, b):
    """equal values, treating blanks alike and 5 and 5.0 alike"""
    na = lambda v: v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v == "")
    if na(a) or na(b): return na(a) and na(b)
    try: return float(a) == float(b)
    except (TypeError, ValueError): return str(a) == str(b)


def _append_changed(path, rows, key_cols, value_cols):
    """append only rows whose values differ from the last recorded row for the same key"""
    if not rows: return 0
    new = pd.DataFrame(rows)
    blank = lambda v: v is None or (isinstance(v, float) and np.isnan(v))
    for c in key_cols: new[c] = new[c].map(lambda v: "" if blank(v) else str(v))   # keys compared as text
    last = None
    if os.path.exists(path):
        old = pd.read_csv(path, dtype={c: str for c in key_cols})
        for c in key_cols: old[c] = old[c].fillna("")
        if len(old):
            last = old.groupby(key_cols).tail(1).set_index(key_cols)[value_cols]
            last = last[~last.index.duplicated(keep="last")]
    keep = []
    for rd in new.to_dict("records"):
        k = tuple(rd[c] for c in key_cols)
        k = k if len(k) > 1 else k[0]
        if last is not None and k in last.index:
            prev = last.loc[k]
            same = all(_same(prev[c], rd[c]) for c in value_cols)
            if same: continue
        keep.append(rd)
    if keep:
        pd.DataFrame(keep).to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    return len(keep)


def _num(x):
    try: return float(str(x).replace("+", "").replace("PK", "0").replace("pk", "0").replace("EVEN", "100"))
    except Exception: return np.nan


def odds_snapshot(now, day, games):
    """full DraftKings market for each game: lines, prices, moneylines, opening values"""
    sb = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={pd.Timestamp(day):%Y%m%d}")
    ids = {(g["home"], g["away"]): g["game_id"] for g in games}
    rows = []
    for ev in sb.get("events", []):
        comp = ev["competitions"][0]
        teams = {c["homeAway"]: espn.ESPN2.get(c["team"]["abbreviation"]) for c in comp["competitors"]}
        gid = ids.get((teams.get("home"), teams.get("away")))
        if gid is None: continue
        state = comp.get("status", {}).get("type", {}).get("state")
        if state not in (None, "pre"): continue
        try:
            od = espn._get(f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{ev['id']}/competitions/{comp['id']}/odds")
        except Exception:
            continue
        items = od.get("items", [])
        it = next((i for i in items if "draftkings" in str(i.get("provider", {}).get("name", "")).lower()), items[0] if items else None)
        if not it: continue
        h, a = it.get("homeTeamOdds") or {}, it.get("awayTeamOdds") or {}
        cur_tot = (it.get("current") or {}); opn_tot = (it.get("open") or {})
        g = lambda d, *ks: _num(((d or {}).get(ks[0]) or {}).get(ks[1], {}).get("american") if len(ks) == 2 else None)
        rows.append(dict(
            seen_at_et=str(now)[:16], game_id=gid, date=str(pd.Timestamp(day).date()), book=it.get("provider", {}).get("name"),
            home_spread=g(h, "current", "pointSpread"), home_spread_odds=g(h, "current", "spread"), away_spread_odds=g(a, "current", "spread"),
            total=_num((cur_tot.get("total") or {}).get("american")) if cur_tot else _num(it.get("overUnder")),
            over_odds=_num((cur_tot.get("over") or {}).get("american")) if cur_tot else _num(it.get("overOdds")),
            under_odds=_num((cur_tot.get("under") or {}).get("american")) if cur_tot else _num(it.get("underOdds")),
            home_ml=g(h, "current", "moneyLine"), away_ml=g(a, "current", "moneyLine"),
            open_home_spread=g(h, "open", "pointSpread"), open_total=_num((opn_tot.get("total") or {}).get("american")),
            open_home_ml=g(h, "open", "moneyLine"), open_away_ml=g(a, "open", "moneyLine"),
            espn_event_id=ev["id"]))
    path = os.path.join(R, "odds", f"{pd.Timestamp(day).date()}.csv")
    vals = ["home_spread", "home_spread_odds", "away_spread_odds", "total", "over_odds", "under_odds", "home_ml", "away_ml"]
    return _append_changed(path, rows, ["game_id"], vals), rows


def predictor_snapshot(now, day, odds_rows):
    """ESPN's matchup predictor (home win %), at most once an hour per game"""
    path = os.path.join(R, "espn_predictor.csv")
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["game_id", "seen_at_et"])
    rows = []
    for r in odds_rows:
        prev = old[old.game_id == r["game_id"]]
        if len(prev) and now - pd.Timestamp(prev.seen_at_et.iloc[-1]) < pd.Timedelta(minutes=55): continue
        try:
            s = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={r['espn_event_id']}")
            p = s.get("predictor") or {}
            rows.append(dict(seen_at_et=str(now)[:16], game_id=r["game_id"], date=r["date"],
                             home_win_pct=_num((p.get("homeTeam") or {}).get("gameProjection")),
                             away_win_pct=_num((p.get("awayTeam") or {}).get("gameProjection"))))
        except Exception:
            pass
    if rows: pd.DataFrame(rows).to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    return len(rows)


def news_log(now, news):
    """every injury note, kept with the time it was first seen (ESPN's feed only keeps the latest per player)"""
    path = os.path.join(R, "news.csv")
    seen = set(pd.read_csv(path).note_id) if os.path.exists(path) else set()
    rows = []
    for team, items in (news or {}).items():
        for when, text in items:
            nid = hashlib.md5(f"{team}|{text}".encode()).hexdigest()[:12]
            if nid in seen: continue
            seen.add(nid)
            rows.append(dict(first_seen_et=str(now)[:16], posted_et=str(when.replace(tzinfo=None))[:16], team=team, note=text, note_id=nid))
    if rows: pd.DataFrame(rows).to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    return len(rows)


def model_snapshot(now, model_rows):
    """the model's number for each game whenever it changes"""
    by_day = {}
    for r in model_rows: by_day.setdefault(r["date"], []).append(r)
    n = 0
    for day, rows in by_day.items():
        n += _append_changed(os.path.join(R, "model", f"{day}.csv"), rows, ["game_id"], ["model_margin", "model_total", "injury_report"])
    return n


# ---------------- Action Network: public betting splits and lines at several books ----------------
AN_BOOKS = {15: "Consensus", 30: "Open", 68: "DraftKings", 69: "FanDuel", 71: "BetRivers", 75: "BetMGM",
            79: "bet365", 123: "Caesars", 2988: "Fanatics"}


def _an_get(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def splits_snapshot(now, day, games):
    """% of bets (tickets) and % of money on each side, plus every book's line and prices.
    Returns (split rows written, book rows written)."""
    ids = {(g["home"], g["away"]): g["game_id"] for g in games}
    d = _an_get(f"https://api.actionnetwork.com/web/v2/scoreboard/nba?bookIds={','.join(map(str, AN_BOOKS))}"
                f"&date={pd.Timestamp(day):%Y%m%d}")
    splits, books = [], []
    for g in d.get("games", []):
        t = {x["id"]: espn.ESPN2.get(x.get("abbr")) for x in g.get("teams", [])}
        home, away = t.get(g["home_team_id"]), t.get(g["away_team_id"])
        gid = ids.get((home, away))
        if gid is None or g.get("status") not in ("scheduled", None): continue
        base = dict(seen_at_et=str(now)[:16], game_id=gid, date=str(pd.Timestamp(day).date()), away=away, home=home)
        for bid, m in (g.get("markets") or {}).items():
            ev = (m or {}).get("event") or {}
            pick = lambda mk, side: next((o for o in ev.get(mk, []) if o.get("side") == side), {}) or {}
            hs, as_, ov, un = pick("spread", "home"), pick("spread", "away"), pick("total", "over"), pick("total", "under")
            hm, am = pick("moneyline", "home"), pick("moneyline", "away")
            tot = _num(ov.get("value"))
            if not np.isnan(tot) and tot < 150: tot = np.nan          # some books post a period/team total here
            books.append(dict(base, book=AN_BOOKS.get(int(bid), bid), home_spread=_num(hs.get("value")),
                              home_spread_odds=_num(hs.get("odds")), away_spread_odds=_num(as_.get("odds")),
                              total=tot, over_odds=_num(ov.get("odds")) if not np.isnan(tot) else np.nan,
                              under_odds=_num(un.get("odds")) if not np.isnan(tot) else np.nan,
                              home_ml=_num(hm.get("odds")), away_ml=_num(am.get("odds"))))
            if int(bid) == 15:
                bi = lambda o, k: _num(((o.get("bet_info") or {}).get(k) or {}).get("percent"))
                splits.append(dict(base, num_bets=g.get("num_bets"),
                                   consensus_home_spread=_num(hs.get("value")),
                                   spread_home_bets_pct=bi(hs, "tickets"), spread_home_money_pct=bi(hs, "money"),
                                   consensus_total=tot, over_bets_pct=bi(ov, "tickets"), over_money_pct=bi(ov, "money"),
                                   home_ml_bets_pct=bi(hm, "tickets"), home_ml_money_pct=bi(hm, "money")))
    os.makedirs(os.path.join(R, "splits"), exist_ok=True); os.makedirs(os.path.join(R, "books"), exist_ok=True)
    dd = pd.Timestamp(day).date()
    n1 = _append_changed(os.path.join(R, "splits", f"{dd}.csv"), splits, ["game_id"],
                         ["spread_home_bets_pct", "spread_home_money_pct", "over_bets_pct", "over_money_pct",
                          "home_ml_bets_pct", "home_ml_money_pct", "consensus_home_spread", "consensus_total"])
    n2 = _append_changed(os.path.join(R, "books", f"{dd}.csv"), books, ["game_id", "book"],
                         ["home_spread", "home_spread_odds", "away_spread_odds", "total", "over_odds", "under_odds",
                          "home_ml", "away_ml"])
    return n1, n2


# ---------------- player props (DraftKings via ESPN) ----------------
def _athlete(ref, cache):
    aid = ref.split("/athletes/")[1].split("?")[0]
    if aid not in cache:
        try:
            a = espn._get(ref.replace("http://", "https://"))
            tm = (a.get("team") or {}).get("$ref", "")
            cache[aid] = dict(athlete_id=aid, player=a.get("displayName"), position=(a.get("position") or {}).get("abbreviation"),
                              espn_team_id=tm.split("/teams/")[1].split("?")[0] if "/teams/" in tm else None)
        except Exception:
            cache[aid] = dict(athlete_id=aid, player=None, position=None, espn_team_id=None)
        cache[aid]["_new"] = True
    return aid


def props_snapshot(now, day, odds_rows, full=False):
    """DraftKings player props for each game still to tip.
    Main over/under lines (points, rebounds, assists, 3s, combos, steals, blocks) every check;
    with full=True also milestones (20+ points ...), team props and quarter/half lines."""
    apath = os.path.join(R, "props_athletes.csv")
    cache = {r["athlete_id"]: r for r in pd.read_csv(apath, dtype=str).to_dict("records")} if os.path.exists(apath) else {}
    main, other = [], []
    for r in odds_rows:
        items, page = [], 1
        while True:
            u = (f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{r['espn_event_id']}/competitions/"
                 f"{r['espn_event_id']}/odds/100/propBets?lang=en&region=us&limit=1000&page={page}")
            p = espn._get(u); items += p.get("items", [])
            if page >= (p.get("pageCount") or 1): break
            page += 1
        seen = {}
        for i in items:
            name = (i.get("type") or {}).get("name", "")
            ath = i.get("athlete", {}).get("$ref")
            is_main = bool(ath) and name.startswith("Total ")
            if not (is_main or full): continue
            aid = _athlete(ath, cache) if ath else None
            od = (i.get("odds") or {}).get("american") or {}
            tgt = lambda w: ((i.get(w) or {}).get("target") or {}).get("value")
            row = dict(seen_at_et=str(now)[:16], game_id=r["game_id"], date=r["date"], market=name, athlete_id=aid,
                       player=cache.get(aid, {}).get("player") if aid else None,
                       team_ref=(i.get("team") or {}).get("$ref", "").split("/teams/")[-1].split("?")[0] or None,
                       line=_num(tgt("current")), odds=_num(od.get("value")),
                       open_line=_num(tgt("open")), open_odds=_num(od.get("open")), book_updated=i.get("lastUpdated"))
            if is_main:   # listed in pairs, over first (checked against DraftKings' milestones: 55 of 57)
                k = (name, aid); n = seen.get(k, 0); seen[k] = n + 1
                row["side"] = "over" if n == 0 else "under" if n == 1 else f"extra{n}"
                main.append(row)
            else:
                k = (name, aid, row["team_ref"], row["line"]); n = seen.get(k, 0); seen[k] = n + 1
                row["side"] = f"{row['line']}|{n}"   # milestones etc.: one row per threshold
                other.append(row)
    os.makedirs(os.path.join(R, "props"), exist_ok=True)
    dd = pd.Timestamp(day).date()
    vals = ["line", "odds"]
    n1 = _append_changed(os.path.join(R, "props", f"{dd}.csv"), main, ["market", "athlete_id", "side", "game_id"], vals)
    n2 = _append_changed(os.path.join(R, "props", f"{dd}_other.csv"), other,
                         ["market", "athlete_id", "team_ref", "side", "game_id"], vals) if full else 0
    newa = [dict((k, v) for k, v in a.items() if k != "_new") for a in cache.values() if a.get("_new")]
    if newa: pd.DataFrame(newa).to_csv(apath, mode="a", header=not os.path.exists(apath), index=False)
    return n1, n2
