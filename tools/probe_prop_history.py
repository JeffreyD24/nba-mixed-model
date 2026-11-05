"""Probe free sources of PAST NBA player-prop lines (run on GitHub). Writes research/probes/prop_history_probe.md.
  1) BettingPros public web API (the key their own site sends; same idea as FanDuel's public _ak key)
  2) ESPN core API propBets for a past game
"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
W = os.path.abspath(sys.argv[1]); OUT = os.path.join(W, "research", "probes"); os.makedirs(OUT, exist_ok=True)
BP_KEY = "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "application/json",
       "x-api-key": BP_KEY, "Origin": "https://www.bettingpros.com", "Referer": "https://www.bettingpros.com/"}
def get(u, h=HDR):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=30) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, e.read()[:200].decode("utf-8", "ignore")
    except Exception as e: return -1, str(e)[:200]
L = ["# Past prop lines probe", "", "## BettingPros"]
c, m = get("https://api.bettingpros.com/v3/markets?sport=NBA&limit=300")
mk = (m or {}).get("markets", []) if isinstance(m, dict) else []
L.append(f"- markets: HTTP {c}, {len(mk)}; " + "; ".join(f"{x.get('id')}={x.get('name') or x.get('slug')}" for x in mk[:60]))
for day in ["2021-12-15", "2022-12-15", "2023-12-15", "2024-12-15", "2026-01-15"]:
    c, e = get(f"https://api.bettingpros.com/v3/events?sport=NBA&date={day}")
    evs = (e or {}).get("events", []) if isinstance(e, dict) else []
    L.append(f"- events {day}: HTTP {c}, {len(evs)} events" + (f"; first id {evs[0].get('id')} {evs[0].get('home')} vs {evs[0].get('visitor')}" if evs else f" {str(e)[:120]}"))
    if evs:
        ids = ":".join(str(x["id"]) for x in evs[:3])
        q = urllib.parse.urlencode(dict(sport="NBA", market_id="156:157:151:162", event_id=ids, location="ALL", limit=50, page=1))
        c2, o = get(f"https://api.bettingpros.com/v3/offers?{q}")
        offers = (o or {}).get("offers", []) if isinstance(o, dict) else []
        L.append(f"  - offers (3 games, pts/reb/ast/3s): HTTP {c2}, {len(offers)} offers, total {(o or {}).get('_pagination') if isinstance(o, dict) else ''}")
        if offers:
            x = offers[0]; sel = x.get("selections", [])
            books = sorted({b.get("id") for s in sel for b in s.get("books", [])})
            ex = sel[0]["books"][0]["lines"][0] if sel and sel[0].get("books") and sel[0]["books"][0].get("lines") else {}
            L.append(f"  - first offer: market {x.get('market_id')} player {(x.get('participants') or [{}])[0].get('name')}; "
                     f"selections {[s.get('label') for s in sel]}; books {books}; example line {json.dumps(ex)[:300]}")
            if day == "2023-12-15": open(os.path.join(OUT, "bp_offer_sample.json"), "w").write(json.dumps(o)[:300000])
    time.sleep(2)
c, b = get("https://api.bettingpros.com/v3/books")
bk = (b or {}).get("books", []) if isinstance(b, dict) else []
L.append(f"- books: HTTP {c}; " + "; ".join(f"{x.get('id')}={x.get('name')}" for x in bk[:40]))

L += ["", "## ESPN core propBets for past games"]
H2 = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
for ev in ["401585109", "401705000", "401810000"]:
    c, p = get(f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{ev}/competitions/{ev}/odds/100/propBets?lang=en&region=us&limit=50", H2)
    n = (p or {}).get("count") if isinstance(p, dict) else None
    it = (p or {}).get("items", [])[:1] if isinstance(p, dict) else []
    L.append(f"- event {ev}: HTTP {c}, count {n}; sample {json.dumps(it)[:250]}")
    c, p = get(f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{ev}/competitions/{ev}/odds?lang=en&region=us", H2)
    L.append(f"  - odds providers: HTTP {c}, {[i.get('provider', {}).get('name') for i in (p or {}).get('items', [])] if isinstance(p, dict) else p}")
open(os.path.join(OUT, "prop_history_probe.md"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
