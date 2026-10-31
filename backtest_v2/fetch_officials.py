"""
Referee crews for every game in games_v2.csv, from ESPN's public game summaries.
Output: officials.csv  (date, home, away, espn_id, officials = 'A|B|C')
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

W = "/home/claude/work/"
SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}&limit=50"
SUM = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={}"


def get(u, tries=4):
    for k in range(tries):
        try:
            return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception:
            time.sleep(1 + 2 * k)
    return None


g = pd.read_csv(W + "games_v2.csv", parse_dates=["date"])
dates = sorted(g.date.dt.strftime("%Y%m%d").unique())


def day(d):
    sb = get(SB.format(d))
    out = []
    for ev in (sb or {}).get("events", []):
        c = ev["competitions"][0]["competitors"]
        h = next(x for x in c if x["homeAway"] == "home")["team"]["abbreviation"].lower()
        a = next(x for x in c if x["homeAway"] == "away")["team"]["abbreviation"].lower()
        out.append((d, h, a, ev["id"]))
    return out


with ThreadPoolExecutor(12) as ex:
    evs = [r for rows in ex.map(day, dates) for r in rows]
E = pd.DataFrame(evs, columns=["d", "home", "away", "espn_id"])
E["date"] = pd.to_datetime(E.d)
m = g[["date", "home", "away"]].merge(E, on=["date", "home", "away"], how="left")
print("games", len(g), "matched to ESPN events", m.espn_id.notna().sum(), flush=True)


def offs(eid):
    s = get(SUM.format(eid))
    o = ((s or {}).get("gameInfo") or {}).get("officials") or []
    return "|".join(x.get("fullName") or x.get("displayName") for x in sorted(o, key=lambda x: x.get("order", 9)))


with ThreadPoolExecutor(12) as ex:
    m["officials"] = list(ex.map(lambda e: offs(e) if isinstance(e, str) else "", m.espn_id))
m.to_csv(W + "officials.csv", index=False)
n = (m.officials.str.count(r"\|") >= 2)
print("games with a full crew:", int(n.sum()), "of", len(m))
print(m.assign(ok=n).groupby(m.date.dt.year).ok.mean().round(3).to_dict())
