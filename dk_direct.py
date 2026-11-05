"""DraftKings' OWN Connecticut odds feed (Nov 5, 2026, Jeffrey: "see every single line every minute ... directly, not through ESPN").

Why it exists: Action Network's DraftKings number was stale for games DraftKings had not posted (POR @ LAL 238.5 and PHI @ CLE 234.5 on Nov 5;
DraftKings itself showed PHI @ CLE 230.5 and no POR @ LAL), and ESPN's copy lags by hours.
Access: plain requests get HTTP 403 (Akamai) from GitHub, and from Jeffrey's home PowerShell too. A Chrome-fingerprint client (curl_cffi) gets 200
from GitHub's servers (research/probes/dk_cffi_probe.md). One request per league returns every game's moneyline, spread and total with prices
(about 50-80 KB). Props, alt lines and quarters live in the category endpoints (not built yet; layout in research/probes/dk_nba_dkusct_sample.json).

  python dk_direct.py WORKDIR        record every change (all NBA / NHL / NFL games) to research/dk_direct/YYYY-MM-DD.csv.gz and
                                     write state/dk_direct_now.json (what DraftKings shows right now). Run every minute by alert_loop.sh.
Library: now(sport) -> DataFrame of the current lines; total(sport, date, home, away) -> (points, over_price, under_price) or None.
Never raises: a failed fetch returns an empty frame (callers fall back to Action Network / ESPN)."""
import os, sys, json, time, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

LEAGUES = {"nba": 42648, "nhl": 42133, "nfl": 88808}
SITE = "dkusct"                      # Connecticut's DraftKings (dkusnj = New Jersey; same NBA lines at the Nov 5 probe)
URL = "https://sportsbook-nash.draftkings.com/api/sportscontent/{site}/v1/leagues/{lg}"
ET = ZoneInfo("America/New_York")
NBA_CODE = {"PHO": "phx", "PHX": "phx", "SA": "sa", "SAS": "sa", "GS": "gs", "GSW": "gs", "NO": "no", "NOP": "no", "NY": "ny", "NYK": "ny",
            "UTA": "utah", "UTAH": "utah", "WAS": "wsh", "WSH": "wsh", "BKN": "bkn", "BRK": "bkn", "CHA": "cha", "CHO": "cha"}
_CACHE = {}


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return float("nan")


def american(s):
    s = str(s or "").replace("−", "-").replace("+", "").strip()
    return _num(s)


def fetch(sport, site=SITE, tries=2):
    """the raw reply for a league (dict) or None"""
    from curl_cffi import requests as R
    for i in range(tries):
        try:
            r = R.get(URL.format(site=site, lg=LEAGUES[sport]), impersonate="chrome124", timeout=25,
                      headers={"Accept": "application/json", "Referer": "https://sportsbook.draftkings.com/"})
            if r.status_code == 200: return r.json()
            print(f"DraftKings direct {sport}: HTTP {r.status_code}")
        except Exception as e:
            print(f"DraftKings direct {sport}: {type(e).__name__} {str(e)[:80]}")
        time.sleep(2)
    return None


def code(sport, short, name=""):
    s = str(short or "").upper()
    if sport == "nba": return NBA_CODE.get(s, s.lower())
    return s.lower()


def rows(j, sport, snap):
    """tidy rows from a league reply: one per selection (game lines)"""
    out = []
    if not j: return pd.DataFrame(out)
    sels = {}
    for s in j.get("selections", []): sels.setdefault(s["marketId"], []).append(s)
    mk = {}
    for m in j.get("markets", []): mk.setdefault(m["eventId"], []).append(m)
    for e in j.get("events", []):
        if e.get("status") not in (None, "NOT_STARTED"): continue          # started games belong to live.py
        p = {x.get("venueRole"): x for x in e.get("participants", [])}
        h, a = p.get("Home") or {}, p.get("Away") or {}
        start = pd.Timestamp(e["startEventDate"]).tz_convert(ET).tz_localize(None)
        for m in mk.get(e["id"], []):
            for s in sels.get(m["id"], []):
                out.append(dict(snap_et=snap, sport=sport, event_id=e["id"], date=str(start.date()), start_et=str(start)[:16],
                                away=code(sport, (a.get("metadata") or {}).get("shortName")), home=code(sport, (h.get("metadata") or {}).get("shortName")),
                                away_name=a.get("name"), home_name=h.get("name"), market=m.get("name"), market_id=m["id"],
                                sel_id=s["id"], label=s.get("label"), outcome=s.get("outcomeType"), points=s.get("points"),
                                price=american((s.get("displayOdds") or {}).get("american"))))
    return pd.DataFrame(out)


def now(sport, max_age=20):
    """current lines (cached for max_age seconds within a process); empty frame on failure"""
    c = _CACHE.get(sport)
    if c and time.time() - c[0] < max_age: return c[1]
    snap = str(dt.datetime.now(ET).replace(tzinfo=None, microsecond=0))
    try: df = rows(fetch(sport), sport, snap)
    except Exception as e:
        print("DraftKings direct parse failed:", type(e).__name__, str(e)[:80]); df = pd.DataFrame()
    _CACHE[sport] = (time.time(), df); return df


def total(sport, date, home, away):
    """(points, over price, under price) of DraftKings' full-game total for this game right now, or None if DraftKings has not posted it"""
    df = now(sport)
    if not len(df): return None
    g = df[(df.date == str(date)) & (df.home == home) & (df.away == away) & (df.market == "Total")]
    ov, un = g[g.outcome == "Over"], g[g.outcome == "Under"]
    if not len(ov) or not len(un): return None
    return float(ov.points.iloc[0]), float(ov.price.iloc[0]), float(un.price.iloc[0])


def merge_current(L, sport="nba"):
    """Replace the current spread / total / prices in a lines frame (ESPN + Action Network merge in alert.py) with DraftKings' own.
    A game DraftKings has not posted gets NaN current lines (so no alert), line_source 'dkdirect_unposted'. If the direct fetch fails,
    L comes back unchanged. Spread columns are the HOME spread, as in the ESPN frame."""
    D = now(sport)
    if not len(D) or not len(L): return L
    L = L.copy(); L["line_source"] = L.get("line_source", "espn")
    cols = ["current_spread", "current_total", "current_home_spread_odds", "current_away_spread_odds", "current_over_odds", "current_under_odds"]
    for c in cols:
        if c not in L: L[c] = float("nan")
        L[c] = L[c].astype(float)
    for i, r in L.iterrows():
        g = D[(D.date == str(pd.Timestamp(r["date"]).date())) & (D.home == r["home"]) & (D.away == r["away"])]
        if not len(g):
            for c in cols: L.at[i, c] = float("nan")
            L.at[i, "line_source"] = "dkdirect_unposted"; continue
        sp, tt = g[g.market == "Spread"], g[g.market == "Total"]
        h, a = sp[sp.outcome == "Home"], sp[sp.outcome == "Away"]
        ov, un = tt[tt.outcome == "Over"], tt[tt.outcome == "Under"]
        L.at[i, "current_spread"] = float(h.points.iloc[0]) if len(h) else float("nan")
        L.at[i, "current_home_spread_odds"] = float(h.price.iloc[0]) if len(h) else float("nan")
        L.at[i, "current_away_spread_odds"] = float(a.price.iloc[0]) if len(a) else float("nan")
        L.at[i, "current_total"] = float(ov.points.iloc[0]) if len(ov) else float("nan")
        L.at[i, "current_over_odds"] = float(ov.price.iloc[0]) if len(ov) else float("nan")
        L.at[i, "current_under_odds"] = float(un.price.iloc[0]) if len(un) else float("nan")
        L.at[i, "line_source"] = "dkdirect"
    return L


def slip_link(sport, date, home, away, side):
    """DraftKings bet-slip link for the full-game Over / Under from the live feed (event id + selection id, the same layout ESPN's links use,
    but never an hour behind). None if DraftKings has not posted the game. Not yet tested by tapping one."""
    df = now(sport)
    if not len(df): return None
    g = df[(df.date == str(date)) & (df.home == home) & (df.away == away) & (df.market == "Total") & (df.outcome == str(side).capitalize())]
    if not len(g): return None
    return f"https://sportsbook.draftkings.com/event/{g.event_id.iloc[0]}?outcomes={g.sel_id.iloc[0]}"


def record(W):
    """save every change since the last look (all leagues) and the current picture; returns the number of changed rows"""
    sd = os.path.join(W, "state"); rd = os.path.join(W, "research", "dk_direct"); os.makedirs(rd, exist_ok=True)
    lp = os.path.join(sd, "dk_direct_last.json")
    last = json.load(open(lp)) if os.path.exists(lp) else {}
    new, cur, now_all = [], {}, []
    for sport in LEAGUES:
        df = now(sport, max_age=0)
        if not len(df): continue
        now_all.append(df)
        for r in df.itertuples():
            k = f"{r.event_id}|{r.sel_id}"; v = [None if pd.isna(r.points) else float(r.points), None if pd.isna(r.price) else float(r.price)]
            cur[k] = v
            if last.get(k) != v: new.append(r._asdict())
    if not now_all: print("DraftKings direct: nothing fetched"); return 0
    # keep memory of games not in this fetch (a league that failed this minute) so they are not logged as new next time
    for k, v in last.items(): cur.setdefault(k, v)
    json.dump(cur, open(lp, "w"))
    allnow = pd.concat(now_all, ignore_index=True); allnow.to_json(os.path.join(sd, "dk_direct_now.json"), orient="records")
    if new:
        f = os.path.join(rd, f"{dt.datetime.now(ET):%Y-%m-%d}.csv.gz")
        N = pd.DataFrame(new).drop(columns=["Index"], errors="ignore")
        old = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame()
        pd.concat([old, N], ignore_index=True).to_csv(f, index=False, compression="gzip")
    print(f"DraftKings direct: {len(allnow)} selections, {len(new)} new or changed")
    return len(new)


if __name__ == "__main__":
    record(os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ".")
