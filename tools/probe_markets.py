"""
One-off probe (run on GitHub, since this needs the open internet): can we get
  (a) DraftKings / FanDuel public odds boosts without logging in, and
  (b) past games' 1st-half / 1st-quarter / team-total lines and quarter scores from Action Network (free backfill)?
Writes research/probes/markets_probe.md with what worked, plus small samples. Reads nothing private and logs in nowhere.

  python tools/probe_markets.py WORKDIR
"""
import os, sys, json, urllib.request, urllib.error
import datetime as dt

W = os.path.abspath(sys.argv[1])
OUT = os.path.join(W, "research", "probes"); os.makedirs(OUT, exist_ok=True)
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
       "Accept": "application/json, text/plain, */*"}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers=HDR)
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read()
            return r.status, b
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500]
    except Exception as e:
        return -1, str(e).encode()[:300]


def boost_hits(text):
    t = text.lower()
    return t.count("boost"), t.count("odds boost"), t.count("profit boost")


lines = [f"# Markets probe — {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC", ""]

# (a) public boosts
lines += ["## (a) Public odds boosts", "", "| Source | HTTP | bytes | 'boost' mentions | note |", "|---|---|---|---|---|"]
BOOST_URLS = {
    "DK nash NBA league (dkusct)": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusct/v1/leagues/42648",
    "DK nash NBA league (dkusnj)": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/42648",
    "DK nash featured/boosts (dkusct)": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusct/v1/leagues/42648/categories/1537",
    "DK nash odds-boosts navigation": "https://sportsbook-nash.draftkings.com/api/sportscontent/navigation/dkusct/v1/nav/leagues/42648",
    "FD CT NBA page": "https://sbapi.ct.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=nba&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York",
    "FD CT boosts page": "https://sbapi.ct.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=boosts&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York",
    "FD NJ promos tab": "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=odds-boosts&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York",
}
for name, url in BOOST_URLS.items():
    code, b = fetch(url)
    txt = b.decode("utf-8", "ignore")
    nb, nob, npb = boost_hits(txt)
    note = ""
    if code == 200 and nb:
        fn = os.path.join(OUT, "boost_sample_" + "".join(c if c.isalnum() else "_" for c in name)[:40] + ".json")
        open(fn, "w").write(txt[:400000]); note = f"sample saved ({os.path.basename(fn)})"
    elif code != 200:
        note = txt[:80].replace("|", "/").replace("\n", " ")
    lines.append(f"| {name} | {code} | {len(b)} | {nb} (odds boost {nob}, profit boost {npb}) | {note} |")

# (b) past period lines + quarter scores from Action Network
lines += ["", "## (b) Past 1H / 1Q / team-total lines (Action Network)", ""]
BOOKS = "15,30,68,69"           # consensus, open, DraftKings, FanDuel
for sport, day, pers in [("nba", "20240115", ["game", "firsthalf", "firstquarter", "secondhalf"]),
                         ("nba", "20220110", ["firsthalf", "firstquarter"]),
                         ("nhl", "20240115", ["game", "firstperiod"]),
                         ("nfl", "20231210", ["firsthalf", "firstquarter"])]:
    for per in pers:
        url = f"https://api.actionnetwork.com/web/v1/scoreboard/{sport}?period={per}&bookIds={BOOKS}&date={day}"
        code, b = fetch(url)
        try: d = json.loads(b)
        except Exception: d = {}
        G = d.get("games", []) if isinstance(d, dict) else []
        n_odds = sum(1 for g in G if g.get("odds"))
        books = sorted({o.get("book_id") for g in G for o in (g.get("odds") or [])})
        ex = {}
        for g in G:
            for o in g.get("odds") or []:
                if o.get("book_id") == 68: ex = {k: o.get(k) for k in ("spread_home", "spread_home_line", "total", "over", "home_total", "away_total", "ml_home", "inserted")}; break
            if ex: break
        status = sorted({g.get("status") for g in G})
        ls = next(((g.get("boxscore") or {}).get("linescore") for g in G if (g.get("boxscore") or {}).get("linescore")), None)
        lines.append(f"- **{sport} {day} {per}**: HTTP {code}, games {len(G)} ({', '.join(map(str, status))}), games with odds {n_odds}, "
                     f"book ids {books}; DK example {json.dumps(ex)}; linescore present: {bool(ls)}")
        if per in ("firsthalf", "firstperiod") and code == 200:
            open(os.path.join(OUT, f"an_{sport}_{day}_{per}.json"), "w").write(json.dumps(d)[:300000])

# v2 scoreboard also carries markets for past dates?
code, b = fetch("https://api.actionnetwork.com/web/v2/scoreboard/nba?bookIds=68,69&date=20240115&periods=event,firsthalf,firstquarter")
try:
    d = json.loads(b); g0 = (d.get("games") or [{}])[0]
    mk = (g0.get("markets") or {}).get("68") or {}
    lines += ["", f"- v2 scoreboard with periods: HTTP {code}, market keys for DK: {list(mk)[:10]}"]
except Exception as e:
    lines += ["", f"- v2 scoreboard with periods: HTTP {code}, unreadable ({e})"]

# ---- round 2 (Nov 4): FanDuel boost pages, depth of the period-line history, NFL by week ----
lines += ["", "## Round 2", ""]
FD = "https://sbapi.ct.sportsbook.fanduel.com/api/content-managed-page?page={p}&customPageId={c}&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"
for p, c in [("HOME", ""), ("CUSTOM", "boost"), ("CUSTOM", "odds-boost"), ("CUSTOM", "profit-boost"), ("CUSTOM", "boosts-hub"),
             ("CUSTOM", "promos"), ("CUSTOM", "nfl"), ("CUSTOM", "nhl"), ("SPORT", "")]:
    code, b = fetch(FD.format(p=p, c=c)); txt = b.decode("utf-8", "ignore"); nb, nob, npb = boost_hits(txt)
    lines.append(f"- FanDuel {p}/{c or '-'}: HTTP {code}, {len(b)} bytes, 'boost' {nb} (odds boost {nob}, profit boost {npb})")
    if code == 200 and nb:
        open(os.path.join(OUT, f"fd_{p}_{c or 'x'}.json"), "w").write(txt[:600000])
for day in ["20221025", "20221215", "20230115", "20230315", "20231101", "20250115", "20260115"]:
    code, b = fetch(f"https://api.actionnetwork.com/web/v1/scoreboard/nba?period=firsthalf&bookIds={BOOKS}&date={day}")
    try: G = json.loads(b).get("games", [])
    except Exception: G = []
    bk = sorted({o.get("book_id") for g in G for o in (g.get("odds") or [])})
    lines.append(f"- NBA 1H {day}: games {len(G)}, book ids with odds {bk}")
for wk in ["14"]:
    code, b = fetch(f"https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=firsthalf&bookIds={BOOKS}&season=2023&week={wk}")
    try: G = json.loads(b).get("games", [])
    except Exception: G = []
    st = sorted({g.get("status") for g in G}); dates = sorted({str(g.get("start_time"))[:10] for g in G})
    bk = sorted({o.get("book_id") for g in G for o in (g.get("odds") or [])})
    lines.append(f"- NFL 1H season 2023 week {wk}: HTTP {code}, games {len(G)} {st}, dates {dates[:3]}, books {bk}")

open(os.path.join(OUT, "markets_probe.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
