"""
Edge statistics for the logged rules (one identical file in the NBA, NHL and NFL repos; the sport is detected from the model file).

  python edge_stats.py WORKDIR [--only boot|calib|pinnacle|book]

Writes to research/edge_stats/:
  bootstrap.csv         ROI (units per bet) and closing line value for every logged rule, with bootstrap ranges
  calibration_*.csv     predicted probability vs what happened (bins, plus Brier / log loss)
  pinnacle_clv_bets.csv one row per bet that has a Pinnacle closing price (see below)
  pinnacle_clv_summary.csv
  by_book.csv           bets, units, ROI and CLV per sportsbook (state/my_bets.csv), and book_limits.csv events with the bets placed before each
  REPORT.md             all of the above in one page

What counts as a rule (every group below gets its own row):
  scorecard   state/picks_log*.csv, the bets the scorecard rule makes at the OPENING line (NBA/NFL: edge >= EDGE_MIN pts at
              -110; NHL: EV >= 6% at the opening price), split into all games and live-only (not backfilled)
  alerts      state/alerts.csv, first alert per game/market/side, BET alerts apart from caution / DON'T BET alerts
  my bets     state/my_bets.csv through state/bet_record.csv, one rule per model version (and ALL)

Bootstrap: 10,000 resamples of the bets (percentile 90% range), and a second range that resamples whole game days, because
bets on one night share luck. A range that includes zero means the record so far cannot be told from no edge.

Pinnacle closing line value in price terms: the closing Pinnacle price is the last snapshot before the game starts from
research/live_odds (The Odds API recorder, written by the NBA repo; this script reads the local copy, a sibling nba-mixed-model
folder, or the public GitHub copy). It exists only from Nov 2, 2026; older Pinnacle closes in data/odds_history are lines only.
  fair close   Pinnacle's no-vig chance for the side bet, from its two prices at the closing line.
  If the bet line differs from Pinnacle's closing line (NBA/NFL spreads and totals), the fair chance is moved to the bet line
  with the model's own backtest misses (data/poly_residuals.json, the same distribution the Polymarket tracker uses, so the
  NFL key numbers 3 and 7 are included). NHL bets at a different line than Pinnacle's close keep points CLV only.
  price CLV %  = fair close chance x bet decimal odds - 1  (the bet's expected value if Pinnacle's close is the truth;
                 negative when you paid the usual vig at the same line, so compare it with zero, not with a +EV target)
  win-% pts    = fair close chance - the bet's break-even chance
  points CLV   = how many points better than Pinnacle's closing line the bet was (spreads and totals)
"""
import os, sys, json, math, io, glob, urllib.request, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

FLAGS = [a for a in sys.argv[1:] if a.startswith("--")]
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
W = os.path.abspath(ARGS[0]) if ARGS else os.getcwd()
sys.argv = [sys.argv[0], W]                       # polymarket.py reads WORKDIR from argv[1]
sys.path.insert(0, W)
import books                                       # one spelling per sportsbook
import polymarket as pm                            # team names, miss distributions, price helpers (same file in all three repos)

SPORT, STATE, RESEARCH = pm.SPORT, pm.STATE, pm.RESEARCH
OUT = os.path.join(RESEARCH, "edge_stats")
ET = ZoneInfo("America/New_York")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))

# ----------------------------------------------------------------------------------------------- settings
N_BOOT = 10000
SEED = 7
CI = (5, 95)                         # 90% range
EDGE_MIN = 3.0                       # NBA / NFL scorecard rule: opening line this many points from the locked model
EV_MIN = 0.06                        # NHL scorecard rule
MIN_N_NOTE = 30                      # below this the range is shown but flagged
CLOSE_MAX_MIN = 60                   # Pinnacle snapshot must be within this many minutes of the start to count as the close
ODDS_RAW = "https://raw.githubusercontent.com/JeffreyD24/nba-mixed-model/main/research/live_odds/{sport}/{file}"
WIN_110 = 100 / 110
CLV_UNIT = {"nba": "points", "nfl": "points", "nhl": "win-prob (fraction)"}[SPORT]
BCOLS = ["source", "rule", "date", "home", "away", "market", "pick", "line", "price", "live", "result", "units", "clv", "p"]


def rd(path, **kw):
    try:
        return pd.read_csv(path, **kw) if os.path.exists(path) else pd.DataFrame()
    except Exception as e:
        print(f"could not read {path}: {type(e).__name__}"); return pd.DataFrame()


def col(df, name, default=np.nan):
    return df[name] if name in df else pd.Series(default, index=df.index)


def num(s): return pd.to_numeric(s, errors="coerce")


def pts_units(res): return res.map({"W": WIN_110, "L": -1.0, "P": 0.0})


def clv_points(market, pick, line, close_home_line, close_total):
    """points better than the DraftKings close: bet line minus close line for the same side (spreads), or the total's move"""
    if market == "spread":
        cl = close_home_line if pick == "home" else -close_home_line
        return line - cl
    if market == "total":
        return (close_total - line) if pick == "over" else (line - close_total)
    return np.nan


# ----------------------------------------------------------------------------------------------- 1. every logged bet
def scorecard_points(graded=True):
    f_models = os.path.join(STATE, "picks_log_models.csv")
    if SPORT == "nba" and os.path.exists(f_models):      # NBA runs three models side by side
        D = rd(f_models); D["label"] = "Model " + D.model.astype(str)
    else:
        D = rd(os.path.join(STATE, "picks_log.csv")); D["label"] = "model"
    rows = []
    for market in ("spread", "total"):
        e, b, r = num(col(D, f"open_{market}_edge")), col(D, f"open_{market}_bet"), col(D, f"open_{market}_result")
        sel = (e >= EDGE_MIN) & b.notna() & (r.isin(["W", "L", "P"]) if graded else True)
        d = D[sel]
        for i, x in d.iterrows():
            pick = x[f"open_{market}_bet"]
            line = float(x.open_spread) * (1 if pick == "home" else -1) if market == "spread" else float(x.open_total)
            clv = clv_points(market, pick, line, num(pd.Series([x.get("close_spread")])).iloc[0], num(pd.Series([x.get("close_total")])).iloc[0])
            rows.append(dict(source="scorecard", rule=f"{x.label} open {market} {EDGE_MIN:g}+ pts", date=x.date, home=x.home, away=x.away,
                             market=market, pick=pick if market == "total" else (x.home if pick == "home" else x.away), line=line, price=-110.0,
                             live=(x.pick_type == "live"), result=x[f"open_{market}_result"], units=pts_units(pd.Series([x[f"open_{market}_result"]])).iloc[0],
                             clv=clv, p=np.nan))
    return pd.DataFrame(rows, columns=BCOLS)


def scorecard_nhl(graded=True):
    rows = []
    for fn, model in (("picks_log.csv", "goals"), ("picks_log_xg.csv", "shot")):
        D = rd(os.path.join(STATE, fn))
        if D.empty: continue
        for market in ("moneyline", "puck line", "total"):
            p = f"open_{market}_"
            if p + "bet" not in D: continue
            sel = D[p + "bet"].notna() & num(D[p + "ev"]).ge(EV_MIN) & (D[p + "result"].isin(["W", "L", "P"]) if graded else True)
            for _, x in D[sel].iterrows():
                side = x[p + "bet"]
                pick = side if market == "total" else (x.home if side == "home" else x.away)
                rows.append(dict(source="scorecard", rule=f"{model} open {market} EV>={EV_MIN:.0%}" + (" (not in rule)" if market == "total" else ""),
                                 date=x.date, home=x.home, away=x.away, market=market, pick=pick, line=x[p + "line"], price=x[p + "price"],
                                 live=(x.pick_type == "live"), result=x[p + "result"], units=x[p + "profit"], clv=x[p + "clv"], p=x[p + "p"]))
    return pd.DataFrame(rows, columns=BCOLS)


def alerts_frame(graded=True):
    A = rd(os.path.join(STATE, "alerts.csv"))
    if A.empty: return pd.DataFrame(columns=BCOLS)
    A = (A[A.result.isin(["W", "L", "P"])] if graded else A).copy()
    A["kind"] = np.where(A.skipped.isna() & col(A, "verdict").isna(), "BET", "caution / DON'T BET")
    keys = ["game_id", "market", "side", "kind"] + (["model"] if SPORT == "nhl" else [])        # NBA/NFL `model` is the model's number, not a label
    A = A.sort_values("alerted_at_et").drop_duplicates(keys)                                   # first alert of each kind per game/market/side
    rows = []
    for _, x in A.iterrows():
        mdl = (str(x.get("model")) + " ") if SPORT == "nhl" else ""
        side = x.side
        pick = side if side in ("over", "under") else (x.home if side == "home" else x.away)
        line = num(pd.Series([x.line])).iloc[0]
        if SPORT != "nhl" and x.market == "spread" and side == "away": line = -line               # NBA/NFL alerts store the HOME team's line
        price = float(x.price) if "price" in x and pd.notna(x.get("price")) else -110.0
        units = x.profit if "profit" in x and pd.notna(x.get("profit")) else pts_units(pd.Series([x.result])).iloc[0]
        clv = x.clv if "clv" in x else x.get("clv_points", np.nan)
        rows.append(dict(source="alerts", rule=f"{mdl}alert {x.market} {x.kind}" + (" (opening price only)" if str(x.get("open_only")) == "True" else ""),
                         date=x.date, home=x.home, away=x.away, market=x.market, pick=pick, line=line, price=price, live=True,
                         result=x.result, units=units, clv=clv, p=x.get("model_prob", np.nan)))
    return pd.DataFrame(rows, columns=BCOLS)


def my_bets_frame(graded=True):
    R = rd(os.path.join(STATE, "bet_record.csv")); B = rd(os.path.join(STATE, "my_bets.csv"))
    if R.empty or B.empty: return pd.DataFrame(columns=BCOLS)
    clvcol = "clv_points" if "clv_points" in B else ("clv" if "clv" in B else None)
    pcol = "model_prob" if "model_prob" in B else None
    B = B.set_index(num(B.issue))
    rows = []
    for _, x in R.iterrows():
        if graded and x.status not in ("W", "L", "P"): continue
        b = B.loc[num(pd.Series([x.issue])).iloc[0]] if pd.notna(x.issue) and num(pd.Series([x.issue])).iloc[0] in B.index else None
        rows.append(dict(source="my bets", rule=x.version, date=x.date, home=x.home, away=x.away, market=x.market, pick=x.pick, line=x.line,
                         price=x.odds, live=True, result=x.status, units=x.units,
                         clv=(b[clvcol] if b is not None and clvcol else np.nan), p=(b[pcol] if b is not None and pcol else np.nan)))
    out = pd.DataFrame(rows, columns=BCOLS)
    if len(out):
        allb = out.copy(); allb["rule"] = "ALL logged bets"; out = pd.concat([out, allb], ignore_index=True)
    return out


def all_bets(graded=True):
    """graded=False keeps bets without a result yet (the Pinnacle close needs only that the game has started)"""
    parts = [scorecard_nhl(graded) if SPORT == "nhl" else scorecard_points(graded), alerts_frame(graded), my_bets_frame(graded)]
    B = pd.concat([p for p in parts if len(p)], ignore_index=True)
    B["units"], B["clv"] = num(B.units), num(B.clv)
    return B


# ----------------------------------------------------------------------------------------------- 2. bootstrap
def boot_mean(x, days=None, rng=None):
    """mean of x with a percentile range from resampling bets; if days is given, also resampling whole days"""
    x = np.asarray(x, float); n = len(x)
    if n == 0: return dict(mean=np.nan, lo=np.nan, hi=np.nan, p_pos=np.nan, lo_day=np.nan, hi_day=np.nan)
    iid = x[rng.integers(0, n, (N_BOOT, n))].mean(axis=1)
    out = dict(mean=x.mean(), lo=np.percentile(iid, CI[0]), hi=np.percentile(iid, CI[1]), p_pos=(iid > 0).mean())
    if days is not None and len(set(days)) > 1:
        u, inv = np.unique(days, return_inverse=True)
        s, c = np.bincount(inv, weights=x), np.bincount(inv).astype(float)
        idx = rng.integers(0, len(u), (N_BOOT, len(u)))
        m = s[idx].sum(axis=1) / c[idx].sum(axis=1)
        out.update(lo_day=np.percentile(m, CI[0]), hi_day=np.percentile(m, CI[1]))
    else:
        out.update(lo_day=np.nan, hi_day=np.nan)
    return out


def bootstrap_table(B):
    rng = np.random.default_rng(SEED); rows = []
    for (source, rule), g in B.groupby(["source", "rule"], sort=False):
        for scope, d in (("all", g), ("live only", g[g.live.astype(bool)])):
            if scope == "live only" and (len(d) == 0 or len(d) == len(g)): continue
            u = d.units.dropna(); days = d.loc[u.index, "date"].astype(str).values
            r = boot_mean(u.values, days, rng)
            c = d.clv.dropna(); rc = boot_mean(c.values, d.loc[c.index, "date"].astype(str).values, rng)
            rows.append(dict(source=source, rule=rule, scope=scope, n=len(u), W=int((d.result == "W").sum()), L=int((d.result == "L").sum()),
                             P=int((d.result == "P").sum()), units=round(u.sum(), 2), roi=r["mean"], roi_lo90=r["lo"], roi_hi90=r["hi"],
                             roi_lo90_by_day=r["lo_day"], roi_hi90_by_day=r["hi_day"], p_roi_above_0=r["p_pos"],
                             clv_n=len(c), clv_mean=rc["mean"], clv_lo90=rc["lo"], clv_hi90=rc["hi"], clv_share_positive=(c > 0).mean() if len(c) else np.nan,
                             clv_unit=CLV_UNIT, note=("n<%d: too few bets to read" % MIN_N_NOTE) if len(u) < MIN_N_NOTE else ""))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- 3. calibration
def cal_table(p, y, bins, label):
    p, y = np.asarray(p, float), np.asarray(y, float); ok = ~(np.isnan(p) | np.isnan(y)); p, y = p[ok], y[ok]
    rows = []
    if len(p) == 0: return pd.DataFrame()
    cut = pd.cut(p, bins, include_lowest=True)
    for iv in cut.categories:
        m = cut == iv; n = int(m.sum())
        if n == 0: continue
        pr, rate = p[m].mean(), y[m].mean(); se = math.sqrt(max(pr * (1 - pr), 1e-9) / n)
        rows.append(dict(set=label, bin=str(iv), n=n, predicted=pr, actual=rate, diff=rate - pr, z=(rate - pr) / se))
    pc = np.clip(p, 1e-4, 1 - 1e-4)
    rows.append(dict(set=label, bin="ALL", n=len(p), predicted=p.mean(), actual=y.mean(), diff=y.mean() - p.mean(),
                     z=(y.mean() - p.mean()) / math.sqrt(p.mean() * (1 - p.mean()) / len(p)),
                     brier=((p - y) ** 2).mean(), logloss=-(y * np.log(pc) + (1 - y) * np.log(1 - pc)).mean()))
    return pd.DataFrame(rows)


def calibration_nhl():
    out = {}; games, bets, bands = [], [], []
    for fn, model in (("picks_log.csv", "goals"), ("picks_log_xg.csv", "shot")):
        D = rd(os.path.join(STATE, fn))
        if D.empty: continue
        g = D[num(D.home_goals).notna() & num(D.p_home_win).notna()]
        games.append(cal_table(g.p_home_win, (num(g.home_goals) > num(g.away_goals)).astype(float),
                               [0, .35, .45, .5, .55, .65, 1], f"{model}: home win chance, all games"))
        m = D[D.open_moneyline_result.isin(["W", "L"]) & num(D.open_moneyline_p).notna()]
        bets.append(cal_table(m.open_moneyline_p, (m.open_moneyline_result == "W").astype(float), [0, .35, .45, .5, .55, .65, 1],
                              f"{model}: higher-EV side of every game (not only rule bets)"))
        price = num(m.open_moneyline_price)
        band = pd.cut(price, [-1e4, -150, 99, 149, 249, 1e4], labels=["-150 or shorter", "-149..+99", "+100..+149", "+150..+249", "+250 or longer"])
        for b in band.cat.categories:
            s = m[band == b]
            if len(s) == 0: continue
            pr, rate = num(s.open_moneyline_p).mean(), (s.open_moneyline_result == "W").mean()
            bands.append(dict(set=f"{model}: higher-EV side of every game, by price band", bin=b, n=len(s), predicted=pr, actual=rate, diff=rate - pr,
                              z=(rate - pr) / math.sqrt(pr * (1 - pr) / len(s)), units=num(s.open_moneyline_profit).sum()))
    out["games"], out["bets"], out["price_bands"] = (pd.concat(x, ignore_index=True) if len(x) else pd.DataFrame() for x in (games, bets, [pd.DataFrame(bands)] if bands else []))
    return out


def calibration_points():
    D = rd(os.path.join(STATE, "picks_log.csv"))
    if D.empty: return {}
    rm, rt = pm.residuals(); prob = pm.points_prob
    rows_s, rows_t = [], []
    for _, x in D.iterrows():
        if pd.isna(x.home_pts) or pd.isna(x.pred_margin): continue
        f = prob(float(x.pred_margin), float(x.pred_total), (rm, rt))
        margin, tot = x.home_pts - x.away_pts, x.home_pts + x.away_pts
        if pd.notna(x.open_spread):
            r = f("spread", "home", float(x.open_spread))
            if r and margin + x.open_spread != 0: rows_s.append((r[0], float(margin + x.open_spread > 0), x.pick_type))
        if pd.notna(x.open_total):
            r = f("total", "over", float(x.open_total))
            if r and tot != x.open_total: rows_t.append((r[0], float(tot > x.open_total), x.pick_type))
    out = {}
    for name, rows in (("spread_home_cover", rows_s), ("total_over", rows_t)):
        if not rows: continue
        a = pd.DataFrame(rows, columns=["p", "y", "pick_type"]); bins = [0, .4, .45, .5, .55, .6, 1]
        t = [cal_table(a.p, a.y, bins, f"{name}: all games")]
        if (a.pick_type == "live").any(): t.append(cal_table(a.p[a.pick_type == "live"], a.y[a.pick_type == "live"], bins, f"{name}: live only"))
        out[name] = pd.concat(t, ignore_index=True)
    return out


# ----------------------------------------------------------------------------------------------- 4. Pinnacle closing price
def odds_file(day):
    if pd.Timestamp(day) > pd.Timestamp.now(tz="UTC").tz_localize(None).normalize(): return pd.DataFrame()      # no file for future days
    fn = f"{day}.csv.gz"
    for d in (os.path.join(RESEARCH, "live_odds", SPORT, fn), os.path.join(W, "..", "nba-mixed-model", "research", "live_odds", SPORT, fn)):
        if os.path.exists(d): return pd.read_csv(d)
    cache = os.path.join(OUT, "_cache"); os.makedirs(cache, exist_ok=True); c = os.path.join(cache, f"{SPORT}_{fn}")
    if not os.path.exists(c):
        try:
            with urllib.request.urlopen(ODDS_RAW.format(sport=SPORT, file=fn), timeout=60) as r: open(c, "wb").write(r.read())
        except Exception as e:
            print(f"no live odds file for {day} ({type(e).__name__})"); return pd.DataFrame()
    return pd.read_csv(c)


def pinnacle_closes(days):
    """{(date, home, away): {'h2h': {team: price}, 'spreads': {team: (point, price)}, 'totals': {'over': (pt, price), ...}, 'mins': minutes before start}}"""
    P = []
    for d in sorted(days):
        for k in (0, 1):                                   # a game's closing snapshots sit in that day's or the next UTC day's file
            f = odds_file((pd.Timestamp(d) + pd.Timedelta(days=k)).strftime("%Y-%m-%d"))
            if len(f): P.append(f[f.book == "pinnacle"])
    if not P: return {}
    P = pd.concat(P, ignore_index=True).drop_duplicates()
    P["snap"] = pd.to_datetime(P.snapshot_utc, utc=True)
    P["start"] = pd.to_datetime(P.commence_et).dt.tz_localize(ET, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    P = P[(P.snap <= P.start) & (P.start <= pd.Timestamp.now(tz="UTC"))]       # games that have started
    out = {}
    for (eid, mk), g in P.groupby(["event_id", "market"]):
        last = g[g.snap == g.snap.max()]
        h, a = pm.team_code(last.home.iloc[0]), pm.team_code(last.away.iloc[0])
        if not h or not a: continue
        key = (str(pd.Timestamp(last.commence_et.iloc[0]).date()), h, a)
        o = out.setdefault(key, {}); o["mins"] = max(o.get("mins", 0), (last.start.iloc[0] - last.snap.iloc[0]).total_seconds() / 60)
        if mk == "h2h":
            o["h2h"] = {pm.team_code(r.outcome): r.price for r in last.itertuples()}
        elif mk == "spreads":
            pts = {abs(r.point) for r in last.itertuples() if pd.notna(r.point)}
            if not pts: continue
            best = min(pts, key=lambda q: abs(last[last.point.abs() == q].price.max() - last[last.point.abs() == q].price.min()))
            o["spreads"] = {pm.team_code(r.outcome): (r.point, r.price) for r in last.itertuples() if pd.notna(r.point) and abs(r.point) == best}
        elif mk == "totals":
            pts = set(last.point.dropna())
            if not pts: continue
            best = min(pts, key=lambda q: abs(last[last.point == q].price.max() - last[last.point == q].price.min()))
            o["totals"] = {str(r.outcome).lower(): (r.point, r.price) for r in last.itertuples() if r.point == best}
    return out


def move_prob(p_fair, market, pick, pin_line, bet_line, res):
    """no-vig chance moved from Pinnacle's closing line to the bet line using the model's backtest misses (see module note)"""
    r = res[0] if market == "spread" else res[1]; n = len(r)
    cdf = lambda x: (np.searchsorted(r, x, side="left") + np.searchsorted(r, x, side="right")) / (2 * n)
    over = (market == "total" and pick == "over")
    f = (lambda L, c: 1 - cdf(L + c)) if over else (lambda L, c: cdf(L + c))
    lo, hi = -80.0, 80.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if (f(pin_line, mid) < p_fair) != over: lo = mid
        else: hi = mid
    return float(f(bet_line, (lo + hi) / 2))


def fair_close(close, market, pick, bet_line, res):
    """-> dict(pin_line, pts, fair, fair_at_bet, adjusted) for one bet, or None when Pinnacle has no matching price"""
    if market == "moneyline":
        h = close.get("h2h", {});
        if pick not in h or len(h) != 2: return None
        other = [v for k, v in h.items() if k != pick][0]
        return dict(pin_line=np.nan, pts=np.nan, fair=pm.fair_pair(h[pick], other), adjusted=False)
    if market in ("spread", "puck line"):
        s = close.get("spreads", {})
        if pick not in s or len(s) != 2: return None
        pt, pr = s[pick]; other = [v for k, v in s.items() if k != pick][0][1]
        return dict(pin_line=pt, pts=float(bet_line) - pt, fair=pm.fair_pair(pr, other), adjusted=float(bet_line) != pt)
    if market == "total":
        t = close.get("totals", {})
        if pick not in t or len(t) != 2: return None
        pt, pr = t[pick]; other = [v for k, v in t.items() if k != pick][0][1]
        pts = (pt - float(bet_line)) if pick == "over" else (float(bet_line) - pt)
        return dict(pin_line=pt, pts=pts, fair=pm.fair_pair(pr, other), adjusted=float(bet_line) != pt)
    return None


def pinnacle_table(B):
    B = B[B.price.notna() & B.line.notna() | (B.market == "moneyline")].copy()
    B = B[pd.to_datetime(B.date) >= pd.Timestamp("2026-11-02")]               # recorder start
    if B.empty: return pd.DataFrame(), pd.DataFrame()
    closes = pinnacle_closes(set(B.date.astype(str)))
    res = pm.residuals() if SPORT in ("nba", "nfl") else None
    rows = []
    for x in B.itertuples():
        c = closes.get((str(x.date), x.home, x.away))
        mk = "spread" if x.market == "puck line" else x.market
        if not c: continue
        r = fair_close(c, x.market, x.pick, x.line, res)
        if r is None: continue
        p_bet = r["fair"]; moved = False
        if r["adjusted"]:
            if res is not None and x.market in ("spread", "total"):
                p_bet = move_prob(r["fair"], mk, x.pick, r["pin_line"], float(x.line), res); moved = True
            else:
                p_bet = np.nan
        d = pm.dec(x.price)
        rows.append(dict(source=x.source, rule=x.rule, date=x.date, home=x.home, away=x.away, market=x.market, pick=x.pick, bet_line=x.line,
                         bet_price=x.price, pin_close_line=r["pin_line"], pin_fair_close=r["fair"], pin_fair_at_bet_line=p_bet, line_moved_by_model=moved,
                         points_clv=r["pts"], price_clv_pct=(p_bet * d - 1) if pd.notna(p_bet) and d == d else np.nan,
                         winpct_pts=((p_bet - 1 / d) * 100) if pd.notna(p_bet) and d == d else np.nan,
                         close_minutes_before=round(c["mins"]), units=x.units))
    T = pd.DataFrame(rows)
    if T.empty: return T, pd.DataFrame()
    T = T[T.close_minutes_before <= CLOSE_MAX_MIN]
    rng = np.random.default_rng(SEED); S = []
    for (source, rule, market), g in T.groupby(["source", "rule", "market"], sort=False):
        r = dict(source=source, rule=rule, market=market, n=len(g))
        for name in ("points_clv", "price_clv_pct", "winpct_pts"):
            v = g[name].dropna().values; b = boot_mean(v, None, rng)
            r.update({f"{name}_n": len(v), f"{name}_mean": b["mean"], f"{name}_lo90": b["lo"], f"{name}_hi90": b["hi"]})
        r["share_points_positive"] = (g.points_clv.dropna() > 0).mean() if g.points_clv.notna().any() else np.nan
        r["note"] = ("n<%d: too few bets to read" % MIN_N_NOTE) if len(g) < MIN_N_NOTE else ""
        S.append(r)
    return T, pd.DataFrame(S)



# ----------------------------------------------------------------------------------------------- 5. sportsbooks and limits
def book_tables():
    """-> (per-book results from my_bets, limit events from state/book_limits.csv with the bets placed at that book before each)"""
    B = rd(os.path.join(STATE, "my_bets.csv")); L = rd(os.path.join(STATE, "book_limits.csv"))
    byb = pd.DataFrame(); lim = pd.DataFrame()
    if len(B):
        B = B.copy(); B["book"] = col(B, "book").map(books.canon_book)
        R = rd(os.path.join(STATE, "bet_record.csv"))
        units = dict(zip(num(R.issue), num(R.units))) if len(R) else {}
        B["units"] = num(B.issue).map(units); B["stake"] = num(B.stake)
        B["clv"] = num(col(B, "clv_points" if "clv_points" in B else "clv"))
        rng = np.random.default_rng(SEED); rows = []
        for book, g in B.groupby("book", sort=False):
            u = g.units.dropna(); r = boot_mean(u.values, None, rng) if len(u) else dict(mean=np.nan, lo=np.nan, hi=np.nan)
            rows.append(dict(book=book, bets=len(g), graded=len(u), stake_units=g.stake.sum(), units=round(u.sum(), 2), roi=r["mean"], roi_lo90=r["lo"], roi_hi90=r["hi"],
                             clv_mean=g.clv.mean(), clv_n=int(g.clv.notna().sum()), first_bet=str(pd.to_datetime(g.logged_at_et).min())[:10],
                             last_bet=str(pd.to_datetime(g.logged_at_et).max())[:10],
                             note=("n<%d: too few bets to read" % MIN_N_NOTE) if len(u) < MIN_N_NOTE else ""))
        byb = pd.DataFrame(rows).sort_values("bets", ascending=False)
        if len(L):
            L = L.copy(); L["book"] = L.book.map(books.canon_book); rows = []
            for x in L.itertuples():
                prior = B[(B.book == x.book) & (pd.to_datetime(B.logged_at_et) < pd.Timestamp(x.date) + pd.Timedelta(days=1))]
                rows.append(dict(date=x.date, book=x.book, event=x.event, max_bet_before=x.max_bet_before, max_bet_after=x.max_bet_after,
                                 stake_tried=x.stake_tried, market=x.market, bets_logged_at_book_before=len(prior),
                                 units_staked_before=prior.stake.sum(), units_won_before=prior.units.sum(), notes=x.notes))
            lim = pd.DataFrame(rows)
    elif len(L):
        lim = L
    return byb, lim

# ----------------------------------------------------------------------------------------------- 6. report
def md(df, fmt=None):
    if df is None or len(df) == 0: return "_no rows yet_\n"
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f": d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.3f}" if abs(v) < 10 else f"{v:.1f}")
    return "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns) + "\n" + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in d.values) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    only = FLAGS[FLAGS.index("--only") + 1] if "--only" in FLAGS and FLAGS.index("--only") + 1 < len(FLAGS) else None
    only = only or next((a for a in ARGS[1:] if a in ("boot", "calib", "pinnacle", "book")), None)
    L = [f"# Edge statistics ({SPORT.upper()}), made {NOW:%Y-%m-%d %H:%M} ET", ""]
    B = all_bets()
    if only in (None, "boot"):
        T = bootstrap_table(B); T.to_csv(os.path.join(OUT, "bootstrap.csv"), index=False)
        L += ["## ROI and closing line value with bootstrap ranges", "",
              f"ROI = units won per bet (each bet 1 unit; scorecard NBA/NFL bets at -110). 90% ranges from {N_BOOT:,} resamples; `by_day` resamples whole days. "
              f"CLV is in {CLV_UNIT} against DraftKings' close (as logged); Pinnacle price CLV is below.", "",
              md(T[["source", "rule", "scope", "n", "W", "L", "P", "units", "roi", "roi_lo90", "roi_hi90", "roi_lo90_by_day", "roi_hi90_by_day",
                    "p_roi_above_0", "clv_n", "clv_mean", "clv_lo90", "clv_hi90", "note"]]), ""]
    if only in (None, "calib"):
        L += ["## Calibration: predicted chance vs what happened", ""]
        C = calibration_nhl() if SPORT == "nhl" else calibration_points()
        for k, v in C.items():
            if len(v):
                v.to_csv(os.path.join(OUT, f"calibration_{k}.csv"), index=False)
                L += [f"### {k}", "", "`z` is (actual - predicted) in standard errors; |z| above 2 is worth a look, and below 30 bets per bin it is mostly noise.", "", md(v), ""]
    if only in (None, "pinnacle"):
        T, S = pinnacle_table(all_bets(graded=False))
        T.to_csv(os.path.join(OUT, "pinnacle_clv_bets.csv"), index=False); S.to_csv(os.path.join(OUT, "pinnacle_clv_summary.csv"), index=False)
        L += ["## CLV against Pinnacle's closing price (games from Nov 2, 2026; live recorder only)", "",
              "price_clv_pct = fair Pinnacle close x bet decimal odds - 1 (negative = paid the usual vig at the same line; zero or above = beat the close). "
              "winpct_pts = fair close chance - break-even chance. points_clv = points better than Pinnacle's closing line.", "",
              md(S), ""]
    if only in (None, "book"):
        byb, lim = book_tables(); byb.to_csv(os.path.join(OUT, "by_book.csv"), index=False)
        if len(lim) or os.path.exists(os.path.join(STATE, "book_limits.csv")): lim.to_csv(os.path.join(OUT, "book_limits.csv"), index=False)
        L += ["## By sportsbook (bets logged through `Log a bet`)", "",
              "Book names are normalized (dk / DraftKings are one book). `(not recorded)` means the form's Sportsbook field was blank.", "", md(byb), "",
              "### Limit events (`Log a limit` form, state/book_limits.csv)", "",
              "`bets_logged_at_book_before` counts logged bets at that book up to the end of that day, so a cut can be read against how much was bet and won first.", "", md(lim), ""]
    open(os.path.join(OUT, "REPORT.md"), "w").write("\n".join(L))
    print(f"Wrote research/edge_stats/REPORT.md ({len(B)} bets)")


if __name__ == "__main__":
    main()
