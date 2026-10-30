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


def _append_changed(path, rows, key_cols, value_cols):
    """append only rows whose values differ from the last recorded row for the same key"""
    if not rows: return 0
    new = pd.DataFrame(rows)
    if os.path.exists(path):
        old = pd.read_csv(path)
        last = old.groupby(key_cols).tail(1).set_index(key_cols)[value_cols] if len(old) else None
    else:
        old, last = None, None
    keep = []
    for r in new.itertuples(index=False):
        rd = r._asdict(); k = tuple(rd[c] for c in key_cols)
        k = k if len(k) > 1 else k[0]
        if last is not None and k in last.index:
            prev = last.loc[k]
            same = all((pd.isna(prev[c]) and pd.isna(rd[c])) or (not pd.isna(prev[c]) and not pd.isna(rd[c]) and str(prev[c]) == str(rd[c]))
                       for c in value_cols)
            if same: continue
        keep.append(rd)
    if keep:
        out = pd.DataFrame(keep)
        out.to_csv(path, mode="a", header=not os.path.exists(path), index=False)
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
