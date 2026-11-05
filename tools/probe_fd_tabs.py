"""Nov 5, 2026 (probe 2): FanDuel tab slugs, customPageId per sport, and DraftKings volume per league. Writes research/probes/fd_tabs_probe.md."""
import sys, json, re, datetime as dt
from curl_cffi import requests as R
W = sys.argv[1] if len(sys.argv) > 1 else "."
AK = "_ak=FhMFpcPWXMeyZxOx"; FD = "https://sbapi.ct.sportsbook.fanduel.com/api"; DK = "https://sportsbook-nash.draftkings.com/api/sportscontent"
out = [f"# FanDuel tabs / page ids probe, {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n"]
def get(url):
    try: return R.get(url, impersonate="chrome124", timeout=40, headers={"Accept": "application/json", "Referer": "https://sportsbook.draftkings.com/"})
    except Exception as e: out.append(f"- ERROR {url[-80:]}: {type(e).__name__}"); return None
out.append("## FanDuel customPageId candidates (events with ' @ ' or ' v ' in the name / markets)")
for pid in ("nba", "nhl", "nfl", "mlb", "wnba", "ncaab", "ncaaf", "college-football", "college-basketball", "ncaa-basketball", "ncaa-football", "womens-college-basketball",
            "ncaaw", "college-hockey", "ncaah", "ncaa-hockey", "college-basketball-women", "cbb", "cfb"):
    r = get(f"{FD}/content-managed-page?page=CUSTOM&customPageId={pid}&{AK}&timezone=America%2FNew_York")
    if r is None: continue
    if r.status_code != 200: out.append(f"- {pid}: HTTP {r.status_code}"); continue
    try:
        att = r.json().get("attachments", {}); evs = att.get("events", {})
        g = [v.get("name") for v in evs.values() if " @ " in str(v.get("name")) or " v " in str(v.get("name"))]
        out.append(f"- {pid}: HTTP 200, {len(r.content)} bytes, events {len(evs)}, game events {len(g)}, markets {len(att.get('markets', {}))}; e.g. {g[:2]}")
    except Exception as e: out.append(f"- {pid}: parse {e}")
r = get(f"{FD}/content-managed-page?page=CUSTOM&customPageId=nba&{AK}&timezone=America%2FNew_York")
evs = r.json()["attachments"]["events"]; eid = next(k for k, v in evs.items() if " @ " in str(v.get("name")))
rd = get(f"{FD}/event-page?{AK}&eventId={eid}&timezone=America%2FNew_York").json()
base = {m.get("marketName") for m in rd["attachments"]["markets"].values()}
out.append(f"\n## FanDuel event {eid} ({evs[eid].get('name')}): default tab {len(base)} markets; tabs: " + ", ".join(f"{k}:{v['title']}" for k, v in rd["layout"]["tabs"].items()))
for k, v in rd["layout"]["tabs"].items():
    t = v["title"]; slugs = []
    for s in (re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-"), t.lower().replace(" ", "-"), str(k)):
        if s not in slugs: slugs.append(s)
    for s in slugs:
        r2 = get(f"{FD}/event-page?{AK}&eventId={eid}&tab={s}&timezone=America%2FNew_York")
        if r2 is None or r2.status_code != 200: out.append(f"- tab '{t}' slug '{s}': HTTP {r2.status_code if r2 is not None else 'err'}"); continue
        mk = r2.json().get("attachments", {}).get("markets", {}); names = {m.get("marketName") for m in mk.values()}
        out.append(f"- tab '{t}' slug '{s}': {len(mk)} markets, {'SAME AS DEFAULT' if names == base else 'different'}; " + "; ".join(sorted(map(str, names))[:5]))
        if names != base: break
out.append("\n## DraftKings volume: categories / subcategories per league")
for name, lid in (("NBA", 42648), ("NHL", 42133), ("NFL", 88808), ("NCAAM", 92483), ("NCAAW", 36647), ("NCAAF", 87637), ("College Hockey", 84813), ("WNBA", 94682), ("MLB", 84240)):
    r = get(f"{DK}/dkusct/v1/leagues/{lid}")
    if r is None or r.status_code != 200: out.append(f"- {name} {lid}: HTTP {r.status_code if r is not None else 'err'}"); continue
    j = r.json()
    out.append(f"- {name} {lid}: events {len(j.get('events', []))}, categories {len(j.get('categories', []))}, subcategories {len(j.get('subcategories', []))}; categories: " + ", ".join(c["name"] for c in j.get("categories", [])[:12]))
open(f"{W}/research/probes/fd_tabs_probe.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
