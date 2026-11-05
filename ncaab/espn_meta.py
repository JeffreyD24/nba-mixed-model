"""ESPN men's college basketball scoreboards for every date (Nov 5, 2026): per game the pre-game AP rank (curatedRank, 99 = unranked),
conference id, neutral site, conference game and final score, for matching to the SBR and Action Network game files.
  python ncaab/espn_meta.py WORKDIR --from 2007-11-01 --to 2026-11-04 --out FILE"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r: return json.loads(r.read())
        except Exception: time.sleep(2 + 3 * i)
    return {}
def day(d):
    js = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={d:%Y%m%d}&groups=50&limit=500")
    out = []
    for e in js.get("events", []):
        c = e["competitions"][0]; t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" not in t or "away" not in t: continue
        r = dict(date=str(d.date()), espn_id=e["id"], neutral=bool(c.get("neutralSite")), conf_game=bool(c.get("conferenceCompetition")),
                 tournament=(c.get("type") or {}).get("abbreviation"), notes=" ".join(n.get("headline", "") for n in c.get("notes", []))[:80])
        for s in ("home", "away"):
            x = t[s]; tm = x["team"]
            r.update({f"{s}_espn_team": tm.get("id"), f"{s}_name": tm.get("displayName"), f"{s}_loc": tm.get("location"),
                      f"{s}_conf_id": tm.get("conferenceId"), f"{s}_rank": (x.get("curatedRank") or {}).get("current", 99),
                      f"{s}_pts": x.get("score")})
        out.append(r)
    return out
if __name__ == "__main__":
    days = [d for d in pd.date_range(ARG("--from"), ARG("--to")) if d.month in (11, 12, 1, 2, 3, 4)]
    rows = []
    with ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(day, days)):
            rows += r
            if i % 200 == 0: print(i, len(days), len(rows), flush=True)
    pd.DataFrame(rows).to_csv(ARG("--out"), index=False); print("saved", len(rows))
