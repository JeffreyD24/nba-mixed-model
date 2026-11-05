"""
One-off probe for the player-props backtest (runs on GitHub; the Odds API key stays in the secret and is never printed):
  1) The Odds API: credits left (free), and ONE historical player-prop call for a past NBA game (cost ~40 credits) to see which
     books/markets come back and how far before tip the snapshots go.
  2) Action Network: do past games' player props come back for a past date?
  3) ESPN: does a past game's summary carry full player box stats (points, rebounds, assists, threes)?
Writes research/probes/props_probe.md.
  python tools/probe_props.py WORKDIR
"""
import os, sys, json, urllib.request, urllib.parse, urllib.error
import datetime as dt

W = os.path.abspath(sys.argv[1])
OUT = os.path.join(W, "research", "probes"); os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get("ODDS_API_KEY", "")
HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
L = [f"# Props probe — {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC", ""]


def get(url, hide=True):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30) as r:
            return r.status, json.loads(r.read()), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", "ignore"), dict(e.headers)
    except Exception as e:
        return -1, str(e)[:200], {}


# 1) The Odds API
API = "https://api.the-odds-api.com/v4"
if KEY:
    c, d, h = get(f"{API}/sports?apiKey={KEY}")
    L += ["## The Odds API", f"- credits left: {h.get('x-requests-remaining')}, used: {h.get('x-requests-used')}"]
    for when in ("2024-01-15T22:00:00Z", "2023-11-01T22:00:00Z"):
        c, ev, h = get(f"{API}/historical/sports/basketball_nba/events?apiKey={KEY}&date={when}")
        evs = (ev or {}).get("data", []) if isinstance(ev, dict) else []
        L.append(f"- historical events at {when}: HTTP {c}, {len(evs)} events, cost {h.get('x-requests-last')}")
        if evs:
            e0 = evs[0]
            mk = "player_points,player_rebounds,player_assists,player_threes"
            url = (f"{API}/historical/sports/basketball_nba/events/{e0['id']}/odds?apiKey={KEY}&regions=us&markets={mk}"
                   f"&oddsFormat=american&date={when}&bookmakers=draftkings,fanduel,pinnacle,betmgm,williamhill_us,betrivers")
            c, od, h = get(url)
            data = od.get("data", {}) if isinstance(od, dict) else {}
            bks = data.get("bookmakers", []) if isinstance(data, dict) else []
            summ = {b["key"]: {m["key"]: len(m.get("outcomes", [])) for m in b.get("markets", [])} for b in bks}
            L.append(f"  - one game ({e0.get('away_team')} @ {e0.get('home_team')}, tip {e0.get('commence_time')}): HTTP {c}, "
                     f"cost {h.get('x-requests-last')}, snapshot {od.get('timestamp') if isinstance(od, dict) else ''}, "
                     f"prev {od.get('previous_timestamp') if isinstance(od, dict) else ''}")
            L.append(f"  - outcomes per book/market: {json.dumps(summ)}")
            if bks:
                ex = bks[0]["markets"][0]["outcomes"][:4]
                L.append(f"  - example: {json.dumps(ex)}")
                open(os.path.join(OUT, "oddsapi_props_sample.json"), "w").write(json.dumps(od)[:200000])
            break
    c, d, h = get(f"{API}/sports?apiKey={KEY}")
    L.append(f"- credits left after probe: {h.get('x-requests-remaining')}")
else:
    L += ["## The Odds API", "- no key in this run"]

# 2) Action Network past props
L += ["", "## Action Network past props"]
for url in ["https://api.actionnetwork.com/web/v1/leagues/4/props/core_bet_type_27_points?bookIds=68,69&date=20240115",
            "https://api.actionnetwork.com/web/v2/scoreboard/nba/props?bookIds=68,69&date=20240115",
            "https://api.actionnetwork.com/web/v1/scoreboard/nba?period=game&bookIds=68,69&date=20240115&include=props"]:
    c, d, h = get(url)
    s = json.dumps(d)[:300] if not isinstance(d, str) else d[:200]
    L.append(f"- {url.split('?')[0].split('/web/')[1]}: HTTP {c}; {s.count('player')} 'player' in first 300 chars; {s[:160]!r}")

# 3) ESPN full box stats
L += ["", "## ESPN past box score"]
c, d, h = get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401585109")
try:
    st = d["boxscore"]["players"][0]["statistics"][0]
    L.append(f"- HTTP {c}; stat names: {st['names']}; first player: {st['athletes'][0]['athlete']['displayName']} {st['athletes'][0]['stats']}")
except Exception as e:
    L.append(f"- HTTP {c}; could not read ({e})")

open(os.path.join(OUT, "props_probe.md"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
