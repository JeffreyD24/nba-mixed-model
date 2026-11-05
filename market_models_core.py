"""Shared code for the market models (research/MARKET_MODELS_PLAN.md), used by the research scripts and the live alert
(market_models_live.py), so live features are computed exactly as in the backtests.

  build_games(odds_files, results)  one row per game: each book's first-seen and close total (The Odds API snapshots) and
                                     features known before the line was first seen (box-score pace/efficiency, recent DK
                                     closes, league scoring level, rest, previous opener errors). Games without a final score
                                     (not played yet) get features from all earlier games; `ready` says whether both teams'
                                     previous games are in the box scores (otherwise the features are a game stale).
  fit_opener / opener_pred          the step-2 opener model: linear + shrunk team-by-season effects (BLUP), NO injury inputs
                                     (the night-before report is not out when many lines first appear).
  snapshot_panel(odds_rows, games)  step-3 movement features: every book's quote at the same snapshot.
  tree_predict(model, X)             numpy evaluation of the exported boosted-tree movement model (no scikit-learn needed).
"""
import numpy as np, pandas as pd

NAME = {"Atlanta Hawks": "atl", "Brooklyn Nets": "bkn", "Boston Celtics": "bos", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
        "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
        "Golden State Warriors": "gs", "Houston Rockets": "hou", "Indiana Pacers": "ind", "Los Angeles Clippers": "lac", "LA Clippers": "lac",
        "Los Angeles Lakers": "lal", "Memphis Grizzlies": "mem", "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min",
        "New Orleans Pelicans": "no", "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl",
        "Philadelphia 76ers": "phi", "Phoenix Suns": "phx", "Portland Trail Blazers": "por", "San Antonio Spurs": "sa",
        "Sacramento Kings": "sac", "Toronto Raptors": "tor", "Utah Jazz": "utah", "Washington Wizards": "wsh"}
COLS = ["snapshot_utc", "event_id", "commence_et", "home", "away", "book", "market", "outcome", "price", "point"]
HL = 12  # team stats half-life, games

# opener model inputs (step 2, without the injury report); the last one is added per book: log(1 + hours before tip first seen)
OPENER_BASE = ["fund_total", "mkt_total", "league_lvl", "exp_pace", "h_e_ortg", "h_e_drtg", "a_e_ortg", "a_e_drtg",
               "h_e_pace", "a_e_pace", "h_operr", "a_operr", "h_opmv", "a_opmv", "h_rest", "a_rest", "b2b_h", "b2b_a",
               "gp_min", "month"]
OPENER_LAM = 20.0
# movement model inputs (step 3), in this order
MOVE_FEAT = ["log_lead", "move_so_far", "pin_gap", "fd_gap", "cons_gap", "n_books", "lean_draftkings", "lean_pinnacle",
             "dk_oresid", "opener_view", "pin_present"]
# Action Network-compatible variant "movement v1-an" (Nov 5, 2026): no Pinnacle (the free feed doesn't carry it); books both
# the history (The Odds API) and Action Network have. AN names: DraftKings, FanDuel, Caesars (= williamhill_us), BetMGM, BetRivers.
MOVE_FEAT_AN = ["log_lead", "move_so_far", "fd_gap", "cons_gap", "n_books", "lean_draftkings", "dk_oresid", "opener_view"]
AN_BOOKS = ("draftkings", "fanduel", "williamhill_us", "betmgm", "betrivers")
AN_NAME = {"DraftKings": "draftkings", "FanDuel": "fanduel", "Caesars": "williamhill_us", "BetMGM": "betmgm", "BetRivers": "betrivers"}


def season_of(t):
    t = pd.Timestamp(t); return t.year + 1 if t.month >= 8 else t.year


def read_odds(files):
    return pd.concat([pd.read_csv(f, usecols=COLS) for f in files], ignore_index=True)


def first_close(d, books=("draftkings", "pinnacle", "fanduel")):
    """per game: each book's first-seen total (+ prices, hours before tip) and its last pre-tip total"""
    d = d[(d.market == "totals") & d.book.isin(books)].copy()
    d["snap"] = pd.to_datetime(d.snapshot_utc).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d["tip"] = pd.to_datetime(d.commence_et)
    d["lead_h"] = (d.tip - d.snap).dt.total_seconds() / 3600
    d = d[d.lead_h > 0]
    ov = d[d.outcome == "Over"][["event_id", "book", "snap", "lead_h", "point", "price"]].rename(columns={"price": "over_px"})
    un = d[d.outcome == "Under"][["event_id", "book", "snap", "price"]].rename(columns={"price": "under_px"})
    x = ov.merge(un, on=["event_id", "book", "snap"], how="left").sort_values("snap")
    # one game can have two API event IDs (an early one, then a replacement): merge by date + teams
    ev = d.drop_duplicates("event_id").set_index("event_id")
    key = ev.tip.dt.strftime("%Y-%m-%d") + "|" + ev.home + "|" + ev.away
    main_id = ev.assign(k=key).sort_values("tip").groupby("k").apply(lambda z: z.index[-1])
    x["event_id"] = x.event_id.map(key).map(main_id)
    x = x.sort_values("snap")
    g = x.groupby(["event_id", "book"])
    first = g.first()[["lead_h", "point", "over_px", "under_px"]].add_prefix("open_")
    last = g.last()[["lead_h", "point"]].rename(columns={"lead_h": "close_lead_h", "point": "close_point"})
    wide = first.join(last).reset_index().pivot(index="event_id", columns="book")
    wide.columns = [f"{b[:2]}_{c}" for c, b in wide.columns]
    wide = wide.rename(columns=lambda c: c.replace("dr_", "dk_").replace("pi_", "pin_").replace("fa_", "fd_"))
    games = ev.loc[main_id.values, ["tip", "home", "away"]].join(wide).reset_index()
    games["home"] = games.home.map(NAME); games["away"] = games.away.map(NAME)
    games["date"] = games.tip.dt.strftime("%Y-%m-%d")
    return games.dropna(subset=["home", "away"])


def build_games(games, ps, results, inj=None, live_from="2026-10-01"):
    """games: first_close() output (plus any extra rows: date, tip, home, away, dk_open_point, dk_close_point ...).
    ps: player box rows (data/player_stats). results: date, home, away, home_pts, away_pts (NaN = not played).
    inj: optional table with *_open injury columns (research only). Returns one row per game with features."""
    ps = ps.drop_duplicates(["game_id", "player_id"])   # some games have every player row twice
    tg = ps.groupby(["game_id", "date", "season", "team", "home"])[["pts", "fga", "oreb", "tov", "fta"]].sum().reset_index()
    tg["poss"] = tg.fga - tg.oreb + tg.tov + 0.44 * tg.fta
    opp = tg[["game_id", "team", "pts", "poss"]].rename(columns={"team": "opp", "pts": "opp_pts", "poss": "opp_poss"})
    tg = tg.merge(opp, on="game_id"); tg = tg[tg.team != tg.opp]
    tg["pace"] = (tg.poss + tg.opp_poss) / 2
    tg["ortg"] = 100 * tg.pts / tg.pace; tg["drtg"] = 100 * tg.opp_pts / tg.pace
    tg["tot"] = tg.pts + tg.opp_pts
    tg["placeholder"] = 0
    sc = pd.concat([results[["date", "home", "home_pts"]].rename(columns={"home": "team", "home_pts": "off_pts"}),
                    results[["date", "away", "away_pts"]].rename(columns={"away": "team", "away_pts": "off_pts"})])
    tg = tg.merge(sc, on=["date", "team"], how="left")
    bad = (tg.off_pts.notna() & (tg.off_pts != tg.pts)) | (tg.tot < 160)
    tg.loc[bad, ["pace", "ortg", "drtg", "pts", "opp_pts", "tot"]] = np.nan
    # live: games scheduled or played since live_from with no box score yet -> placeholder rows (no stats), so rest days and
    # "previous game" are right; a game whose team's previous game is a placeholder is not ready
    sched = pd.concat([results[["date", "home"]].rename(columns={"home": "team"}), results[["date", "away"]].rename(columns={"away": "team"})])
    sched = sched[sched.date >= live_from]
    have = set(zip(tg.date, tg.team))
    ph = sched[[(a, b) not in have for a, b in zip(sched.date, sched.team)]].drop_duplicates()
    if len(ph):
        ph = ph.assign(season=[season_of(x) for x in ph.date], placeholder=1, game_id=-1, home=np.nan)
        tg = pd.concat([tg, ph], ignore_index=True)
    tg = tg.sort_values(["team", "date"])

    def pre_ewm(col):
        return tg.groupby("team")[col].transform(lambda s: s.ewm(halflife=HL, min_periods=1, ignore_na=True).mean().shift(1))
    for c, v in zip(["pace", "ortg", "drtg", "pts", "opp_pts"], ["pace", "ortg", "drtg", "pf", "pa"]):
        tg[f"e_{v}"] = pre_ewm(c)
    tg["prev_date"] = tg.groupby("team").date.shift(1)
    tg["prev_ph"] = tg.groupby("team").placeholder.shift(1).fillna(0)
    tg["rest"] = (pd.to_datetime(tg.date) - pd.to_datetime(tg.prev_date)).dt.days.clip(upper=5)
    tg["gp_season"] = tg.groupby(["team", "season"]).cumcount()
    team_feat = tg[["date", "team", "e_pace", "e_ortg", "e_drtg", "e_pf", "e_pa", "rest", "gp_season", "prev_ph"]]

    played = results.dropna(subset=["home_pts", "away_pts"])
    lg = (played.home_pts + played.away_pts).groupby(played.date).mean().sort_index()
    lg_pre = lg.ewm(halflife=60).mean().shift(1)
    G = games.merge(results[["date", "home", "away", "home_pts", "away_pts"]], on=["date", "home", "away"], how="inner")
    G["final_total"] = G.home_pts + G.away_pts
    for side in ["home", "away"]:
        f = team_feat.rename(columns={c: f"{side[0]}_{c}" for c in team_feat.columns if c not in ("date", "team")})
        G = G.merge(f.rename(columns={"team": side}), on=["date", side], how="left")
    # league level for a date not played yet: the latest value (all earlier dates)
    full = lg.ewm(halflife=60).mean()
    G["league_lvl"] = [lg_pre.get(dd, np.nan) if dd in lg_pre.index else (full[full.index < dd].iloc[-1] if (full.index < dd).any() else np.nan)
                       for dd in G.date]

    G = G.sort_values("tip").reset_index(drop=True)
    long = pd.concat([G[["date", "tip", "home", "dk_close_point", "dk_open_point", "final_total"]].rename(columns={"home": "team"}),
                      G[["date", "tip", "away", "dk_close_point", "dk_open_point", "final_total"]].rename(columns={"away": "team"})])
    long = long.sort_values(["team", "tip"])
    long["dk_err"] = long.final_total - long.dk_open_point
    long["dk_mv"] = long.dk_close_point - long.dk_open_point
    for c, hl in [("dk_close_point", 5), ("dk_err", 10), ("dk_mv", 10)]:
        long[f"m_{c}"] = long.groupby("team")[c].transform(lambda s: s.ewm(halflife=hl, ignore_na=True).mean().shift(1))
    mem = long[["date", "team", "m_dk_close_point", "m_dk_err", "m_dk_mv"]].drop_duplicates(["date", "team"])
    for side in ["home", "away"]:
        G = G.merge(mem.rename(columns={"team": side, "m_dk_close_point": f"{side[0]}_mkt",
                                        "m_dk_err": f"{side[0]}_operr", "m_dk_mv": f"{side[0]}_opmv"}), on=["date", side], how="left")
    if inj is not None:
        icols = [c for c in inj.columns if c.endswith("_open") and c not in ("open_spread", "open_total")]
        G = G.merge(inj[["date", "home", "away"] + icols], on=["date", "home", "away"], how="left")
    G["season"] = G.tip.apply(season_of)
    G["exp_pace"] = (G.h_e_pace + G.a_e_pace) / 2
    G["fund_total"] = G.exp_pace * (G.h_e_ortg + G.a_e_drtg + G.a_e_ortg + G.h_e_drtg) / 200
    G["mkt_total"] = (G.h_mkt + G.a_mkt) / 2
    G["b2b_h"] = (G.h_rest == 1).astype(int); G["b2b_a"] = (G.a_rest == 1).astype(int)
    G["gp_min"] = G[["h_gp_season", "a_gp_season"]].min(axis=1)
    G["month"] = G.tip.dt.month
    G["ready"] = (G.h_prev_ph.fillna(0) == 0) & (G.a_prev_ph.fillna(0) == 0) & G.fund_total.notna() & G.mkt_total.notna()
    return G


# ---------------------------------------------------------------- opener model (step 2, no injury inputs)
def fit_opener(tr, lam=OPENER_LAM):
    """tr: games with dk_open_point and dk_open_lead_h. Returns a dict model (JSON-safe)."""
    tr = tr.dropna(subset=["dk_open_point"]).copy()
    tr["dk_lead"] = np.log1p(tr.dk_open_lead_h)
    cols = OPENER_BASE + ["dk_lead"]
    med = tr[cols].median()
    X = tr[cols].fillna(med).to_numpy(float)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    A = np.c_[np.ones(len(tr)), (X - mu) / sd]
    keys = sorted(set((tr.season.astype(str) + tr.home).tolist() + (tr.season.astype(str) + tr.away).tolist()))
    idx = {k: i for i, k in enumerate(keys)}
    Z = np.zeros((len(tr), len(keys)))
    for r, (s, h, a) in enumerate(zip(tr.season.astype(str), tr.home, tr.away)):
        Z[r, idx[s + h]] += 1; Z[r, idx[s + a]] += 1
    M = np.c_[A, Z]
    pen = np.sqrt(np.array([0.0] + [1e-3] * (A.shape[1] - 1) + [lam] * Z.shape[1]))
    beta = np.linalg.lstsq(np.r_[M, np.diag(pen)], np.r_[tr.dk_open_point.to_numpy(), np.zeros(M.shape[1])], rcond=None)[0]
    return dict(cols=cols, med=med.tolist(), mu=mu.tolist(), sd=sd.tolist(), beta=beta[:A.shape[1]].tolist(),
                team=dict(zip(keys, beta[A.shape[1]:].tolist())), n=int(len(tr)), lam=lam)


def opener_pred(m, df, lead_h=None):
    """DK opener prediction for rows of df; lead_h (hours before tip the line was first seen) overrides dk_open_lead_h"""
    df = df.copy()
    df["dk_lead"] = np.log1p(pd.to_numeric(df.dk_open_lead_h if lead_h is None else pd.Series(lead_h, index=df.index), errors="coerce").astype(float))
    X = df[m["cols"]].fillna(pd.Series(m["med"], index=m["cols"])).to_numpy(float)
    p = np.c_[np.ones(len(df)), (X - np.array(m["mu"])) / np.array(m["sd"])] @ np.array(m["beta"])
    te = [m["team"].get(str(s) + h, 0.0) + m["team"].get(str(s) + a, 0.0) for s, h, a in zip(df.season, df.home, df.away)]
    return p + np.array(te)


# ---------------------------------------------------------------- movement features (step 3)
def implied(p):
    p = np.asarray(p, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(p > 0, 100 / (100 + p), -p / (100 - p))


def snapshot_panel(d, games, books=None):
    """d: raw odds rows (any books). games: date, home, away, dk_open_point, dk_close_point (may be NaN live), dk_opred.
    One row per game and snapshot with DK quoted; every input uses only quotes from that same snapshot."""
    d = d[d.market == "totals"].copy()
    if books is not None: d = d[d.book.isin(books)]
    d["snap"] = pd.to_datetime(d.snapshot_utc).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d["tipt"] = pd.to_datetime(d.commence_et)
    d["lead_h"] = (d.tipt - d.snap).dt.total_seconds() / 3600
    d = d[d.lead_h > 0]
    d["date"] = d.tipt.dt.strftime("%Y-%m-%d")
    d["home"] = d.home.map(NAME); d["away"] = d.away.map(NAME)
    d = d.dropna(subset=["home", "away"])
    key = ["date", "home", "away", "snap", "book"]
    ov, un = d[d.outcome == "Over"], d[d.outcome == "Under"]
    q = ov[key + ["lead_h", "point", "price"]].merge(un[key + ["price"]], on=key, suffixes=("_o", "_u"), how="left")
    q = q.drop_duplicates(key, keep="last")
    q["lean"] = implied(q.price_o) - implied(q.price_u)
    ix = ["date", "home", "away", "snap"]
    pt = q.pivot_table(index=ix, columns="book", values="point")
    ld = q.pivot_table(index=ix, columns="book", values="lean")
    for b in ("draftkings", "pinnacle", "fanduel"):
        if b not in pt: pt[b] = np.nan
        if b not in ld: ld[b] = np.nan
    px = q[q.book == "draftkings"].set_index(ix)[["price_o", "price_u", "lead_h"]]
    P = px.join(pt.add_prefix("pt_")).join(ld[["draftkings", "pinnacle"]].add_prefix("lean_")).reset_index()
    P = P.dropna(subset=["pt_draftkings"])
    others = [c for c in pt.columns if c != "draftkings"]
    P["cons_gap"] = P[["pt_" + c for c in others]].median(axis=1) - P.pt_draftkings
    P["n_books"] = P[["pt_" + c for c in pt.columns]].notna().sum(axis=1)
    P["pin_gap"] = P.pt_pinnacle - P.pt_draftkings
    P["fd_gap"] = P.pt_fanduel - P.pt_draftkings
    P = P.merge(games, on=["date", "home", "away"], how="inner").sort_values(["date", "home", "snap"])
    P["dk_now"] = P.pt_draftkings
    P["move_so_far"] = P.dk_now - P.dk_open_point
    P["dk_oresid"] = P.dk_open_point - P.dk_opred
    P["opener_view"] = P.dk_opred - P.dk_now
    P["log_lead"] = np.log1p(P.lead_h)
    P["pin_present"] = P.pin_gap.notna().astype(int)
    return P


def move_design(df, med, feats=None):
    feats = MOVE_FEAT if feats is None else feats
    X = df[feats].copy()
    for c in ["pin_gap", "fd_gap", "cons_gap", "lean_pinnacle"]:
        if c in X: X[c] = X[c].fillna(0.0)
    return X.fillna(pd.Series(list(med), index=feats)).to_numpy(float)


def an_to_odds(an, start_utc=None):
    """Action Network pregame rows (research/pregame/*.csv: change-only, every minute) -> odds rows in the history's format,
    one snapshot per 5 minutes, each book's latest full-game total as of that moment (forward-filled; the history's snapshots
    were likewise each book's current quote). Only the five AN_BOOKS. home/away become full names so NAME maps them back."""
    inv = {v: k for k, v in NAME.items() if k != "LA Clippers"}
    x = an[(an.period == "event") & (an.market == "total") & an.book.isin(AN_NAME) & an.side.isin(["over", "under"])].copy()
    if not len(x): return pd.DataFrame(columns=COLS)
    x["book"] = x.book.map(AN_NAME)
    x["t"] = pd.to_datetime(x.seen_at_et)
    x["tip"] = pd.to_datetime(x.start_et)
    x = x.sort_values("t")
    grid_end = x.t.max().ceil("5min")
    grid_start = x.t.min().floor("5min") if start_utc is None else pd.Timestamp(start_utc)
    grid = pd.date_range(grid_start, grid_end, freq="5min")
    out = []
    for (gid, book, side), g in x.groupby(["an_game_id", "book", "side"]):
        g = g.drop_duplicates("t", keep="last").set_index("t")
        s = g[["value", "odds"]].reindex(g.index.union(grid)).ffill().loc[grid].dropna()
        tip = g.tip.iloc[0]
        s = s[s.index < tip]
        if not len(s): continue
        out.append(pd.DataFrame(dict(snap=s.index, an_game_id=gid, book=book, outcome=side.capitalize(), point=s.value.values,
                                     price=s.odds.values, tip=tip, home=inv.get(g.home.iloc[0]), away=inv.get(g.away.iloc[0]))))
    if not out: return pd.DataFrame(columns=COLS)
    o = pd.concat(out, ignore_index=True).dropna(subset=["home", "away"])
    o["snapshot_utc"] = o.snap.dt.tz_localize("America/New_York").dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    o["event_id"] = "an" + o.an_game_id.astype(str); o["commence_et"] = o.tip.astype(str); o["market"] = "totals"
    return o[COLS]


def tree_predict(m, X):
    """exported HistGradientBoosting model: baseline + sum of trees (nodes: feature, threshold, left, right, leaf, value, nan_left)"""
    out = np.full(len(X), m["baseline"], float)
    for t in m["trees"]:
        f, th, lf, rt, leaf, val, nl = (np.asarray(t[k]) for k in ("f", "th", "l", "r", "leaf", "v", "nl"))
        node = np.zeros(len(X), int)
        for _ in range(64):
            act = leaf[node] == 0
            if not act.any(): break
            xv = X[np.arange(len(X)), f[node]]
            go_left = np.where(np.isnan(xv), nl[node] == 1, xv <= th[node])
            node = np.where(act, np.where(go_left, lf[node], rt[node]), node)
        out += val[node]
    return out


# ---------------------------------------------------------------- reachability (Fable check, Nov 5, 2026)
BOX_READY = pd.Timedelta(hours=11, minutes=41)   # morning run time: a game's box score is in the data from 11:41 AM ET the next day


def ready_time(results):
    """per game (date, home, away): earliest moment the live code can price it = morning run after BOTH teams' previous games.
    results: date, home, away for every game (played or scheduled). Returns a DataFrame date, home, away, ready_at."""
    r = results[["date", "home", "away"]].drop_duplicates()
    long = pd.concat([pd.DataFrame(dict(date=r.date, team=r.home)), pd.DataFrame(dict(date=r.date, team=r.away))])
    long = long.sort_values(["team", "date"]).drop_duplicates()
    long["prev"] = long.groupby("team").date.shift(1)
    long["team_ready"] = pd.to_datetime(long.prev) + pd.Timedelta(days=1) + BOX_READY
    tr_ = dict(zip(zip(long.date, long.team), long.team_ready))
    h = r.assign(h_ready=[tr_.get(k) for k in zip(r.date, r.home)])[["date", "home", "away", "h_ready"]]
    a = r.assign(a_ready=[tr_.get(k) for k in zip(r.date, r.away)])[["date", "home", "away", "a_ready"]]
    out = r.merge(h, on=["date", "home", "away"], how="left").merge(a, on=["date", "home", "away"], how="left")
    out["ready_at"] = out[["h_ready", "a_ready"]].max(axis=1)
    return out[["date", "home", "away", "ready_at"]]
