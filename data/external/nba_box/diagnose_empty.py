"""Print the raw ESPN summary structure for one known-empty game (CHI-SAC 2012-10-31, ESPN event 400277727, 2013 season) and one good game, so we can see why
Chicago / New Orleans 2013-2018 box scores come back with zero minutes. Output goes to the Actions log. Run from this folder."""
import sys, json
sys.path.insert(0, "../../.."); import espn
for ev in ("400277727", "400278111", "400488886"):   # CHI-SAC (empty), a 2013 game with NO/CHI?, SA-MEM 2013-10-30 (good)
    try: s = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={ev}")
    except Exception as e: print(ev, "FAILED", e); continue
    bx = s.get("boxscore", {}); pl = bx.get("players", [])
    print("=====", ev, "boxscore keys:", list(bx.keys()), "| teams in players:", [p["team"].get("abbreviation") for p in pl])
    for tb in pl:
        print("  team", tb["team"].get("abbreviation"), "n statistics groups:", len(tb.get("statistics", [])))
        for st in tb.get("statistics", []):
            print("   names:", st.get("names"), "| athletes:", len(st.get("athletes", [])))
            for a in st.get("athletes", [])[:2]: print("    ", (a.get("athlete") or {}).get("displayName"), "stats:", a.get("stats"), "dnp:", a.get("didNotPlay"), "reason:", a.get("reason"))
    print("  header status:", json.dumps(s.get("header", {}).get("competitions", [{}])[0].get("status", {}))[:200])
