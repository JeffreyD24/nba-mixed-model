"""
Polymarket US tracker: prices, model edges and paper trades. It never places a trade.

  python polymarket.py WORKDIR              # one check: run by alert_loop.sh right after alert.py
  python polymarket.py WORKDIR --grade      # morning run: grade finished paper trades, rebuild the report
  python polymarket.py WORKDIR --residuals  # NBA/NFL: rebuild data/poly_residuals.json from the backtests
  python polymarket.py WORKDIR --force      # check even when POLYMARKET_OFF is set

The same file runs in the NHL, NBA and NFL repos; it works out which sport it is in from the model file it finds.

Each check:
  1. pulls today's and upcoming games for this league from Polymarket US's public data API (no account or key needed),
  2. matches them to the games in state/model_YYYY-MM-DD.json and reads the model's latest number from
     research/model/YYYY-MM-DD.csv (the live number alert.py just wrote, with goalie or injury news included),
  3. saves Polymarket's best bid, best offer and depth for every moneyline, spread and total contract to
     research/polymarket/YYYY-MM-DD.csv (a row only when something changed),
  4. turns the model's number into a probability for each contract and logs paper trades to state/poly_paper.csv:
       taker: buy at the best offer (plus Polymarket's taker fee) the first time expected value >= THRESHOLD
       maker: post a limit bid at the highest price that still has THRESHOLD expected value; it counts as filled
              if the best offer later drops to that price before the game starts (approximate: ignores queue position)
     each with DraftKings' price on the same bet at that moment, from research/odds/.

Probabilities:
  NHL  the repo's own Poisson model (nhl_mixed_model.market_probs / over_prob) on the live expected goals, both models.
  NBA, NFL  predicted margin or total + the model's backtest misses (data/poly_residuals.json, centred on zero so a
       model total equal to the line is a 50/50 over), counted directly: P(home covers -5.5) = share of past misses
       that would have put the home team ahead by 6+.

Settings below. Polymarket US's API: https://docs.polymarket.us (public base URL https://gateway.polymarket.us).
"""
import os, sys, re, json, math, glob, unicodedata, urllib.request, urllib.parse, urllib.error, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

# ----------------------------------------------------------------------------------------------- settings
BASE = "https://gateway.polymarket.us"
TAKER_FEE_RATE = 0.05        # sports taker fee per contract = rate x price x (1 - price); about 1.25 cents at 50 cents
MAKER_FEE_RATE = 0.0         # resting (maker) orders pay nothing
THRESHOLD = {"nhl": 0.06, "nba": 0.05, "nfl": 0.05}      # expected value per dollar needed for a paper trade
PAPER_MARKETS = {"nhl": ("moneyline", "spread"),         # NHL totals had no edge in the backtests (README), so they
                 "nba": ("moneyline", "spread", "total"),  # are snapshotted but not paper-traded
                 "nfl": ("moneyline", "spread", "total")}
MAKER = True                 # also simulate resting limit orders
MIN_DEPTH = 20               # contracts needed at the price (a stray 1-contract offer is not a real price)
BOOK_EVERY_MIN = 30         # save the full order book at least this often per contract (and whenever the best price or size changes)
BOOK_RANGE = 0.10           # keep price levels within this many dollars of the best price
BOOK_LEVELS = 15            # and at most this many per side
HOURS_BEFORE = 100           # NHL and NBA early runs cover games up to 4 days out (state/early/); the NFL model files already cover a week (170 h)            # look at games starting within this many hours
TIMEOUT = 12                 # seconds per request
WORKERS = 8                  # parallel price requests
ET = ZoneInfo("America/New_York")
MARKET_NAME = {"nhl": {"spread": "puck line"}, "nba": {}, "nfl": {}}
TOTAL_RANGE = {"nhl": (3, 12), "nba": (150, 300), "nfl": (20, 80)}      # anything outside is a period or team total
SPREAD_MAX = {"nhl": 4, "nba": 30, "nfl": 30}

W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.getcwd()
sys.path.insert(0, W)
STATE, RESEARCH = os.path.join(W, "state"), os.path.join(W, "research")
PM_DIR = os.path.join(RESEARCH, "polymarket")
PAPER = os.path.join(STATE, "poly_paper.csv")
LAST = os.path.join(STATE, "poly_last.json")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
TODAY = NOW.normalize()

if os.path.exists(os.path.join(W, "nhl_mixed_model.py")): SPORT = "nhl"
elif os.path.exists(os.path.join(W, "nfl_mixed_model.py")): SPORT = "nfl"
elif os.path.exists(os.path.join(W, "nba_mixed_model.py")): SPORT = "nba"
else: SPORT = os.environ.get("SPORT", "nba").lower()

# ----------------------------------------------------------------------------------------------- team names
# repo code -> names Polymarket might use (full name, nickname, other abbreviations). Cities shared by two teams are left out.
TEAMS = {
    "nba": {
        "atl": "Atlanta Hawks|Hawks|ATL", "bkn": "Brooklyn Nets|Nets|BKN|BRK|BK", "bos": "Boston Celtics|Celtics|BOS",
        "cha": "Charlotte Hornets|Hornets|CHA|CHO", "chi": "Chicago Bulls|Bulls|CHI", "cle": "Cleveland Cavaliers|Cavaliers|Cavs|CLE",
        "dal": "Dallas Mavericks|Mavericks|Mavs|DAL", "den": "Denver Nuggets|Nuggets|DEN", "det": "Detroit Pistons|Pistons|DET",
        "gs": "Golden State Warriors|Warriors|GSW|GS|Golden State", "hou": "Houston Rockets|Rockets|HOU",
        "ind": "Indiana Pacers|Pacers|IND", "lac": "Los Angeles Clippers|LA Clippers|Clippers|LAC",
        "lal": "Los Angeles Lakers|LA Lakers|Lakers|LAL", "mem": "Memphis Grizzlies|Grizzlies|MEM",
        "mia": "Miami Heat|Heat|MIA", "mil": "Milwaukee Bucks|Bucks|MIL", "min": "Minnesota Timberwolves|Timberwolves|Wolves|MIN",
        "no": "New Orleans Pelicans|Pelicans|NOP|NO|New Orleans", "ny": "New York Knicks|Knicks|NYK|NY",
        "okc": "Oklahoma City Thunder|Thunder|OKC|Oklahoma City", "orl": "Orlando Magic|Magic|ORL",
        "phi": "Philadelphia 76ers|76ers|Sixers|PHI", "phx": "Phoenix Suns|Suns|PHX|PHO", "por": "Portland Trail Blazers|Trail Blazers|Blazers|POR",
        "sac": "Sacramento Kings|Kings|SAC", "sa": "San Antonio Spurs|Spurs|SAS|SA|San Antonio", "tor": "Toronto Raptors|Raptors|TOR",
        "utah": "Utah Jazz|Jazz|UTA|UTAH", "wsh": "Washington Wizards|Wizards|WAS|WSH"},
    "nhl": {
        "ana": "Anaheim Ducks|Ducks|ANA", "bos": "Boston Bruins|Bruins|BOS", "buf": "Buffalo Sabres|Sabres|BUF",
        "car": "Carolina Hurricanes|Hurricanes|Canes|CAR", "cbj": "Columbus Blue Jackets|Blue Jackets|CBJ|CLB",
        "cgy": "Calgary Flames|Flames|CGY|CAL", "chi": "Chicago Blackhawks|Blackhawks|CHI", "col": "Colorado Avalanche|Avalanche|COL",
        "dal": "Dallas Stars|Stars|DAL", "det": "Detroit Red Wings|Red Wings|DET", "edm": "Edmonton Oilers|Oilers|EDM",
        "fla": "Florida Panthers|Panthers|FLA", "la": "Los Angeles Kings|LA Kings|Kings|LAK|LA", "min": "Minnesota Wild|Wild|MIN",
        "mtl": "Montreal Canadiens|Montréal Canadiens|Canadiens|MTL|MON", "nj": "New Jersey Devils|Devils|NJD|NJ",
        "nsh": "Nashville Predators|Predators|Preds|NSH|NAS", "nyi": "New York Islanders|Islanders|NYI",
        "nyr": "New York Rangers|Rangers|NYR", "ott": "Ottawa Senators|Senators|OTT", "phi": "Philadelphia Flyers|Flyers|PHI",
        "pit": "Pittsburgh Penguins|Penguins|PIT", "sea": "Seattle Kraken|Kraken|SEA", "sj": "San Jose Sharks|Sharks|SJS|SJ",
        "stl": "St. Louis Blues|St Louis Blues|Blues|STL", "tb": "Tampa Bay Lightning|Lightning|TBL|TB",
        "tor": "Toronto Maple Leafs|Maple Leafs|Leafs|TOR", "uta": "Utah Mammoth|Mammoth|Utah Hockey Club|Utah HC|UTA|UTAH",
        "van": "Vancouver Canucks|Canucks|VAN", "vgk": "Vegas Golden Knights|Golden Knights|VGK|VEG",
        "wpg": "Winnipeg Jets|Jets|WPG|WIN", "wsh": "Washington Capitals|Capitals|Caps|WSH|WAS"},
    "nfl": {
        "ari": "Arizona Cardinals|Cardinals|ARI|ARZ", "atl": "Atlanta Falcons|Falcons|ATL", "bal": "Baltimore Ravens|Ravens|BAL",
        "buf": "Buffalo Bills|Bills|BUF", "car": "Carolina Panthers|Panthers|CAR", "chi": "Chicago Bears|Bears|CHI",
        "cin": "Cincinnati Bengals|Bengals|CIN", "cle": "Cleveland Browns|Browns|CLE", "dal": "Dallas Cowboys|Cowboys|DAL",
        "den": "Denver Broncos|Broncos|DEN", "det": "Detroit Lions|Lions|DET", "gb": "Green Bay Packers|Packers|GB|GNB|Green Bay",
        "hou": "Houston Texans|Texans|HOU", "ind": "Indianapolis Colts|Colts|IND", "jax": "Jacksonville Jaguars|Jaguars|Jags|JAX|JAC",
        "kc": "Kansas City Chiefs|Chiefs|KC|KAN|Kansas City", "lac": "Los Angeles Chargers|LA Chargers|Chargers|LAC",
        "lar": "Los Angeles Rams|LA Rams|Rams|LAR|LA", "lv": "Las Vegas Raiders|Raiders|LV|LVR|Las Vegas",
        "mia": "Miami Dolphins|Dolphins|MIA", "min": "Minnesota Vikings|Vikings|MIN", "ne": "New England Patriots|Patriots|Pats|NE|NWE|New England",
        "no": "New Orleans Saints|Saints|NO|NOR|New Orleans", "nyg": "New York Giants|Giants|NYG", "nyj": "New York Jets|Jets|NYJ",
        "phi": "Philadelphia Eagles|Eagles|PHI", "pit": "Pittsburgh Steelers|Steelers|PIT", "sea": "Seattle Seahawks|Seahawks|SEA",
        "sf": "San Francisco 49ers|49ers|Niners|SF|SFO|San Francisco", "tb": "Tampa Bay Buccaneers|Buccaneers|Bucs|TB|TAM|Tampa Bay",
        "ten": "Tennessee Titans|Titans|TEN", "wsh": "Washington Commanders|Commanders|WAS|WSH"},
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


ALIASES = {}                                     # normalized alias -> code (aliases used by two teams are dropped)
for _code, _names in TEAMS[SPORT].items():
    for _a in _names.split("|"):
        k = norm(_a)
        ALIASES[k] = None if (k in ALIASES and ALIASES[k] != _code) else _code
ALIASES = {k: v for k, v in ALIASES.items() if v}
_BY_LEN = sorted((a for a in ALIASES if len(a) > 3), key=len, reverse=True)   # long names searched inside text


def team_code(*texts):
    """repo team code for a team name or abbreviation (exact match first, then the longest name found inside the text)"""
    for t in texts:
        k = norm(t)
        if k in ALIASES: return ALIASES[k]
    for t in texts:
        k = f" {norm(t)} "
        for a in _BY_LEN:
            if f" {a} " in k: return ALIASES[a]
    return None


# ----------------------------------------------------------------------------------------------- small helpers
def get_json(path, params=None):
    url = BASE + path + (("?" + urllib.parse.urlencode(params, doseq=True)) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": f"{SPORT}-mixed-model research tracker", "Accept": "application/json"})
    last = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (400, 404): raise
            last = e
        except Exception as e:                       # timeouts, resets: one retry
            last = e
    raise last


def amount(x):
    """Polymarket US prices come as {"value": "0.43", "currency": "USD"}, a string or a number"""
    if isinstance(x, dict): x = x.get("value", x.get("amount"))
    try: return float(x)
    except (TypeError, ValueError): return float("nan")


def num(x):
    try: return float(x)
    except (TypeError, ValueError): return float("nan")


def to_et(s):
    """ISO time (UTC unless it says otherwise) -> naive Eastern time"""
    if not s: return None
    try:
        t = pd.Timestamp(s)
        if t.tzinfo is None: t = t.tz_localize("UTC")
        return t.tz_convert(ET).tz_localize(None)
    except Exception:
        return None


def taker_fee(p): return TAKER_FEE_RATE * p * (1 - p)
def maker_fee(p): return MAKER_FEE_RATE * p * (1 - p)


def american(price):
    """contract price -> American odds (what the same bet would look like at a sportsbook, before fees)"""
    if not (0 < price < 1): return float("nan")
    return -100 * price / (1 - price) if price >= 0.5 else 100 * (1 - price) / price


def dec(o):
    o = num(o)
    if math.isnan(o) or o == 0: return float("nan")
    return 1 + (o / 100 if o > 0 else 100 / -o)


def fair_pair(a, b):
    """no-vig chance of side a from the two American prices"""
    da, db = dec(a), dec(b)
    if math.isnan(da) or math.isnan(db): return float("nan")
    return (1 / da) / (1 / da + 1 / db)


def load_last():
    try: return json.load(open(LAST))
    except Exception: return {"sig": {}, "unmatched": [], "samples": ""}


def append_csv(path, rows, cols=None):
    if not rows: return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(rows)
    if cols: df = df.reindex(columns=cols)
    df.to_csv(path, mode="a", header=not os.path.exists(path), index=False)


# ----------------------------------------------------------------------------------------------- games and model numbers
def latest_rows(day, keys):
    p = os.path.join(RESEARCH, "model", f"{day}.csv")
    if not os.path.exists(p): return {}
    try: R = pd.read_csv(p, dtype={"game_id": str})
    except Exception: return {}
    R = R.sort_values("seen_at_et").groupby(keys, as_index=False).last()
    return {tuple(str(r[k]) for k in keys): r for r in R.to_dict("records")}


def load_games():
    """games for today and later from the saved model files, each with a function giving P(win), P(push) for any outcome"""
    files = sorted(f for f in os.listdir(STATE) if re.fullmatch(r"model_\d{4}-\d{2}-\d{2}\.json", f) and f[6:16] >= str(TODAY.date()))
    games = {}
    early = []                      # NHL: models made 2-4 days ahead by early.yml into state/early/, used until the regular model file for that day exists
    if SPORT in ("nhl", "nba") and os.path.isdir(os.path.join(STATE, "early")):
        main_days = {f[6:16] for f in files}
        early = [f for f in sorted(os.listdir(os.path.join(STATE, "early")))
                 if re.fullmatch(r"model_\d{4}-\d{2}-\d{2}\.json", f) and f[6:16] >= str(TODAY.date()) and f[6:16] not in main_days]
    for is_early, f in [(True, x) for x in early] + [(False, x) for x in files]:
        M = json.load(open(os.path.join(STATE, "early" if is_early else "", f)))
        day = M["date"]
        tag = "@early" if is_early else ""
        if SPORT == "nhl":
            import nhl_mixed_model as nm
            if "models" not in M: M = dict(date=day, active="goals", models={"goals": M})
            live = {} if is_early else latest_rows(day, ["model", "game_id"])
            order = [k for k in ("xg", "goals") if k in M["models"]] + [k for k in M["models"] if k not in ("xg", "goals")]
            for name in order:
                OM = M["models"][name]
                for g in OM["games"]:
                    gid = str(g["game_id"]); r = live.get((name, gid))
                    if r is not None and not pd.isna(r.get("lam_home")):
                        lh, la = float(r["lam_home"]), float(r["lam_away"])
                        known = all("not announced" not in str(r.get(c, "")) for c in ("home_goalie", "away_goalie"))
                    elif "morning_lam_home" in g:
                        lh, la, known = float(g["morning_lam_home"]), float(g["morning_lam_away"]), False
                    else:
                        continue
                    cal = OM["cal"]["pretip" if known else "open"]
                    G = games.setdefault(gid, dict(game_id=gid, date=day, home=g["home"], away=g["away"], tip_et=pd.Timestamp(g["tip_et"]), models={}))
                    G["models"][name + tag] = nhl_prob(nm, lh, la, OM["h_ot"], cal)
        else:
            res = residuals()
            live = {} if is_early else latest_rows(day, ["game_id"])
            for g in M["games"]:
                gid = str(g["game_id"]); r = live.get((gid,))
                mm = num(r["model_margin"]) if r is not None else num(g.get("morning_margin"))
                mt = num(r["model_total"]) if r is not None else num(g.get("morning_total"))
                if math.isnan(mm) and math.isnan(mt): continue
                G = games.setdefault(gid, dict(game_id=gid, date=day, home=g["home"], away=g["away"], tip_et=pd.Timestamp(g["tip_et"]), models={}))
                G["models"]["model" + tag] = points_prob(mm, mt, res)
    return games


def nhl_prob(nm, lh, la, h_ot, cal):
    mp = nm.market_probs(np.array([lh]), np.array([la]), h_ot, cal)
    ph, hb2, ab2 = float(mp["home_win"][0]), float(mp["home_by2"][0]), float(mp["away_by2"][0])
    cache = {}

    def prob(market, side, line):
        if market == "moneyline": return (ph if side == "home" else 1 - ph), 0.0
        if market == "spread":
            hl = line if side == "home" else -line          # the home team's line
            if abs(abs(hl) - 1.5) > 1e-9: return None        # only the +-1.5 puck line is modeled
            p_home_cover = hb2 if hl < 0 else 1 - ab2
            return (p_home_cover if side == "home" else 1 - p_home_cover), 0.0
        if market == "total":
            if line not in cache:
                po, pu, pp = nm.over_prob(np.array([lh]), np.array([la]), np.array([line]), h_ot, cal)
                cache[line] = (float(po[0]), float(pu[0]), float(pp[0]))
            po, pu, pp = cache[line]
            return (po if side == "over" else pu), pp
        return None
    return prob


def residuals():
    p = os.path.join(W, "data", "poly_residuals.json")
    if not os.path.exists(p): build_residuals()
    R = json.load(open(p))
    return np.sort(np.array(R["margin"], float)), np.sort(np.array(R["total"], float))


def points_prob(mm, mt, res):
    rm, rt = res

    def share_above(r, x):           # share of misses r with value > x, and exactly x (a push)
        hi = len(r) - np.searchsorted(r, x, side="right"); eq = np.searchsorted(r, x, side="right") - np.searchsorted(r, x, side="left")
        return hi / len(r), eq / len(r)

    def prob(market, side, line):
        if market == "moneyline":
            if math.isnan(mm): return None
            p, _ = share_above(rm, -mm)                # home wins when margin + miss > 0
            return (p if side == "home" else 1 - p), 0.0
        if market == "spread":
            if math.isnan(mm): return None
            hl = line if side == "home" else -line       # home covers when margin + miss + home line > 0
            p, push = share_above(rm, -mm - hl)
            return (p if side == "home" else 1 - p - push), push
        if market == "total":
            if math.isnan(mt): return None
            p, push = share_above(rt, line - mt)
            return (p if side == "over" else 1 - p - push), push
        return None
    return prob


def build_residuals():
    """NBA: Model 1 (the live model) with the last report before tip, 2024-25 and 2025-26.  NFL: the last four backtest seasons."""
    if SPORT == "nba":
        d = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(W, "research", "model_comparison", "predictions_*.csv")))])
        m, t = d.home_pts - d.away_pts, d.home_pts + d.away_pts
        rm, rt = (m - d.m1_margin_close_report).dropna(), (t - d.m1_total_close_report).dropna()
        src = "research/model_comparison/predictions_*.csv, Model 1, last report before tip"
    elif SPORT == "nfl":
        files = sorted(glob.glob(os.path.join(W, "backtests", "predictions_20*.csv")))[-4:]
        d = pd.concat([pd.read_csv(f) for f in files])
        rm, rt = (d.margin - d.pred_margin).dropna(), (d.tot - d.pred_total).dropna()
        src = ", ".join("backtests/" + os.path.basename(f) for f in files)
    else:
        raise SystemExit("The NHL tracker uses its own Poisson model, not residuals.")
    out = dict(source=src, made=str(NOW)[:16], n_margin=len(rm), n_total=len(rt),
               margin_mean_removed=round(float(rm.mean()), 3), total_mean_removed=round(float(rt.mean()), 3),
               margin_sd=round(float(rm.std()), 3), total_sd=round(float(rt.std()), 3),
               margin=[round(float(x), 2) for x in np.sort(rm - rm.mean())],
               total=[round(float(x), 2) for x in np.sort(rt - rt.mean())])
    os.makedirs(os.path.join(W, "data"), exist_ok=True)
    json.dump(out, open(os.path.join(W, "data", "poly_residuals.json"), "w"))
    print(f"Saved data/poly_residuals.json: {len(rm)} margin misses (sd {out['margin_sd']}), {len(rt)} total misses (sd {out['total_sd']}).")


# ----------------------------------------------------------------------------------------------- Polymarket
LEAGUE_RE = re.compile(rf"(^|[^a-z]){SPORT}([^a-z]|$)")


def league_text(ev):
    bits = [ev.get("seriesSlug"), ev.get("slug"), ev.get("title"), ev.get("category"), ev.get("subcategory")]
    for t in (ev.get("tags") or []) + [ev.get("primaryTag") or {}]:
        if isinstance(t, dict):
            bits += [t.get("slug"), t.get("label")]
            for k in ("league", "sport"):
                v = t.get(k)
                bits += [v.get("slug"), v.get("name"), v.get("label"), v.get("abbreviation")] if isinstance(v, dict) else [v]
    return " ".join(str(b) for b in bits if b).lower()


def fetch_events(t0, t1):
    """this league's sports events starting between t0 and t1 (Eastern)"""
    utc = lambda t: pd.Timestamp(t).tz_localize(ET).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    base = dict(active="true", categories="sports", limit=100)
    params = dict(base, startTimeMin=utc(t0), startTimeMax=utc(t1))
    out, offset = [], 0
    while offset < 3000:
        try:
            r = get_json("/v1/events", dict(params, offset=offset))
        except urllib.error.HTTPError as e:
            if e.code == 400 and "startTimeMin" in params:      # date filter not accepted: filter here instead
                params = dict(base); continue
            raise
        evs = r.get("events", r.get("data", [])) if isinstance(r, dict) else r
        if not evs: break
        out += evs
        if len(evs) < params["limit"]: break
        offset += len(evs)
    keep = []
    for ev in out:
        if not LEAGUE_RE.search(league_text(ev)): continue
        st = to_et(ev.get("startTime") or ev.get("gameStartTime") or ev.get("startDate") or ev.get("eventDate"))
        if st is not None and not (t0 - pd.Timedelta(hours=6) <= st <= t1): continue
        keep.append(ev)
    return keep


def event_markets(ev):
    """the event's markets, fetched by slug when the listing left them out"""
    mk = ev.get("markets")
    if mk: return mk
    try:
        return (get_json(f"/v1/events/slug/{ev['slug']}").get("event") or {}).get("markets") or []
    except Exception:
        return []


def event_teams(ev):
    """{Polymarket team id: repo code} and the set of codes for the event"""
    ids, codes = {}, set()
    for t in (ev.get("teams") or ev.get("participants") or []):
        if not isinstance(t, dict): continue
        c = team_code(t.get("name"), t.get("abbreviation"), t.get("alias"), t.get("displayName"))
        if c:
            codes.add(c)
            for k in ("id", "teamId", "participantId"):
                if t.get(k) is not None: ids[str(t[k])] = c
    if len(codes) < 2:                                   # fall back to the title: "Lakers vs. Celtics", "Bruins @ Rangers"
        parts = re.split(r"\s+(?:vs\.?|v\.?|@|at)\s+", str(ev.get("title", "")), flags=re.I)
        codes |= {c for c in (team_code(p) for p in parts) if c}
    return ids, codes


NUM_SIGNED = re.compile(r"(?<![\w.])([+-]\d+(?:\.\d+)?)")
NUM_ANY = re.compile(r"(\d+(?:\.\d+)?)")


def parse_market(mk, ids, game):
    """the long and short outcomes of one contract, or (None, reason)"""
    kind = str(mk.get("sportsMarketTypeV2") or mk.get("sportsMarketType") or "").upper()
    market = "moneyline" if "MONEYLINE" in kind else "spread" if "SPREAD" in kind else "total" if "TOTAL" in kind else None
    if market is None: return None, f"skipped type {kind or 'unknown'}"
    sides = [s for s in (mk.get("marketSides") or []) if isinstance(s, dict)]
    if not sides: return None, "no market sides"
    long = next((s for s in sides if s.get("long") is True), sides[0])
    desc = str(long.get("description") or "")
    q = str(mk.get("question") or mk.get("title") or "")
    home, away = game["home"], game["away"]
    src = ""
    if market in ("moneyline", "spread"):
        team = ids.get(str(long.get("teamId"))) or ids.get(str(long.get("participantId"))) or team_code(desc)
        if team not in (home, away): return None, f"long side team not found ({desc or q})"
        side, other = ("home", "away") if team == home else ("away", "home")
        if market == "moneyline":
            return dict(market=market, long=(side, float("nan")), short=(other, float("nan")), src="team"), None
        m = NUM_SIGNED.search(desc)
        if m: line, src = float(m.group(1)), "side description"
        else:
            line, src = num(mk.get("line")), "market line"
            if math.isnan(line): return None, "spread without a line"
        if not 0 < abs(line) <= SPREAD_MAX[SPORT]: return None, f"spread line {line} outside +-{SPREAD_MAX[SPORT]}"
        return dict(market=market, long=(side, line), short=(other, -line), src=src), None
    low = f" {desc.lower()} "
    if " under " in low or low.strip().startswith("under"): side, other, src = "under", "over", "side description"
    elif " over " in low or low.strip().startswith("over"): side, other, src = "over", "under", "side description"
    else: side, other, src = "over", "under", "assumed long = over"
    line = num(mk.get("line"))
    if math.isnan(line):
        m = NUM_ANY.search(desc) or NUM_ANY.search(q)
        line = float(m.group(1)) if m else float("nan")
    lo, hi = TOTAL_RANGE[SPORT]
    if math.isnan(line) or not lo < line < hi: return None, f"total line {line} outside {lo}-{hi} (period or team total?)"
    return dict(market=market, long=(side, line), short=(other, line), src=src), None


def bbo(slug):
    try:
        r = get_json(f"/v1/markets/{urllib.parse.quote(slug, safe='')}/bbo")
        d = r.get("marketData", r) if isinstance(r, dict) else {}
        return dict(bid=amount(d.get("bestBid")), ask=amount(d.get("bestAsk")), bid_depth=num(d.get("bidDepth")),
                    ask_depth=num(d.get("askDepth")), last=amount(d.get("lastTradePx")), traded=num(d.get("sharesTraded")),
                    oi=num(d.get("openInterest")), raw=r)
    except Exception as e:
        return dict(error=f"{type(e).__name__}")


def _levels(lst):
    out = []
    for x in lst or []:
        px, q = amount(x.get("px")), num(x.get("qty"))
        if not math.isnan(px) and not math.isnan(q) and q > 0: out.append((px, q))
    return out


def book(slug):
    """Every price level on both sides: bids (best first) and offers (best first), as (price, contracts)."""
    try:
        r = get_json(f"/v1/markets/{urllib.parse.quote(slug, safe='')}/book")
        d = r.get("marketData", r) if isinstance(r, dict) else {}
        st = d.get("stats") or {}
        return dict(bids=sorted(_levels(d.get("bids")), key=lambda t: -t[0]), offers=sorted(_levels(d.get("offers")), key=lambda t: t[0]), raw=r,
                    open_px=amount(st.get("openPx")), opened=st.get("openSetTime"))
    except Exception as e:
        return dict(error=f"{type(e).__name__}")


def walk(lv, n):
    """Average price paid to buy n contracts by walking the levels (best first); NaN if the book is not that deep."""
    got = cost = 0.0
    for px, q in lv:
        t = min(q, n - got); got += t; cost += t * px
        if got >= n - 1e-9: return cost / n
    return np.nan


def within(lv, c):
    """Contracts available within c dollars of the best price."""
    return sum(q for px, q in lv if abs(px - lv[0][0]) <= c + 1e-9) if lv else 0.0


def book_row(bk):
    bids, offers = bk["bids"], bk["offers"]
    short = [(round(1 - px, 4), q) for px, q in bids]            # buying "short" = selling long: you pay 1 - bid
    keep = lambda lv: "|".join([f"{px:g}:{q:.0f}" for px, q in lv if abs(px - lv[0][0]) <= BOOK_RANGE + 1e-9][:BOOK_LEVELS]) if lv else ""
    row = dict(bids=keep(bids), offers=keep(offers), open_px=bk.get("open_px"))
    try: row["opened_at_et"] = str(to_et(bk.get("opened")))[:16] if bk.get("opened") else ""     # when trading in this contract began
    except Exception: row["opened_at_et"] = ""
    for tag, lv in (("long", offers), ("short", short)):
        for c in (0.01, 0.03, 0.05): row[f"{tag}_within_{int(c * 100)}c"] = round(within(lv, c))
        for n in (100, 1000, 5000):
            a = walk(lv, n); row[f"{tag}_avg_{n}"] = round(a, 4) if not math.isnan(a) else np.nan
    return row


# ----------------------------------------------------------------------------------------------- DraftKings at the same moment
def dk_quotes(day):
    p = os.path.join(RESEARCH, "odds", f"{day}.csv")
    if not os.path.exists(p): return {}
    try: O = pd.read_csv(p, dtype={"game_id": str})
    except Exception: return {}
    return {r["game_id"]: r for r in O.sort_values("seen_at_et").groupby("game_id", as_index=False).last().to_dict("records")}


def dk_for(q, market, side, line):
    """(DraftKings line, American price, no-vig chance) for the same bet, when DraftKings has the same line"""
    if q is None: return float("nan"), float("nan"), float("nan")
    sp = "pl" if SPORT == "nhl" else "spread"
    if market == "moneyline":
        a, b = (q.get("home_ml"), q.get("away_ml")) if side == "home" else (q.get("away_ml"), q.get("home_ml"))
        return float("nan"), num(a), fair_pair(a, b)
    if market == "spread":
        hl = num(q.get(f"home_{sp}")); want = line if side == "home" else -line
        if math.isnan(hl) or abs(hl - want) > 1e-9: return hl if side == "home" else -hl, float("nan"), float("nan")
        a, b = (q.get(f"home_{sp}_odds"), q.get(f"away_{sp}_odds")) if side == "home" else (q.get(f"away_{sp}_odds"), q.get(f"home_{sp}_odds"))
        return line, num(a), fair_pair(a, b)
    t = num(q.get("total"))
    if math.isnan(t) or abs(t - line) > 1e-9: return t, float("nan"), float("nan")
    a, b = (q.get("over_odds"), q.get("under_odds")) if side == "over" else (q.get("under_odds"), q.get("over_odds"))
    return line, num(a), fair_pair(a, b)


# ----------------------------------------------------------------------------------------------- one check
SNAP_COLS = ["seen_at_et", "game_id", "date", "away", "home", "market", "line_home", "long_side", "slug", "bid", "ask",
             "bid_depth", "ask_depth", "mid_home_or_over", "last", "shares_traded", "open_interest", "line_source"]
BOOK_COLS = ["seen_at_et", "game_id", "date", "away", "home", "market", "line_home", "long_side", "slug", "bid", "ask", "opened_at_et", "open_px", "bids", "offers"] + \
    [f"{t}_{k}" for t in ("long", "short") for k in ("within_1c", "within_3c", "within_5c", "avg_100", "avg_1000", "avg_5000")]
PAPER_COLS = ["trade_id", "kind", "status", "logged_at_et", "filled_at_et", "game_id", "date", "tip_et", "away", "home", "model",
              "market", "side", "line", "slug", "pm_side", "price", "fee", "cost", "american", "model_p", "model_push", "ev",
              "depth", "bid_at_log", "ask_at_log", "dk_line", "dk_price", "dk_fair_p", "settle", "result", "profit",
              "close_mid", "clv"]


TEXT_COLS = {c: object for c in ("trade_id", "kind", "status", "logged_at_et", "filled_at_et", "game_id", "date", "tip_et", "away", "home",
                                  "model", "market", "side", "slug", "pm_side", "result")}


def read_paper():
    return pd.read_csv(PAPER, dtype=TEXT_COLS) if os.path.exists(PAPER) else pd.DataFrame(columns=PAPER_COLS).astype(TEXT_COLS)


def side_quote(b, pm_side):
    """(price to buy now, best bid, depth at that price, mid) for the long or short side of a contract"""
    bid, ask = b.get("bid", np.nan), b.get("ask", np.nan)
    mid = (bid + ask) / 2 if not (math.isnan(bid) or math.isnan(ask)) else (ask if not math.isnan(ask) else bid)
    if pm_side == "long": return ask, bid, b.get("ask_depth", np.nan), mid
    return 1 - bid, 1 - ask, b.get("bid_depth", np.nan), (1 - mid if not math.isnan(mid) else np.nan)


def check():
    if os.environ.get("POLYMARKET_OFF") and "--force" not in sys.argv:
        print("POLYMARKET_OFF is set; skipping the Polymarket check."); return
    games = {gid: g for gid, g in load_games().items() if g["tip_et"] > NOW}
    if not games: print("Polymarket: no upcoming games in the saved model files."); return
    t1 = min(max(g["tip_et"] for g in games.values()) + pd.Timedelta(hours=6), NOW + pd.Timedelta(hours=170 if SPORT == "nfl" else HOURS_BEFORE))
    events = fetch_events(NOW - pd.Timedelta(hours=1), t1)
    last = load_last(); unmatched_seen = set(last.get("unmatched", [])); unmatched_new = []
    by_pair = {}
    for g in games.values():
        by_pair.setdefault(frozenset((g["home"], g["away"])), []).append(g)

    # ---- match events to games and parse their contracts
    contracts = []                                     # (game, market dict, parsed)
    sample_day = str(TODAY.date())
    for ev in events:
        ids, codes = event_teams(ev)
        st = to_et(ev.get("startTime") or ev.get("gameStartTime") or ev.get("startDate") or ev.get("eventDate"))
        cand = by_pair.get(frozenset(codes), [])
        game = min(cand, key=lambda g: abs((g["tip_et"] - st).total_seconds())) if cand and st is not None else (cand[0] if len(cand) == 1 else None)
        if game is None or (st is not None and abs((game["tip_et"] - st).total_seconds()) > 18 * 3600):
            key = f"{ev.get('slug')}|no game"
            if key not in unmatched_seen:
                unmatched_seen.add(key)
                unmatched_new.append(dict(first_seen_et=str(NOW)[:16], slug=ev.get("slug"), title=ev.get("title"),
                                          start_et=str(st)[:16] if st is not None else "", teams=",".join(sorted(codes)), reason="no matching game in the model files"))
            continue
        mks = event_markets(ev)
        if last.get("samples") != sample_day and not os.path.exists(os.path.join(PM_DIR, "samples", f"{sample_day}_event.json")):  # one raw event a day
            os.makedirs(os.path.join(PM_DIR, "samples"), exist_ok=True)
            json.dump(dict(ev, markets=mks[:8]), open(os.path.join(PM_DIR, "samples", f"{sample_day}_event.json"), "w"), indent=1, default=str)
        for mk in mks:
            status = str(mk.get("status") or "")
            if mk.get("closed") or any(s in status for s in ("CLOSED", "RESOLV", "SETTLED", "HALT")): continue
            parsed, why = parse_market(mk, ids, game)
            if parsed is None:
                if why.startswith("skipped type"): continue
                key = f"{mk.get('slug')}|{why}"
                if key not in unmatched_seen:
                    unmatched_seen.add(key)
                    unmatched_new.append(dict(first_seen_et=str(NOW)[:16], slug=mk.get("slug"), title=mk.get("question"),
                                              start_et=str(game["tip_et"])[:16], teams=f"{game['away']}@{game['home']}", reason=why))
                continue
            if mk.get("slug"): contracts.append((game, mk, parsed))

    # ---- prices
    slugs = sorted({mk["slug"] for _, mk, _ in contracts})
    with ThreadPoolExecutor(WORKERS) as ex:
        B = dict(zip(slugs, ex.map(bbo, slugs)))
    if slugs and last.get("samples") != sample_day:
        ok = next((B[s] for s in slugs if "raw" in B[s]), None)
        if ok: json.dump(ok["raw"], open(os.path.join(PM_DIR, "samples", f"{sample_day}_bbo.json"), "w"), indent=1, default=str)
        last["samples"] = sample_day
    for _, mk, _ in contracts:                         # fall back to the prices in the event listing
        b = B.get(mk["slug"], {})
        if "error" in b or math.isnan(b.get("bid", np.nan)) and math.isnan(b.get("ask", np.nan)):
            B[mk["slug"]] = dict(bid=amount(mk.get("bestBid")), ask=amount(mk.get("bestAsk")), bid_depth=np.nan, ask_depth=np.nan,
                                 last=amount(mk.get("lastTradePrice")), traded=num(mk.get("volumeNum")), oi=np.nan)

    # ---- snapshots (only rows that changed)
    snaps, want_book = {}, []
    bt = last.setdefault("book_t", {})
    for game, mk, P in contracts:
        b = B[mk["slug"]]; side, line = P["long"]
        sig = f"{b.get('bid')}|{b.get('ask')}|{b.get('bid_depth')}|{b.get('ask_depth')}"
        line_home = line if P["market"] == "total" else (line if side == "home" else -line) if P["market"] == "spread" else np.nan
        try: stale = NOW - pd.Timestamp(bt.get(mk["slug"], "2000-01-01")) >= pd.Timedelta(minutes=BOOK_EVERY_MIN)
        except Exception: stale = True
        changed = last["sig"].get(mk["slug"]) != sig
        if (changed or stale) and "error" not in b:
            want_book.append(dict(seen_at_et=str(NOW)[:16], game_id=game["game_id"], date=game["date"], away=game["away"], home=game["home"],
                                  market=P["market"], line_home=line_home, long_side=side, slug=mk["slug"], bid=b.get("bid"), ask=b.get("ask")))
        if not changed: continue
        last["sig"][mk["slug"]] = sig
        _, _, _, mid = side_quote(b, "long")
        home_or_over = side in ("home", "over")
        snaps.setdefault(game["date"], []).append(dict(
            seen_at_et=str(NOW)[:16], game_id=game["game_id"], date=game["date"], away=game["away"], home=game["home"],
            market=P["market"], line_home=line_home, long_side=side, slug=mk["slug"], bid=b.get("bid"), ask=b.get("ask"),
            bid_depth=b.get("bid_depth"), ask_depth=b.get("ask_depth"),
            mid_home_or_over=round(mid if home_or_over else 1 - mid, 4) if not math.isnan(mid) else np.nan,
            last=b.get("last"), shares_traded=b.get("traded"), open_interest=b.get("oi"), line_source=P["src"]))
    for day, rows in snaps.items(): append_csv(os.path.join(PM_DIR, f"{day}.csv"), rows, SNAP_COLS)
    n_book = 0
    if want_book:                                      # full order books for the contracts that moved (or are due)
        with ThreadPoolExecutor(WORKERS) as ex: BK = list(ex.map(book, [w["slug"] for w in want_book]))
        out = {}
        for w, bk in zip(want_book, BK):
            if "error" in bk or not (bk["bids"] or bk["offers"]): continue
            bt[w["slug"]] = str(NOW)
            out.setdefault(w["date"], []).append(dict(w, **book_row(bk))); n_book += 1
            if not os.path.exists(os.path.join(PM_DIR, "samples", f"{sample_day}_book.json")):
                json.dump(bk["raw"], open(os.path.join(PM_DIR, "samples", f"{sample_day}_book.json"), "w"), indent=1, default=str)
        for day, rows in out.items(): append_csv(os.path.join(PM_DIR, f"book_{day}.csv"), rows, BOOK_COLS)
    append_csv(os.path.join(PM_DIR, "unmatched.csv"), unmatched_new)

    # ---- paper trades
    T = read_paper()
    have = set(zip(T.game_id, T.market, T.model, T.kind)) if len(T) else set()
    thr = THRESHOLD[SPORT]; new, n_fill = [], 0
    DK = {d: dk_quotes(d) for d in {g["date"] for g in games.values()}}

    # fill resting maker orders whose price was reached
    if len(T):
        for i, r in T[(T.kind == "maker") & (T.status == "open")].iterrows():
            tip = pd.Timestamp(r.tip_et)
            if NOW >= tip:
                T.loc[i, ["status", "result", "profit"]] = ["unfilled", "unfilled", 0.0]; continue
            b = B.get(r.slug)
            if not b: continue
            buy, _, _, _ = side_quote(b, r.pm_side)
            if not math.isnan(buy) and buy <= float(r.price) + 1e-9:
                T.loc[i, ["status", "filled_at_et"]] = ["filled", str(NOW)[:16]]; n_fill += 1

    for game in games.values():
        mine = [(mk, P) for g2, mk, P in contracts if g2 is game]
        if not mine: continue
        for name, prob in game["models"].items():
            for market in PAPER_MARKETS[SPORT]:
                best_t, best_m = None, None
                for mk, P in mine:
                    if P["market"] != market: continue
                    b = B[mk["slug"]]
                    for pm_side in ("long", "short"):
                        side, line = P[pm_side]
                        pp = prob(market, side, line)
                        if pp is None: continue
                        p, push = pp
                        buy, bid_s, depth, mid = side_quote(b, pm_side)
                        base = dict(game=game, mk=mk, P=P, pm_side=pm_side, side=side, line=line, p=p, push=push, bid=bid_s, buy=buy, depth=depth, mid=mid)
                        if not math.isnan(buy) and 0 < buy < 1 and (math.isnan(depth) or depth >= MIN_DEPTH):
                            cost = buy + taker_fee(buy)
                            ev = (p + push * cost) / cost - 1
                            if best_t is None or ev > best_t["ev"]: best_t = dict(base, price=buy, fee=taker_fee(buy), cost=cost, ev=ev)
                        lim = math.floor(p / (1 + thr) * 100) / 100 if p > 0 else 0.0
                        if MAKER and 0.01 <= lim < 0.99 and (math.isnan(bid_s) or lim > bid_s + 1e-9) and (math.isnan(buy) or lim < buy - 1e-9):
                            cost = lim + maker_fee(lim); ev = (p + push * cost) / cost - 1
                            if best_m is None or p - lim > best_m["p"] - best_m["price"]:
                                best_m = dict(base, price=lim, fee=maker_fee(lim), cost=cost, ev=ev)
                for kind, c in (("taker", best_t), ("maker", best_m)):
                    if c is None or (game["game_id"], market, name, kind) in have: continue
                    if kind == "taker" and c["ev"] < thr: continue
                    dl, dp, dfp = dk_for(DK[game["date"]].get(game["game_id"]), market, c["side"], c["line"])
                    new.append(dict(
                        trade_id=f"{game['game_id']}-{market}-{name}-{kind}", kind=kind, status="filled" if kind == "taker" else "open",
                        logged_at_et=str(NOW)[:16], filled_at_et=str(NOW)[:16] if kind == "taker" else "", game_id=game["game_id"],
                        date=game["date"], tip_et=str(game["tip_et"])[:16], away=game["away"], home=game["home"], model=name,
                        market=market, side=c["side"], line=c["line"], slug=c["mk"]["slug"], pm_side=c["pm_side"],
                        price=round(c["price"], 4), fee=round(c["fee"], 5), cost=round(c["cost"], 5), american=round(american(c["cost"]), 1),
                        model_p=round(c["p"], 4), model_push=round(c["push"], 4), ev=round(c["ev"], 4), depth=c["depth"],
                        bid_at_log=c["bid"], ask_at_log=c["buy"], dk_line=dl, dk_price=dp, dk_fair_p=round(dfp, 4) if not math.isnan(dfp) else np.nan))
                    have.add((game["game_id"], market, name, kind))

    if new: T = pd.concat([T, pd.DataFrame(new)], ignore_index=True)
    if new or n_fill or len(T): T.reindex(columns=PAPER_COLS).to_csv(PAPER, index=False)
    last["unmatched"] = sorted(unmatched_seen)[-5000:]
    json.dump(last, open(LAST, "w"))
    nm_ = MARKET_NAME[SPORT]
    print(f"Polymarket: {len(events)} {SPORT.upper()} events, {len(contracts)} contracts on {len({g['game_id'] for g, _, _ in contracts})} of "
          f"{len(games)} games, {sum(len(v) for v in snaps.values())} price changes saved, {n_book} order books saved, {len(new)} new paper trades, "
          f"{n_fill} limit orders filled, {len(unmatched_new)} new unmatched.")
    for r in new:
        ln = "" if r["market"] == "moneyline" else (f" {r['line']:+g}" if r["market"] == "spread" else f" {r['line']:g}")
        print(f"  [{r['kind']}] {r['away'].upper()} @ {r['home'].upper()} {nm_.get(r['market'], r['market'])} {r['side']}{ln} at {r['price']:.2f} "
              f"(model {r['model_p']:.1%}, EV {r['ev']:+.1%}, model={r['model']})")


# ----------------------------------------------------------------------------------------------- grading and report
def settlement(slug):
    try:
        r = get_json(f"/v1/markets/{urllib.parse.quote(slug, safe='')}/settlement")
        v = amount(r.get("settlement", r.get("settlementPx")) if isinstance(r, dict) else r)
        return v if 0 <= v <= 1 else float("nan")
    except Exception:
        return float("nan")


def close_mid(r):
    """the side's last mid price before the start, from the snapshots"""
    p = os.path.join(PM_DIR, f"{r.date}.csv")
    if not os.path.exists(p): return float("nan")
    S = pd.read_csv(p)
    S = S[(S.slug == r.slug) & (S.seen_at_et <= str(r.tip_et)[:16])]
    if not len(S): return float("nan")
    s = S.iloc[-1]; long_side = s.long_side
    bid, ask = num(s.bid), num(s.ask)
    mid = (bid + ask) / 2 if not (math.isnan(bid) or math.isnan(ask)) else float("nan")
    if math.isnan(mid): return float("nan")
    return mid if r.pm_side == "long" else 1 - mid


def grade():
    if not os.path.exists(PAPER): print("No Polymarket paper trades yet."); report(pd.DataFrame(columns=PAPER_COLS)); return
    T = read_paper()
    for c in ("settle", "profit", "close_mid", "clv"): T[c] = pd.to_numeric(T[c], errors="coerce")
    n = 0
    for i, r in T.iterrows():
        if r.kind == "maker" and r.status == "open" and NOW >= pd.Timestamp(r.tip_et):
            T.loc[i, ["status", "result", "profit"]] = ["unfilled", "unfilled", 0.0]; continue
        if r.status != "filled" or isinstance(r.result, str) and r.result in ("W", "L", "P", "partial"): continue
        if NOW < pd.Timestamp(r.tip_et) + pd.Timedelta(hours=4): continue
        s = settlement(r.slug)
        if math.isnan(s): continue
        v = s if r.pm_side == "long" else 1 - s
        cost = float(r.cost)
        T.loc[i, "settle"] = v
        T.loc[i, "result"] = "W" if v >= 0.99 else "L" if v <= 0.01 else ("P" if abs(v - cost) < 0.02 else "partial")
        T.loc[i, "profit"] = round((v - cost) / cost, 4)            # units: 1 unit = $1 spent
        cm = close_mid(r)
        T.loc[i, "close_mid"] = round(cm, 4) if not math.isnan(cm) else np.nan
        T.loc[i, "clv"] = round(100 * (cm - float(r.price)), 2) if not math.isnan(cm) else np.nan
        n += 1
    T.reindex(columns=PAPER_COLS).to_csv(PAPER, index=False)
    print(f"Polymarket: graded {n} paper trades.")
    report(T)


def report(T):
    os.makedirs(PM_DIR, exist_ok=True)
    nm_ = MARKET_NAME[SPORT]
    L = [f"# Polymarket US paper trades ({SPORT.upper()})", "",
         f"Updated {NOW:%Y-%m-%d %H:%M} ET by `polymarket.py --grade`. Nothing here was actually bet: these are the trades the model "
         f"would have made on Polymarket US. 1 unit = $1 spent (price plus fee). Taker = bought at the best offer; maker = a limit bid at the "
         f"highest price with {THRESHOLD[SPORT]:.0%}+ expected value, counted as filled if the best offer later fell to it before the game "
         f"(approximate). CLV = the side's last mid price before the start minus the price paid, in cents (positive = the market moved toward us).", ""]
    G = T[T.result.isin(["W", "L", "P", "partial"])] if len(T) else T
    if len(G):
        G = G.assign(profit=G.profit.astype(float), clv=pd.to_numeric(G.clv, errors="coerce"), ev=G.ev.astype(float))
        L += ["| model | market | kind | trades | W-L | units | ROI | avg EV at entry | avg CLV (cents) |", "|---|---|---|---|---|---|---|---|---|"]
        for (m, mk, k), g in G.groupby(["model", "market", "kind"]):
            L.append(f"| {m} | {nm_.get(mk, mk)} | {k} | {len(g)} | {(g.result == 'W').sum()}-{(g.result == 'L').sum()} | {g.profit.sum():+.2f} | "
                     f"{g.profit.sum() / len(g):+.1%} | {g.ev.mean():+.1%} | {g.clv.mean():+.2f} |")
        L.append("")
    else:
        L += ["No graded trades yet.", ""]
    if len(T):
        mk_ = T[T.kind == "maker"]
        if len(mk_):
            done = mk_[mk_.status.isin(["filled", "unfilled"])]
            if len(done): L += [f"Limit orders: {(done.status == 'filled').sum()} of {len(done)} filled before the game.", ""]
        tk = T[(T.kind == "taker") & T.dk_price.notna()]
        if len(tk):
            dk_cost = tk.dk_price.map(lambda o: 1 / dec(o))
            better = (tk.cost.astype(float) < dk_cost).mean()
            L += [f"Same bet at DraftKings at the moment of the trade (same line): Polymarket was cheaper on {better:.0%} of {len(tk)} taker trades "
                  f"(average {100 * (dk_cost - tk.cost.astype(float)).mean():+.1f} cents per $1 contract in Polymarket's favor).", ""]
        pend = T[(T.status == "filled") & ~T.result.isin(["W", "L", "P", "partial"])]
        L += [f"Waiting to be graded: {len(pend)}. Open limit orders: {int(((T.kind == 'maker') & (T.status == 'open')).sum())}.", ""]
    bf = sorted(glob.glob(os.path.join(PM_DIR, "book_20*.csv")))[-3:]
    if bf:
        try:
            Bk = pd.concat([pd.read_csv(x) for x in bf])
            Bk["ask"] = pd.to_numeric(Bk.ask, errors="coerce")
            L += ["## Order book depth (last 3 days of saved books)", "",
                  "Contracts you could buy on the long side at the best offer plus 1 / 3 / 5 cents, and what it would cost to buy 1,000 contracts "
                  "(about $300-700) by walking the book: average price above the best offer, in cents, and how often the book was deep enough. "
                  "Full levels are in `research/polymarket/book_YYYY-MM-DD.csv`.", "",
                  "| market | snapshots | within 1c | within 3c | within 5c | 1,000 contracts: extra cents | deep enough for 1,000 |", "|---|---|---|---|---|---|---|"]
            for mk, g in Bk.groupby("market"):
                a1 = pd.to_numeric(g.long_avg_1000, errors="coerce")
                L.append(f"| {nm_.get(mk, mk)} | {len(g)} | {g.long_within_1c.median():.0f} | {g.long_within_3c.median():.0f} | "
                         f"{g.long_within_5c.median():.0f} | {(100 * (a1 - g.ask)).median():+.1f} | {a1.notna().mean():.0%} |")
            L.append("")
        except Exception as e:
            L += [f"(order book summary failed: {type(e).__name__})", ""]
    um = os.path.join(PM_DIR, "unmatched.csv")
    if os.path.exists(um):
        U = pd.read_csv(um)
        if len(U): L += [f"Contracts or events the tracker couldn't read: {len(U)} (see `research/polymarket/unmatched.csv`).", ""]
    open(os.path.join(PM_DIR, "REPORT.md"), "w").write("\n".join(L))
    print("Wrote research/polymarket/REPORT.md")


if __name__ == "__main__":
    try:
        if "--residuals" in sys.argv: build_residuals()
        elif "--grade" in sys.argv: grade()
        else: check()
    except Exception as e:                              # never stop the alert loop
        import traceback; traceback.print_exc()
        print(f"Polymarket check failed: {type(e).__name__}: {e}")
