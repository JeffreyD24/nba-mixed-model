"""Probe: can GitHub's servers read FanDuel's live NBA player props (public, no login)? Writes research/probes/fd_props_probe.md."""
import os, sys, json, urllib.request, urllib.error
W = os.path.abspath(sys.argv[1]); OUT = os.path.join(W, "research", "probes"); os.makedirs(OUT, exist_ok=True)
AK = "FhMFpcPWXMeyZxOx"; BASE = "https://sbapi.ct.sportsbook.fanduel.com/api"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "application/json"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=30) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, None
    except Exception as e: return -1, str(e)
L = ["# FanDuel props probe", ""]
c, d = get(f"{BASE}/content-managed-page?page=CUSTOM&customPageId=nba&_ak={AK}&timezone=America%2FNew_York")
ev = (d or {}).get("attachments", {}).get("events", {}) if isinstance(d, dict) else {}
nba = [e for e in ev.values() if e.get("competitionId") in (10547864,) or "@" in e.get("name", "")]
L.append(f"- NBA page HTTP {c}; events {len(ev)}; with '@' {len(nba)}; sample {[e.get('name') for e in nba[:3]]}")
for e in nba[:2]:
    for tab in ("player-points", "player-rebounds", "player-assists", "player-threes", "popular"):
        c2, p = get(f"{BASE}/event-page?_ak={AK}&eventId={e['eventId']}&tab={tab}&timezone=America%2FNew_York")
        mk = (p or {}).get("attachments", {}).get("markets", {}) if isinstance(p, dict) else {}
        names = sorted({m.get("marketType") for m in mk.values()})[:12]
        ex = next((m for m in mk.values() if "POINTS" in str(m.get("marketType", "")).upper()), None)
        L.append(f"- {e['name']} tab {tab}: HTTP {c2}, markets {len(mk)}, types {names}")
        if ex: L.append(f"  - example: {ex.get('marketName')} | runners {[(r.get('runnerName'), r.get('handicap'), (r.get('winRunnerOdds') or {}).get('americanDisplayOdds')) for r in ex.get('runners', [])[:4]]}")
        if p and tab == "player-points": open(os.path.join(OUT, "fd_event_sample.json"), "w").write(json.dumps(p)[:400000])
open(os.path.join(OUT, "fd_props_probe.md"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
