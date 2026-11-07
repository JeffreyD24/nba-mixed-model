"""All-markets odds feed: every line DraftKings and FanDuel (Connecticut) show, polled from their own feeds (Nov 5, 2026, Jeffrey).

DraftKings: league reply (game lines, every game) + every category + every subcategory (props, alternate lines, quarters, halves, team totals, ...).
FanDuel:    league page (every game's main markets) + each game's event page for every tab (player props, quarters, half, alt lines, race to, ...).
Both need a Chrome TLS fingerprint (curl_cffi); plain requests get HTTP 403. See research/probes/dk_cffi_probe.md, dk_fd_markets_probe.md, fd_tabs_probe.md.

  python odds_feed.py WORKDIR          one tick (run about every 60 s by feed_loop.sh)
Config: WORKDIR/feed_config.json  {"dk":[{"sport":"nba","league_id":42648}], "fd":[{"sport":"nba","page":"nba"}]} (+ optional "cadence", "*_budget").
Each endpoint is fetched when it is due (cadence below, seconds), most overdue first, up to a per-tick request budget, so the load stays
steady whatever the league size. Only CHANGES are saved (a selection whose line or price moved, appeared, or disappeared = status "off"),
one new small file per 5 minutes: research/feed/<book>/<sport>/<YYYY-MM-DD>/<HHMM>_<run id>.csv.gz (never rewritten after its window, so git does not bloat).
Memory between ticks (last values, schedule) lives in WORKDIR/_tmp/feed_state.json, not committed: a fresh job re-logs everything once.
Started games are skipped (live lines belong to live.py). Never raises: a failed fetch is counted and the tick goes on."""
import os, sys, json, re, time, datetime as dt
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

ET = ZoneInfo("America/New_York")
DKB = "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusct/v1"
FDB = "https://sbapi.ct.sportsbook.fanduel.com/api"
AK = "_ak=FhMFpcPWXMeyZxOx"
CAD = {"dk_root": 60, "dk_category": 300, "dk_sub": 600, "dk_slow": 3600, "fd_page": 60, "fd_event": 300, "fd_tab": 600, "fd_far": 3600}
SLOW = re.compile(r"futures|awards?|wins?\b|playoffs?|play in|champion|mvp|season|cup|specials? *$|seed|division|conference", re.I)
FD_SKIP_TABS = {"Same Game Parlay™", "Odd/Even", "Popular"}      # same as the default tab / a subset of the other tabs (fd_tabs_probe.md)
FAR_HOURS = 48
_STATS = {"requests": 0, "errors": 0, "blocked": 0}



# Nov 7, 2026 bug fix (RULE 11): two feed jobs once wrote the same <HHMM>.csv.gz and every later save hit an add/add merge conflict
# (nba-mixed-model run 42311335030 lost 18:42 ET onward). Each job now adds its run id, so files from different jobs never collide.
RUN_TAG = "_" + (os.environ.get("GITHUB_RUN_ID", "") or "local")[-8:]

def http_get(url, tries=2):
    """(status, json or None). 403 / 429 are not retried (hammering a block makes it worse)."""
    from curl_cffi import requests as R
    for i in range(tries):
        try:
            _STATS["requests"] += 1
            r = R.get(url, impersonate="chrome124", timeout=30, headers={"Accept": "application/json", "Referer": "https://sportsbook.draftkings.com/"})
            if r.status_code == 200: return 200, r.json()
            if r.status_code in (403, 429): _STATS["blocked"] += 1; return r.status_code, None
            time.sleep(1.5)
        except Exception:
            time.sleep(1.5)
    _STATS["errors"] += 1
    return 0, None


def num(x):
    try: return float(str(x).replace("−", "-").replace("+", ""))
    except (TypeError, ValueError): return float("nan")


# ------------------------------------------------------------------ DraftKings
def dk_rows(j, sport, snap, subs, cats):
    out = []
    if not j: return out
    sel = {}
    for s in j.get("selections", []): sel.setdefault(s["marketId"], []).append(s)
    mk = {}
    for m in j.get("markets", []): mk.setdefault(m["eventId"], []).append(m)
    for e in j.get("events", []):
        if e.get("status") not in (None, "NOT_STARTED"): continue
        p = {x.get("venueRole"): x for x in e.get("participants", [])}
        try: start = str(pd.Timestamp(e["startEventDate"]).tz_convert(ET).tz_localize(None))[:16]
        except Exception: start = ""
        for m in mk.get(e["id"], []):
            sc = subs.get(m.get("subcategoryId")) or subs.get(str(m.get("subcategoryId"))) or ("", "")
            for s in sel.get(m["id"], []):
                pl = next((x.get("name") for x in s.get("participants", []) if x.get("type") == "Player"), "")
                out.append(dict(snap_et=snap, book="dk", sport=sport, event_id=str(e["id"]), start_et=start, event=e.get("name"),
                                away=(p.get("Away") or {}).get("name"), home=(p.get("Home") or {}).get("name"),
                                category=sc[0], subcategory=sc[1], market_id=str(m["id"]), market=m.get("name"),
                                market_type=(m.get("marketType") or {}).get("name"), sel_id=str(s["id"]), label=s.get("label"),
                                outcome=s.get("outcomeType"), points=s.get("points"), price=num((s.get("displayOdds") or {}).get("american")),
                                player=pl, main=bool(s.get("main")), status="on"))
    return out


def dk_maps(root):
    cats = {c["id"]: c["name"] for c in root.get("categories", [])}
    subs = {s["id"]: (cats.get(s["categoryId"], ""), s["name"]) for s in root.get("subcategories", [])}
    return cats, subs


# ------------------------------------------------------------------ FanDuel
def fd_rows(j, sport, snap, tab=""):
    out = []
    if not j: return out
    att = j.get("attachments", {}); evs = att.get("events", {})
    for m in att.get("markets", {}).values():
        if m.get("inPlay"): continue
        e = evs.get(str(m.get("eventId"))) or {}
        name = e.get("name") or ""
        away, home = (name.split(" @ ", 1) + [None])[:2] if " @ " in name else (None, None)
        start = ""
        try: start = str(pd.Timestamp(e.get("openDate") or m.get("marketTime")).tz_convert(ET).tz_localize(None))[:16]
        except Exception: pass
        for r in m.get("runners", []):
            od = ((r.get("winRunnerOdds") or {}).get("americanDisplayOdds") or {}).get("americanOdds")
            status = "on" if (m.get("marketStatus") == "OPEN" and r.get("runnerStatus") == "ACTIVE") else f"{m.get('marketStatus')}/{r.get('runnerStatus')}"
            out.append(dict(snap_et=snap, book="fd", sport=sport, event_id=str(m.get("eventId")), start_et=start, event=name, away=away, home=home,
                            category=tab, subcategory="", market_id=str(m.get("marketId")), market=m.get("marketName"), market_type=m.get("marketType"),
                            sel_id=f"{m.get('marketId')}:{r.get('selectionId')}", label=r.get("runnerName"), outcome="", points=r.get("handicap"),
                            price=num(od), player="", main=False, status=status))
    return out


def slug(title): return re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")


# ------------------------------------------------------------------ state, scheduling
def load_state(W):
    f = os.path.join(W, "_tmp", "feed_state.json")
    try: return json.load(open(f))
    except Exception: return {"sched": {}, "last": {}, "ep": {}, "dk": {}, "fd": {}}


def save_state(W, S):
    os.makedirs(os.path.join(W, "_tmp"), exist_ok=True)
    json.dump(S, open(os.path.join(W, "_tmp", "feed_state.json"), "w"), separators=(",", ":"))


def changes(rows, ep, S):
    """rows of changed / new selections, plus 'off' rows for selections this endpoint showed last time and not now"""
    last, new_keys, out = S["last"], [], []
    for r in rows:
        k = f"{r['book']}|{r['event_id']}|{r['sel_id']}"
        pt = r.get("points")
        try: pt = None if pd.isna(pt) else float(pt)
        except (TypeError, ValueError): pt = str(pt)
        v = [pt, None if pd.isna(r["price"]) else float(r["price"]), r["status"]]
        new_keys.append(k)
        if last.get(k) != v: last[k] = v; out.append(r)
    for k in set(S["ep"].get(ep, [])) - set(new_keys):
        b, e, s = k.split("|", 2)
        if last.get(k, [None, None, "off"])[2] != "off":
            last[k] = [None, None, "off"]
            out.append(dict(snap_et=rows[0]["snap_et"] if rows else str(dt.datetime.now(ET).replace(tzinfo=None))[:19], book=b, event_id=e, sel_id=s,
                            price=float("nan"), status="off"))
    S["ep"][ep] = new_keys
    return out


def write(W, rows):
    if not rows: return 0
    df = pd.DataFrame(rows)
    snap = pd.to_datetime(df.snap_et.iloc[0]); win = snap.floor("5min")
    n = 0
    for (book, sport), g in df.groupby([df.book, df.sport.fillna("")]):
        d = os.path.join(W, "research", "feed", book, sport or "all", f"{win:%Y-%m-%d}"); os.makedirs(d, exist_ok=True)
        f = os.path.join(d, f"{win:%H%M}{RUN_TAG}.csv.gz")
        # dtype=str (Nov 6, 2026): read as numbers, FanDuel market ids lost a trailing zero (709.196153110 -> 709.19615311; ~8% of rows)
        old = pd.read_csv(f, low_memory=False, dtype={"event_id": str, "market_id": str, "sel_id": str}) if os.path.exists(f) else pd.DataFrame()
        pd.concat([old, g], ignore_index=True).to_csv(f, index=False, compression="gzip"); n += len(g)
    return n


def due_list(items, S, now, budget):
    """items: [(endpoint_key, cadence_s, payload)] -> the most overdue first, up to budget"""
    d = [(now - S["sched"].get(k, 0)) / c for k, c, _ in items]
    order = sorted(range(len(items)), key=lambda i: -d[i])
    return [items[i] for i in order if d[i] >= 1][:budget]


def tick(W, cfg=None, now=None):
    cfg = cfg or json.load(open(os.path.join(W, "feed_config.json")))
    cad = {**CAD, **cfg.get("cadence", {})}; now = now or time.time()
    snap = str(dt.datetime.fromtimestamp(now, ET).replace(tzinfo=None, microsecond=0))
    S = load_state(W); allrows = []; stat = {}
    pool = ThreadPoolExecutor(max_workers=cfg.get("workers", 6))
    # ---- DraftKings
    for L in cfg.get("dk", []):
        sp, lid = L["sport"], L["league_id"]; items = []
        root_key = f"dk|{sp}|root"
        st, root = http_get(f"{DKB}/leagues/{lid}") if now - S["sched"].get(root_key, 0) >= cad["dk_root"] else (None, None)
        if st == 200:
            S["sched"][root_key] = now; S["dk"][sp] = {"categories": root.get("categories", []), "subcategories": root.get("subcategories", [])}
            cats, subs = dk_maps(root); allrows += changes(dk_rows(root, sp, snap, subs, cats), root_key, S)
        meta = S["dk"].get(sp)
        if not meta: continue
        cats, subs = dk_maps(meta)
        for c in meta["categories"]:
            slow = bool(SLOW.search(c["name"]))
            items.append((f"dk|{sp}|cat|{c['id']}", cad["dk_slow"] if slow else cad["dk_category"], (f"{DKB}/leagues/{lid}/categories/{c['id']}", sp)))
        for s in meta["subcategories"]:
            slow = bool(SLOW.search(cats.get(s["categoryId"], ""))) or bool(SLOW.search(s["name"]))
            items.append((f"dk|{sp}|sub|{s['id']}", cad["dk_slow"] if slow else cad["dk_sub"],
                          (f"{DKB}/leagues/{lid}/categories/{s['categoryId']}/subcategories/{s['id']}", sp)))
        todo = due_list(items, S, now, cfg.get("dk_budget", 40))
        for (k, c, (url, sp_)), (st, j) in zip(todo, pool.map(lambda it: http_get(it[2][0]), todo)):
            if st != 200: stat[k] = st; continue
            S["sched"][k] = now; allrows += changes(dk_rows(j, sp_, snap, subs, cats), k, S)
    # ---- FanDuel
    for L in cfg.get("fd", []):
        sp, page = L["sport"], L["page"]; page_key = f"fd|{sp}|page"
        if now - S["sched"].get(page_key, 0) >= cad["fd_page"]:
            st, j = http_get(f"{FDB}/content-managed-page?page=CUSTOM&customPageId={page}&{AK}&timezone=America%2FNew_York")
            if st == 200:
                S["sched"][page_key] = now; allrows += changes(fd_rows(j, sp, snap, "page"), page_key, S)
                S["fd"][sp] = {str(k): {"name": v.get("name"), "open": v.get("openDate")} for k, v in j.get("attachments", {}).get("events", {}).items()
                               if " @ " in str(v.get("name"))}
        items = []
        for eid, e in S["fd"].get(sp, {}).items():
            try: hrs = (pd.Timestamp(e["open"]) - pd.Timestamp.now(tz="UTC")).total_seconds() / 3600
            except Exception: hrs = 0
            if hrs < -0.1: continue
            far = hrs > FAR_HOURS
            items.append((f"fd|{sp}|ev|{eid}|", cad["fd_far"] if far else cad["fd_event"], (eid, "")))
            for t in S.setdefault("fd_tabs", {}).get(eid, []):
                items.append((f"fd|{sp}|ev|{eid}|{t}", cad["fd_far"] if far else cad["fd_tab"], (eid, t)))
        todo = due_list(items, S, now, cfg.get("fd_budget", 40))
        def getf(it):
            eid, t = it[2]; return http_get(f"{FDB}/event-page?{AK}&eventId={eid}" + (f"&tab={slug(t)}" if t else "") + "&timezone=America%2FNew_York")
        for (k, c, (eid, t)), (st, j) in zip(todo, pool.map(getf, todo)):
            if st != 200: stat[k] = st; continue
            S["sched"][k] = now
            if not t:      # default tab: learn this event's tab list
                S.setdefault("fd_tabs", {})[eid] = [v["title"] for v in (j.get("layout", {}).get("tabs", {}) or {}).values() if v.get("title") not in FD_SKIP_TABS]
            allrows += changes(fd_rows(j, sp, snap, t or "default"), k, S)
    pool.shutdown()
    n = write(W, allrows); save_state(W, S)
    print(f"odds feed {snap}: {_STATS['requests']} requests, {n} changed rows, {_STATS['errors']} errors, {_STATS['blocked']} blocked" + (f", not ok: {stat}" if stat else ""))
    return n


if __name__ == "__main__":
    W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
    try: tick(W)
    except Exception as e: print("odds feed failed:", type(e).__name__, str(e)[:200])
