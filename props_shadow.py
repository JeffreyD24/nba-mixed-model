"""
NBA player props SHADOW record (paper only, no alerts, no real bets) — props v1b frozen in data/props_v1b_params.json.
Why paper: the backtest made money (+116u test) but did not beat the closing line (research/props/PROPS_V1_RESULTS_2026-11-05.md).
Prices: FanDuel's public NBA pages (free; where nearly all of the backtest profit was).

  python props_shadow.py WORKDIR snapshot   every hour: FanDuel points / rebounds / assists / threes lines for today's games
                                              -> research/props_fd/{date}.csv (rows appended when a line or price changes)
  python props_shadow.py WORKDIR pick       once, ~11:30 AM ET: model probabilities vs FanDuel, EV >= 5% -> state/props_shadow.csv
  python props_shadow.py WORKDIR grade      next morning: result (box score) and FanDuel's last pre-tip line (closing-line EV)
"""
import os, sys, re, json, glob, unicodedata, urllib.request
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
from scipy import stats

W = os.path.abspath(sys.argv[1]); MODE = sys.argv[2]; sys.path.insert(0, W)
ET = ZoneInfo("America/New_York")
P = json.load(open(os.path.join(W, "data", "props_v1b_params.json")))
STATS = ["pts", "reb", "ast", "fg3m"]
FD_TABS = {"player-points": "pts", "player-rebounds": "reb", "player-assists": "ast", "player-threes": "fg3m"}
FD_TYPE = re.compile(r"^PLAYER_[A-Z]+_(TOTAL_POINTS|TOTAL_REBOUNDS|TOTAL_ASSISTS|MADE_THREES|TOTAL_MADE_THREES|TOTAL_THREES|THREES)$")
AK, BASE = "FhMFpcPWXMeyZxOx", "https://sbapi.ct.sportsbook.fanduel.com/api"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "application/json"}
SHADOW = os.path.join(W, "state", "props_shadow.csv")
NOW = dt.datetime.now(ET); TODAY = NOW.strftime("%Y-%m-%d"); TOMORROW = (NOW + dt.timedelta(days=1)).strftime("%Y-%m-%d")


FULL = {"Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
        "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det", "Golden State Warriors": "gs",
        "Houston Rockets": "hou", "Indiana Pacers": "ind", "LA Clippers": "lac", "Los Angeles Clippers": "lac", "Los Angeles Lakers": "lal",
        "Memphis Grizzlies": "mem", "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min", "New Orleans Pelicans": "no",
        "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl", "Philadelphia 76ers": "phi", "Phoenix Suns": "phx",
        "Portland Trail Blazers": "por", "Sacramento Kings": "sac", "San Antonio Spurs": "sa", "Toronto Raptors": "tor", "Utah Jazz": "utah",
        "Washington Wizards": "wsh"}


def norm(n):
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"[.'`]", "", n).replace("-", " "); n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=30) as r: return json.loads(r.read())


def dec(a): a = np.asarray(a, float); return np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))


# ---------------- FanDuel snapshot
def snapshot():
    d = get(f"{BASE}/content-managed-page?page=CUSTOM&customPageId=nba&_ak={AK}&timezone=America%2FNew_York")
    evs = [e for e in d.get("attachments", {}).get("events", {}).values() if " @ " in e.get("name", "")]
    rows = []
    for e in evs:
        tip = pd.Timestamp(e["openDate"]).tz_convert(ET)
        gdate = tip.strftime("%Y-%m-%d")
        if gdate not in (TODAY, TOMORROW) or tip < pd.Timestamp(NOW): continue   # Nov 5, 2026: tomorrow too, to catch openers early
        away, home = [FULL.get(x.strip()) for x in e["name"].split(" @ ")]
        for tab, stat in FD_TABS.items():
            try: p = get(f"{BASE}/event-page?_ak={AK}&eventId={e['eventId']}&tab={tab}&timezone=America%2FNew_York")
            except Exception as ex: print(f"{e['name']} {tab}: {ex}"); continue
            for m in p.get("attachments", {}).get("markets", {}).values():
                mt = m.get("marketType", "")
                ok = FD_TYPE.match(mt) or (stat == "fg3m" and mt.startswith("PLAYER_") and "THREE" in mt and "QUARTER" not in mt)
                if not ok or len(m.get("runners", [])) != 2: continue
                r = {x.get("result", {}).get("type"): x for x in m["runners"]}
                if "OVER" not in r or "UNDER" not in r: continue
                o, u = r["OVER"], r["UNDER"]
                odds = lambda x: (x.get("winRunnerOdds") or {}).get("americanDisplayOdds", {}).get("americanOdds")
                rows.append(dict(seen_at_et=NOW.strftime("%Y-%m-%d %H:%M"), date=gdate, event_id=e["eventId"], tip_et=tip.strftime("%Y-%m-%d %H:%M"),
                                 game=e["name"], home=home, away=away, stat=stat, player=m["marketName"].split(" - ")[0], name=norm(m["marketName"].split(" - ")[0]),
                                 line=o.get("handicap"), over=odds(o), under=odds(u), team_abbr=o.get("teamAbbr"),
                                 market_id=m.get("marketId"), over_sel=o.get("selectionId"), under_sel=u.get("selectionId")))     # Nov 6, 2026: ids for the FanDuel bet-slip link
    allnew = pd.DataFrame(rows)
    rp = os.path.join(W, "state", "props_fd_runs.csv")      # every snapshot time, so an "opener" is only trusted if a run just before it saw nothing
    pd.DataFrame([dict(run_et=NOW.strftime("%Y-%m-%d %H:%M"), lines=len(rows))]).to_csv(rp, mode="a", header=not os.path.exists(rp), index=False)
    if allnew.empty: print("no FanDuel prop lines right now"); return
    for gdate, new in allnew.groupby("date"):
        path = os.path.join(W, "research", "props_fd", f"{gdate}.csv"); os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            old = pd.read_csv(path); last = old.sort_values("seen_at_et").drop_duplicates(["event_id", "stat", "name"], keep="last")
            m = new.merge(last[["event_id", "stat", "name", "line", "over", "under"]], on=["event_id", "stat", "name"], how="left", suffixes=("", "_old"))
            new = new[~((m.line == m.line_old) & (m.over == m.over_old) & (m.under == m.under_old)).values]
            pd.concat([old, new], ignore_index=True).to_csv(path, index=False)
        else:
            new.to_csv(path, index=False)
    new = allnew
    print(f"FanDuel props: {len(rows)} lines now ({new.stat.value_counts().to_dict() if len(new) else 'no changes'})")


# ---------------- model (same as analysis/props_v1.py v1b), state as of today
def player_state():
    files = {int(re.search(r"(\d{4})", f).group(1)): f for f in glob.glob(os.path.join(W, "data", "player_stats", "season_*.csv.gz"))}
    cur = max(files); B = pd.read_csv(files[cur], dtype={"player_id": str, "game_id": str}); B = B[(B["min"] > 0) & (B.date < TODAY)].copy()
    prev = pd.read_csv(files[cur - 1], dtype={"player_id": str}); prev = prev[prev["min"] > 0]
    pa = prev.groupby("player_id").agg(g=("min", "size"), m=("min", "sum"), **{s: (s, "sum") for s in STATS})
    lg_rate = {s: prev[s].sum() / prev["min"].sum() for s in STATS}
    dm, dr = 0.5 ** (1 / P["hl_min"]), 0.5 ** (1 / P["hl_rate"])
    out = []
    for pid, g in B.sort_values("date").groupby("player_id"):
        pr = pa.loc[pid] if pid in pa.index else None
        p_mpg = pr.m / pr.g if pr is not None else 18.0
        p_rate = {s: (pr[s] / pr.m if pr is not None and pr.m >= 300 else lg_rate[s]) for s in STATS}
        Sm = Sw = Srm = 0.0; Sr = {s: 0.0 for s in STATS}
        for r in g.itertuples():
            Sm = Sm * dm + r.min; Sw = Sw * dm + 1; Srm = Srm * dr + r.min
            for s in STATS: Sr[s] = Sr[s] * dr + getattr(r, s)
        row = dict(player_id=pid, player=g.player.iloc[-1], name=norm(g.player.iloc[-1]), team=g.team.iloc[-1], n_prev=len(g), last_date=g.date.iloc[-1],
                   min_proj=(Sm + P["prior_games"] * p_mpg) / (Sw + P["prior_games"]))
        for s in STATS: row[f"rate_{s}"] = (Sr[s] + P["prior_min"] * p_rate[s]) / (Srm + P["prior_min"])
        out.append(row)
    S = pd.DataFrame(out)
    # opponent allowed per game (shrunk to last season's league average, k games)
    TG = B.groupby(["date", "game_id", "team"])[STATS].sum().reset_index()
    J = TG.merge(TG, on=["date", "game_id"], suffixes=("", "_o")); J = J[J.team != J.team_o]
    base = {s: prev.groupby(["game_id", "team"])[s].sum().mean() for s in STATS}
    allow = {}
    for t, g in J.groupby("team"):
        allow[t] = {s: ((g[f"{s}_o"].sum() + P["k_opp"] * base[s]) / (len(g) + P["k_opp"])) / base[s] for s in STATS}
    return S, allow


def p_over(mu, stat, line, params=None):
    a, b = (params or P)["var_ab"][stat]; ex = (a - 1) * mu + b * mu ** 2
    r = mu ** 2 / ex if ex > 1e-6 else 1e6
    return float(1 - stats.nbinom.cdf(np.floor(line), r, r / (r + mu)))


def stop_price(popen, p, ev_min, tol=0.05):
    """Worst American price the live rule still bets (Nov 6, 2026, Jeffrey asked every alert to say when to stop).
    Same two checks as live(): decimal price within `tol` of the opener's, and EV >= ev_min at that price."""
    ok = lambda a: abs(float(dec(a)) - float(dec(popen))) <= tol and p * float(dec(a)) - 1 >= ev_min   # exactly live()'s checks
    a = int(popen)
    if not ok(a): return None
    while True:                                   # step one cent worse at a time (-118 -> -119 ...; +110 -> +109 ... +100 -> -101)
        nxt = a - 1 if a > 100 else (-101 if a == 100 else a - 1)
        if not ok(nxt): return a
        a = nxt


def pick():
    import actionnet
    path = os.path.join(W, "research", "props_fd", f"{TODAY}.csv")
    if not os.path.exists(path): print("no FanDuel snapshot today"); return
    L = pd.read_csv(path).sort_values("seen_at_et").drop_duplicates(["event_id", "stat", "name"], keep="last")
    S, allow = player_state()
    # pace: DraftKings full-game total (Action Network) vs this season's average opener so far
    an = actionnet.lines(TODAY); an["game_total"] = an.an_total
    O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv")); avg = O[O.book == "draftkings"].open_total.tail(1230).mean()
    LS = L.merge(S, on="name", how="inner")
    teams = {}
    for r in an.itertuples(): teams[r.home] = (r.away, r.an_total); teams[r.away] = (r.home, r.an_total)
    rows = []
    done = set(pd.read_csv(SHADOW).key) if os.path.exists(SHADOW) else set()
    for r in LS.itertuples():
        if r.n_prev < 3: continue
        opp, tot = teams.get(r.team, (None, np.nan))
        pace = (tot / avg) if (tot == tot and r.stat != "reb") else 1.0
        mu = r.min_proj * getattr(r, f"rate_{r.stat}") * (allow.get(opp, {}).get(r.stat, 1.0)) * pace
        pm = p_over(max(mu, 0.05), r.stat, r.line)
        qo, qu = 1 / dec(r.over), 1 / dec(r.under); pk = float(qo / (qo + qu))
        p = P["w_model"] * pm + (1 - P["w_model"]) * pk
        for side, ps, price in (("over", p, r.over), ("under", 1 - p, r.under)):
            ev = ps * float(dec(price)) - 1
            key = f"{TODAY}|{r.event_id}|{r.stat}|{r.name}"
            if ev >= P["ev_min"] and key not in done:
                rows.append(dict(key=key, date=TODAY, logged_at_et=NOW.strftime("%Y-%m-%d %H:%M"), model_version=P["version"], book="FanDuel",
                                 game=r.game, tip_et=r.tip_et, player=getattr(r, "player_x", getattr(r, "player", "")), name=r.name,
                                 team=r.team, stat=r.stat, side=side, line=r.line, price=int(price), mu=round(mu, 2), p_model=round(pm, 4),
                                 p_market=round(pk, 4), p=round(ps, 4), ev=round(ev, 4), units=1, result="", actual="", u="",
                                 close_line="", close_price="", close_other="", close_ev=""))
                done.add(key)
    new = pd.DataFrame(rows)
    if len(new):
        new.to_csv(SHADOW, mode="a", header=not os.path.exists(SHADOW), index=False)
    print(f"props shadow: {len(new)} paper bets logged for {TODAY} (from {len(LS)} FanDuel lines matched to players)")


def grade(path=None, params=None):
    path = path or SHADOW; params = params or P
    if not os.path.exists(path): print(f"nothing to grade in {os.path.basename(path)}"); return
    D = pd.read_csv(path, dtype=str)
    files = sorted(glob.glob(os.path.join(W, "data", "player_stats", "season_*.csv.gz")))
    B = pd.read_csv(files[-1], dtype={"player_id": str}); B["name"] = B.player.map(norm)
    n = 0
    for i, r in D[(D.result.isna() | (D.result == "")) & (D.date < TODAY)].iterrows():
        b = B[(B.date == r.date) & (B.name == r["name"])]
        if b.empty:
            if r.date < (NOW - dt.timedelta(days=3)).strftime("%Y-%m-%d"): D.loc[i, ["result", "u"]] = ["void (no box score)", "0"]
            continue
        if float(b["min"].iloc[0]) <= 0: D.loc[i, ["result", "u"]] = ["void (did not play)", "0"]; n += 1; continue
        a = float(b[r.stat].iloc[0]); line = float(r.line); price = float(r.price)
        won = a > line if r.side == "over" else a < line
        D.loc[i, "actual"] = a
        D.loc[i, "result"] = "push" if a == line else ("win" if won else "loss")
        D.loc[i, "u"] = 0.0 if a == line else (round(float(dec(price)) - 1, 4) if won else -1.0)
        # FanDuel's last line before tip
        fp = os.path.join(W, "research", "props_fd", f"{r.date}.csv")
        if os.path.exists(fp):
            L = pd.read_csv(fp); L = L[(L.name == r["name"]) & (L.stat == r.stat) & (L.seen_at_et < L.tip_et)].sort_values("seen_at_et")
            if len(L):
                c = L.iloc[-1]; qo, qu = 1 / dec(c.over), 1 / dec(c.under); fo = float(qo / (qo + qu))
                if float(c.line) != line:     # move the close to our line with a normal shift (sd from the model's spread)
                    a_, b_ = params["var_ab"][r.stat]; mu = float(r.mu); sd = np.sqrt(max(a_ * mu + b_ * mu ** 2, mu))
                    m = float(c.line) + sd * stats.norm.ppf(min(max(fo, 0.01), 0.99)); fo = float(1 - stats.norm.cdf((line - m) / sd))
                side_p = fo if r.side == "over" else 1 - fo
                D.loc[i, ["close_line", "close_price", "close_other"]] = [c.line, c.over if r.side == "over" else c.under, c.under if r.side == "over" else c.over]
                D.loc[i, "close_ev"] = round(side_p * float(dec(price)) - 1, 4)
        n += 1
    D.to_csv(path, index=False)
    g = D[D.result.isin(["win", "loss", "push"])]
    if len(g):
        u = g.u.astype(float); ce = pd.to_numeric(g.close_ev, errors="coerce")
        print(f"{os.path.basename(path)} graded {n}; record {(g.result == 'win').sum()}-{(g.result == 'loss').sum()}-{(g.result == 'push').sum()}, "
              f"{u.sum():+.1f}u, closing-line EV {ce.mean()*100:+.2f}% (n {ce.notna().sum()})")


# ---------------- PROVISIONAL real-money alerts (Nov 5, 2026; research/PROVISIONAL_BETS.md registry row "NBA props v1b at FanDuel openers")
LIVE = os.path.join(W, "state", "props_live.csv")
PO_PATH = os.path.join(W, "data", "props_v1b_open_params.json")


def push(title, body, actions=""):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic: print("NTFY_TOPIC not set; would have sent:", title, "|", body); return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high", "Tags": "basketball", **({"Actions": actions} if actions else {})})
    urllib.request.urlopen(req, timeout=20); return True


def live():
    """bet FanDuel props still at their FanDuel opener (first line we saw), opener 4h+ before tip, EV >= 5% (v1b, clean params)"""
    import actionnet
    PO = json.load(open(PO_PATH))
    h0, h1 = PO["alert_hours_et"]
    if not (h0 <= NOW.hour < h1): print(f"props live: {NOW:%H:%M} ET is outside {h0}:00-{h1}:00; nothing sent"); return
    if NOW.month in PO["skip_months"]: print("props live: April, no provisional prop bets (declared Nov 5, 2026)"); return
    if TODAY < PO["live_from"]: print(f"props live: starts {PO['live_from']} (the first day FanDuel openers are captured from the night before)"); return
    path = os.path.join(W, "research", "props_fd", f"{TODAY}.csv")
    if not os.path.exists(path): print("props live: no FanDuel lines for today yet"); return
    A = pd.read_csv(path).sort_values("seen_at_et")
    first = A.drop_duplicates(["event_id", "stat", "name"], keep="first"); last = A.drop_duplicates(["event_id", "stat", "name"], keep="last")
    J = last.merge(first[["event_id", "stat", "name", "line", "over", "under", "seen_at_et"]], on=["event_id", "stat", "name"], suffixes=("", "_open"))
    tip = pd.to_datetime(J.tip_et); first_seen = pd.to_datetime(J.seen_at_et_open)
    now_n = pd.Timestamp(NOW.replace(tzinfo=None))
    J = J[(J.line == J.line_open) & (J.line >= PO["min_line"]) & ((tip - now_n).dt.total_seconds() >= PO["min_lead_hours_any"] * 3600)].copy()
    rp = os.path.join(W, "state", "props_fd_runs.csv")
    runs = pd.to_datetime(pd.read_csv(rp).run_et).sort_values().tolist() if os.path.exists(rp) else []
    def prior_run_ok(t):      # Fable fix 3: a real opener = a snapshot ran 1-45 min before it and did not have the line
        before = [x for x in runs if x < t - pd.Timedelta(minutes=1)]
        return bool(before) and (t - before[-1]) <= pd.Timedelta(minutes=45)
    fs = pd.to_datetime(J.seen_at_et_open); lead = (pd.to_datetime(J.tip_et) - fs).dt.total_seconds() / 3600
    fresh = ((now_n - fs) <= pd.Timedelta(minutes=40)).values & np.array([prior_run_ok(t) for t in fs], dtype=bool)
    # three PROVISIONAL tiers, each its own record (Jeffrey, Nov 5, 2026): early = the backtested slice; late and stale added by him
    J["tier"] = np.where(fresh & (lead >= PO["min_lead_hours"]).values, "early", np.where(fresh, "late", "stale"))
    S, allow = player_state()
    try: an = actionnet.lines(TODAY)
    except Exception as e:
        print("props live: Action Network totals unavailable, pace = 1:", e); an = pd.DataFrame(columns=["home", "away", "an_total"])
    O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv")); avg = O[O.book == "draftkings"].open_total.tail(1230).mean()
    teams = {}
    for r in an.itertuples(): teams[r.home] = (r.away, r.an_total); teams[r.away] = (r.home, r.an_total)
    LS = J.merge(S, on="name", how="inner", suffixes=("", "_s"))
    done = set(pd.read_csv(LIVE).key) if os.path.exists(LIVE) else set()
    rows = []
    for r in LS.itertuples():
        if r.n_prev < 3: continue
        if str(r.last_date) >= str(r.seen_at_et_open)[:10]: continue      # Fable fix 5: no result from the opener's own day in the features
        vals = [r.over, r.under, r.over_open, r.under_open]
        if not all(np.isfinite(float(v)) and 100 <= abs(float(v)) <= 1000 for v in vals): continue   # Fable fix 2: suspended / bad quotes
        opp, tot = teams.get(r.team, (None, np.nan))
        pace = (tot / avg) if (tot == tot and r.stat != "reb") else 1.0
        mu = r.min_proj * getattr(r, f"rate_{r.stat}") * allow.get(opp, {}).get(r.stat, 1.0) * pace
        pm = p_over(max(mu, 0.05), r.stat, r.line, PO)
        qo, qu = 1 / dec(r.over_open), 1 / dec(r.under_open); pk = float(qo / (qo + qu))     # the opener's own prices, as in the backtest
        p = PO["w_model"] * pm + (1 - PO["w_model"]) * pk
        for side, ps, price, popen in (("over", p, r.over, r.over_open), ("under", 1 - p, r.under, r.under_open)):
            # backtest = bet AT the opener: line unchanged AND this side's price within 5 cents of its opening price; EV at the opening price
            if abs(float(dec(price)) - float(dec(popen))) > 0.05: continue
            ev = ps * float(dec(popen)) - 1
            ev_now = ps * float(dec(price)) - 1                 # Fable: EV must also clear 5% at the price Jeffrey actually gets
            key = f"{TODAY}|{r.event_id}|{r.stat}|{r.name}"
            if not np.isfinite(ev) or ev < PO["ev_min"] or ev_now < PO["ev_min"] or key in done: continue
            tier_lab = {"early": "PROVISIONAL PROP", "late": "PROVISIONAL PROP (LATE)", "stale": "PROVISIONAL PROP (STALE OPENER)"}[r.tier]
            done.add(key)
            sname = {"pts": "points", "reb": "rebounds", "ast": "assists", "fg3m": "threes"}[r.stat]
            title = f"{tier_lab} - {r.player} {side.upper()} {r.line:g} {sname} {int(price):+d} (FanDuel)"
            body = (f"{r.game}, tip {str(r.tip_et)[11:16]} ET. Model projects {mu:.1f} {sname}; chance {ps*100:.0f}% vs FanDuel's {((pk if side == 'over' else 1-pk))*100:.0f}%, "
                    f"EV {ev*100:+.1f}%. Still at FanDuel's opening line. {tier_lab} (props v1b at FanDuel openers, tier '{r.tier}'): 1 unit, own record, "
                    f"stop rules in research/PROVISIONAL_BETS.md. Backtest 2023-25 at FanDuel openers: 4h+ before tip +3.9% ROI; 1-4h +22%; stale not tested. "
                    f"Log it with 'Log a bet' (market: prop) if you place it.")
            # Nov 6, 2026 (Jeffrey): every alert says exactly when to stop placing it (the same two price checks this rule uses)
            sp = stop_price(popen, ps, PO["ev_min"])
            if sp is not None: body += (f"\nSTOP: bet only {side.upper()} {r.line:g} at {sp:+d} or better at FanDuel. If the line leaves {r.line:g} or the price "
                     f"gets worse than {sp:+d}, don't bet it (outside the opener window or EV under {PO['ev_min']*100:.0f}%).\n")
            # Nov 6, 2026 (Jeffrey): FanDuel + DraftKings links and which book is better, by the model's own EV at each book's line and price
            try:
                import dk_props, fanduel
                dkq = dk_props.quote(r.stat, r.name)
                ps_at = lambda ln: (p_over(max(mu, 0.05), r.stat, ln, PO) if side == "over" else 1 - p_over(max(mu, 0.05), r.stat, ln, PO))
                ev_fd = ps_at(r.line) * float(dec(price)) - 1
                fd_link = (f"https://sportsbook.fanduel.com/addToBetslip?marketId[0]={r.market_id}&selectionId[0]={r.over_sel if side == 'over' else r.under_sel}"
                           if pd.notna(getattr(r, "market_id", np.nan)) else fanduel.FD_PAGE["nba"])
                if dkq:
                    dpx = dkq[side]; ev_dk = ps_at(dkq["line"]) * float(dec(dpx)) - 1
                    best = "FanDuel" if ev_fd >= ev_dk else "DraftKings"
                    comp = (f"BEST: {best}. FanDuel {side} {r.line:g} ({int(price):+d}) model EV {ev_fd*100:+.1f}% | "
                            f"DraftKings {side} {dkq['line']:g} ({int(dpx):+d}) model EV {ev_dk*100:+.1f}%")
                    dk_link = dkq[side + "_link"]
                else:
                    best, dk_link = "FanDuel", None
                    comp = f"BEST: FanDuel (no DraftKings {sname} line found for {r.player}: not posted, or not reachable). FanDuel {side} {r.line:g} ({int(price):+d})"
                body += " " + comp
                acts = fanduel.actions(dk_link, fd_link, best)
            except Exception as ex:
                acts = "view, Bet on FanDuel, https://sportsbook.fanduel.com/navigation/nba"; print("props alert links failed:", type(ex).__name__, str(ex)[:100])
            try: sent = push(title, body, acts)
            except Exception as e: sent = False; print("push failed:", e)
            rows.append(dict(key=key, date=TODAY, logged_at_et=NOW.strftime("%Y-%m-%d %H:%M"), model_version=PO["version"], tier=f"provisional_{r.tier}",
                             book="FanDuel", game=r.game, tip_et=r.tip_et, player=r.player, name=r.name, team=r.team, stat=r.stat, side=side,
                             line=r.line, price=int(price), open_seen_et=r.seen_at_et_open, mu=round(mu, 2), p_model=round(pm, 4), p_market=round(pk, 4),
                             p=round(ps, 4), ev=round(ev, 4), units=1, pushed=sent, result="", actual="", u="", close_line="", close_price="",
                             close_other="", close_ev=""))
    if rows: pd.DataFrame(rows).to_csv(LIVE, mode="a", header=not os.path.exists(LIVE), index=False)
    print(f"props live: {len(rows)} PROVISIONAL prop alerts {pd.Series([x['tier'] for x in rows]).value_counts().to_dict() if rows else ''} ({sum(r['pushed'] for r in rows)} pushed) from {len(LS)} FanDuel lines at their opener")


def grade_my_props():
    """grade the props Jeffrey logged with 'Log a bet' (market: prop) from the box scores, at his own line, odds and stake"""
    path = os.path.join(W, "state", "my_bets.csv")
    if not os.path.exists(path): return
    B = pd.read_csv(path)
    if "market" not in B or not (B.market == "prop").any(): return
    files = sorted(glob.glob(os.path.join(W, "data", "player_stats", "season_*.csv.gz")))
    X = pd.read_csv(files[-1], dtype={"player_id": str}); X["name"] = X.player.map(norm)
    for c in ("result", "profit"):
        if c not in B: B[c] = np.nan
    B["result"] = B["result"].astype(object)
    for i, r in B[(B.market == "prop") & B.result.isna()].iterrows():
        b = X[(X.date == r.date) & (X.name == norm(r.player))]
        if b.empty: continue
        if float(b["min"].iloc[0]) <= 0: B.loc[i, ["result", "profit"]] = ["P", 0.0]; continue    # did not play = void, shown as a push
        a = float(b[r.stat].iloc[0]); v = (a - r.line) * (1 if r.side == "over" else -1)
        B.loc[i, "result"] = "W" if v > 0 else ("L" if v < 0 else "P")
        B.loc[i, "profit"] = round(r.stake * (100 / abs(r.odds) if r.odds < 0 else r.odds / 100), 2) if v > 0 else (-r.stake if v < 0 else 0.0)
    B.to_csv(path, index=False)


if __name__ == "__main__":
    if MODE == "grade":
        grade(); grade(LIVE, json.load(open(PO_PATH))); grade_my_props()
    else:
        {"snapshot": snapshot, "pick": pick, "live": live}[MODE]()
