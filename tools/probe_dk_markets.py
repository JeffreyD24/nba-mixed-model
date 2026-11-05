"""Nov 5, 2026: what do DraftKings' and FanDuel's own feeds expose beyond game lines (props, alt lines, quarters, halves), and which league ids exist for
the other sports? Runs on a GitHub runner with a Chrome TLS fingerprint. Writes research/probes/dk_fd_markets_probe.md + a few raw samples."""
import sys, json, datetime as dt
from curl_cffi import requests as R
W = sys.argv[1] if len(sys.argv) > 1 else "."
DK = "https://sportsbook-nash.draftkings.com/api/sportscontent"
H = {"Accept": "application/json", "Referer": "https://sportsbook.draftkings.com/"}
out = [f"# DraftKings / FanDuel markets probe, {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n"]
def get(url, **kw):
    try: return R.get(url, impersonate="chrome124", timeout=40, headers=kw.pop("headers", H), **kw)
    except Exception as e: out.append(f"- ERROR {url[-90:]}: {type(e).__name__} {str(e)[:80]}"); return None

# 1. DraftKings categories for the NBA
out.append("## DraftKings NBA: category endpoints")
out.append("| url suffix | HTTP | bytes | events | markets | selections | sample market names |"); out.append("|---|---|---|---|---|---|---|")
base = f"{DK}/dkusct/v1/leagues/42648"
for cid in (487, 1215, 1216, 1217, 1218, 583, 1293, 520, 522, 521, 523, 1157, 1683, 1684, 1320, 1206, 1280, 1241, 1921):
    r = get(f"{base}/categories/{cid}")
    if r is None: continue
    note = ""
    if r.status_code == 200:
        try:
            j = r.json(); names = []
            for m in j.get("markets", []):
                n = m.get("name")
                if n not in names: names.append(n)
            out.append(f"| categories/{cid} | 200 | {len(r.content)} | {len(j.get('events', []))} | {len(j.get('markets', []))} | {len(j.get('selections', []))} | {'; '.join(map(str, names[:8]))} |")
            if cid in (1215, 520, 522):
                json.dump(j, open(f"{W}/research/probes/dk_nba_cat{cid}_sample.json", "w"))
        except Exception as e: out.append(f"| categories/{cid} | 200 | {len(r.content)} | not JSON: {e} | | | |")
    else: out.append(f"| categories/{cid} | {r.status_code} | {len(r.content)} | | | | {r.text[:60]!r} |")
# subcategory form
r0 = get(f"{base}")
if r0 is not None and r0.status_code == 200:
    j0 = r0.json(); alt = [s for s in j0.get("subcategories", []) if s.get("categoryId") == 487]
    out.append("\n## DraftKings NBA: subcategory endpoints (Game Lines, 487)")
    for s in alt[:6]:
        r = get(f"{base}/categories/487/subcategories/{s['id']}")
        if r is None: continue
        d = r.json() if r.status_code == 200 else {}
        out.append(f"- {s['name']} (id {s['id']}): HTTP {r.status_code}, {len(r.content)} bytes, markets {len(d.get('markets', []))}, selections {len(d.get('selections', []))}")

# 2. league ids for other sports (names read from the reply)
out.append("\n## DraftKings league ids (name read from the reply; 0 events means off-season or none listed)")
cand = {}
for lid in (42648, 42133, 88808, 92483, 87637, 94682, 84240, 36647, 41484, 41473, 40253, 33241, 91522, 92060, 93046, 89073, 80402, 88670, 87639):
    r = get(f"{DK}/dkusct/v1/leagues/{lid}")
    if r is None or r.status_code != 200: out.append(f"- {lid}: HTTP {r.status_code if r is not None else 'err'}"); continue
    try:
        j = r.json(); lg = (j.get("leagues") or [{}])[0]; sp = (j.get("sports") or [{}])[0]
        out.append(f"- {lid}: {sp.get('name')} / {lg.get('name')}: {len(j.get('events', []))} events, {len(j.get('markets', []))} markets")
    except Exception as e: out.append(f"- {lid}: not JSON {e}")
for url in (f"{DK}/navigation/dkusct/v1/nav/sports", f"{DK}/navigation/dkusct/v1/nav/leagues/42648", f"{DK}/dkusct/v1/sports", f"{DK}/dkusct/v1/sports/2", f"{DK}/dkusct/v1/leagues"):
    r = get(url)
    if r is not None:
        out.append(f"- nav {url[len(DK):]}: HTTP {r.status_code}, {len(r.content)} bytes, head {r.text[:160]!r}")
        if r.status_code == 200 and len(r.content) < 400000: open(f"{W}/research/probes/dk_nav_{url.rsplit('/', 1)[-1]}.json", "w").write(r.text)

# 3. FanDuel
out.append("\n## FanDuel Connecticut (sbapi.ct)")
AK = "_ak=FhMFpcPWXMeyZxOx"
FD = "https://sbapi.ct.sportsbook.fanduel.com/api"
r = get(f"{FD}/content-managed-page?page=CUSTOM&customPageId=nba&{AK}&timezone=America%2FNew_York", headers={"Accept": "application/json"})
ev_ids = []
if r is not None:
    out.append(f"- content-managed-page nba: HTTP {r.status_code}, {len(r.content)} bytes")
    if r.status_code == 200:
        try:
            j = r.json(); att = j.get("attachments", {}); evs = att.get("events", {}); mk = att.get("markets", {})
            out.append(f"- events {len(evs)}, markets {len(mk)}; sample markets: " + "; ".join(sorted({str(m.get('marketName')) for m in mk.values()})[:14]))
            ev_ids = [k for k, v in evs.items() if " @ " in str(v.get("name"))][:3]
            out.append("- sample events: " + "; ".join(f"{k}={evs[k].get('name')}" for k in ev_ids))
        except Exception as e: out.append(f"- parse failed: {e}")
for eid in ev_ids[:1]:
    r = get(f"{FD}/event-page?{AK}&eventId={eid}&timezone=America%2FNew_York", headers={"Accept": "application/json"})
    if r is not None and r.status_code == 200:
        j = r.json(); att = j.get("attachments", {}); mk = att.get("markets", {})
        names = sorted({str(m.get("marketName")) for m in mk.values()})
        out.append(f"- event-page {eid}: HTTP 200, {len(r.content)} bytes, markets {len(mk)}; names: " + "; ".join(names[:40]))
        out.append(f"- event-page tabs/keys: {list(j.keys())}; layout tabs: " + json.dumps(j.get('layout', {}))[:500])
        json.dump(j, open(f"{W}/research/probes/fd_nba_event_sample.json", "w"))
    elif r is not None: out.append(f"- event-page {eid}: HTTP {r.status_code} {r.text[:120]!r}")
    for tab in ("player-points", "player-rebounds", "quarters", "halves", "alternate-lines"):
        r = get(f"{FD}/event-page?{AK}&eventId={eid}&tab={tab}&timezone=America%2FNew_York", headers={"Accept": "application/json"})
        if r is not None and r.status_code == 200:
            mk = r.json().get("attachments", {}).get("markets", {})
            out.append(f"- tab {tab}: HTTP 200, markets {len(mk)}; " + "; ".join(sorted({str(m.get('marketName')) for m in mk.values()})[:8]))
        elif r is not None: out.append(f"- tab {tab}: HTTP {r.status_code}")
open(f"{W}/research/probes/dk_fd_markets_probe.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
