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
