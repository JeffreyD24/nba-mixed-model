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
NOW = dt.datetime.now(ET); TODAY = NOW.strftime("%Y-%m-%d")


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
        if tip.strftime("%Y-%m-%d") != TODAY or tip < pd.Timestamp(NOW): continue
        away, home = [FULL.get(x.strip()) for x in e["name"].split(" @ ")]
        for tab, stat in FD_TABS.items():
            try: p = get(f"{BASE}/event-page?_ak={AK}&eventId={e['eventId']}&tab={tab}&timezone=America%2FNew_York")
            except Exception as ex: print(f"{e['name']} {tab}: {ex}"); continue
            for m in p.get("attachments", {}).get("markets", {}).values():
                if not FD_TYPE.match(m.get("marketType", "")) or len(m.get("runners", [])) != 2: continue
                r = {x.get("result", {}).get("type"): x for x in m["runners"]}
                if "OVER" not in r or "UNDER" not in r: continue
                o, u = r["OVER"], r["UNDER"]
                odds = lambda x: (x.get("winRunnerOdds") or {}).get("americanDisplayOdds", {}).get("americanOdds")
                rows.append(dict(seen_at_et=NOW.strftime("%Y-%m-%d %H:%M"), date=TODAY, event_id=e["eventId"], tip_et=tip.strftime("%Y-%m-%d %H:%M"),
                                 game=e["name"], home=home, away=away, stat=stat, player=m["marketName"].split(" - ")[0], name=norm(m["marketName"].split(" - ")[0]),
                                 line=o.get("handicap"), over=odds(o), under=odds(u), team_abbr=o.get("teamAbbr")))
    path = os.path.join(W, "research", "props_fd", f"{TODAY}.csv"); os.makedirs(os.path.dirname(path), exist_ok=True)
    new = pd.DataFrame(rows)
    if new.empty: print("no FanDuel prop lines right now"); return
    if os.path.exists(path):
        old = pd.read_csv(path); last = old.sort_values("seen_at_et").drop_duplicates(["event_id", "stat", "name"], keep="last")
        m = new.merge(last[["event_id", "stat", "name", "line", "over", "under"]], on=["event_id", "stat", "name"], how="left", suffixes=("", "_old"))
        new = new[~((m.line == m.line_old) & (m.over == m.over_old) & (m.under == m.under_old)).values]
        pd.concat([old, new], ignore_index=True).to_csv(path, index=False)
    else:
        new.to_csv(path, index=False)
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
        row = dict(player_id=pid, player=g.player.iloc[-1], name=norm(g.player.iloc[-1]), team=g.team.iloc[-1], n_prev=len(g),
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


def p_over(mu, stat, line):
    a, b = P["var_ab"][stat]; ex = (a - 1) * mu + b * mu ** 2
    r = mu ** 2 / ex if ex > 1e-6 else 1e6
    return float(1 - stats.nbinom.cdf(np.floor(line), r, r / (r + mu)))


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


def grade():
    if not os.path.exists(SHADOW): print("no shadow record yet"); return
    D = pd.read_csv(SHADOW, dtype=str)
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
                    a_, b_ = P["var_ab"][r.stat]; mu = float(r.mu); sd = np.sqrt(max(a_ * mu + b_ * mu ** 2, mu))
                    m = float(c.line) + sd * stats.norm.ppf(min(max(fo, 0.01), 0.99)); fo = float(1 - stats.norm.cdf((line - m) / sd))
                side_p = fo if r.side == "over" else 1 - fo
                D.loc[i, ["close_line", "close_price", "close_other"]] = [c.line, c.over if r.side == "over" else c.under, c.under if r.side == "over" else c.over]
                D.loc[i, "close_ev"] = round(side_p * float(dec(price)) - 1, 4)
        n += 1
    D.to_csv(SHADOW, index=False)
    g = D[D.result.isin(["win", "loss", "push"])]
    if len(g):
        u = g.u.astype(float); ce = pd.to_numeric(g.close_ev, errors="coerce")
        print(f"props shadow graded {n}; record {(g.result == 'win').sum()}-{(g.result == 'loss').sum()}-{(g.result == 'push').sum()}, "
              f"{u.sum():+.1f}u, closing-line EV {ce.mean()*100:+.2f}% (n {ce.notna().sum()})")


if __name__ == "__main__":
    {"snapshot": snapshot, "pick": pick, "grade": grade}[MODE]()
