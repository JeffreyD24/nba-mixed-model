"""
Market models, live (research/MARKET_MODELS_PLAN.md, step 3): DraftKings NBA totals LINE-MOVEMENT bets. PROVISIONAL tier
(research/PROVISIONAL_BETS.md), started Nov 5, 2026 at Jeffrey's request: alerts with money, own record, stop rule.

  python market_models_live.py WORKDIR fit     morning: refit the opener model (step 2, no injury report) on everything
                                                through yesterday and save features for upcoming games
  python market_models_live.py WORKDIR check   every 5-minute check: predict where DK's total will close vs now, from every
                                                book's quote at the latest snapshot; BET alert the first time the predicted
                                                move is 1.5+ pts (side the line is predicted to move toward, at DK now)
  python market_models_live.py WORKDIR grade   morning: grade alerts (DK close from the live snapshots, final score)

The model (data/movement_model_v1an_reach.json, "movement v1-an") is the pre-registered step-3 model without injury inputs and
without Pinnacle, using only the five books the free Action Network feed shares with the history (DraftKings, FanDuel,
Caesars, BetMGM, BetRivers), trained on DK totals 2022-23 to 2025-26. Why: The Odds API live feed (with Pinnacle) paused
Nov 5 when the plan's credits ran low. Pre-registered addendum (research/market_models/STEP3_MOVEMENT_PREREG.md, 7f40f5e):
2025-26 test 505 bets, CLV +1.41 (break-even +1.07), +5.4u. Fable check (Nov 5): 144 of those used a box score not played yet;
counting only bets the live code could make (after the morning run that follows both teams' previous games, 48 h or less, trained
the same way): 385 bets, CLV +1.31, -10.8u. Live as PROVISIONAL on CLV (the addendum's live bar). Blend (step 4) also lives here.
Quotes: Action Network, fetched fresh at every check (research/pregame/ files give each game's first DraftKings total).
Files: state/market_models/ (opener_model.json, upcoming.csv, dk_first_seen.csv, movement_alerts.csv);
every prediction: research/market_models_live/YYYY-MM-DD.csv.gz.
"""
import os, sys, glob, json
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]); MODE = sys.argv[2] if len(sys.argv) > 2 else "check"
sys.path.insert(0, W)
import market_models_core as C           # noqa: E402

ET = ZoneInfo("America/New_York")
NOW = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None)); TODAY = NOW.normalize()
SD = os.path.join(W, "state", "market_models"); os.makedirs(SD, exist_ok=True)
LIVE = os.path.join(W, "research", "live_odds", "nba")
MOVE_MODEL = os.path.join(W, "data", "movement_model_v1an_reach.json")   # trained on snapshots live can price (Fable, Nov 5)
PREGAME = os.path.join(W, "research", "pregame")
BET_MOVE = 1.5            # pre-registered trigger (pts of predicted DK move)
MIN_LEAD_H = 0.5          # no bets in the last 30 minutes (as tested)
STOP_MOVE = 0.5           # DON'T BET follow-up when the predicted move in the bet's direction drops under this (move done/reversed)
MAX_LEAD_H = 48           # only games starting within 2 days: later games' schedules (and so rest/previous game) aren't complete
                          #   in the feed yet. 4% of the 2025-26 test bets fired earlier (23 bets, CLV +1.80, +5.5u): small loss.
REFIT_MIN = 60            # the 5-minute check refits the opener model when its files are older than this (new games appear)
REMIND_MOVE = 1.0         # reminders only while the predicted move is still this big and the line is no worse than alerted
TIER = "provisional_movement"
BLEND = os.path.join(W, "data", "blend_v1_reach.json")     # step 4 blend (research/market_models/STEP4_BLEND_RESULTS.md)
BLEND_TIER = "provisional_blend"
BLEND_STOP = 1.07          # DON'T BET follow-up when the blend's edge at DK now drops under break-even CLV (judgment, not tested)
B_EXTRA = ["v4", "fair", "edge"]                     # extra columns in blend_alerts.csv
A_COLS = ["key", "date", "home", "away", "tip_et", "game_id", "alerted_at_et", "snap_et", "lead_h", "side", "line", "price",
          "pred_move", "dk_first_seen", "opener_pred", "pin_now", "fd_now", "fd_line_txt", "pushed", "skip_reason", "tier",
          "reminded_at_et", "stopped_at_et", "closing_line", "clv_points", "home_pts", "away_pts", "result", "units"]


def p(*a): print("[market models]", *a)


def save_csv(df, path, **kw):
    """write to a temp file then rename, so a timeout mid-write never leaves a truncated file (Fable check, Nov 5)"""
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, **kw); os.replace(tmp, path)


def results_2027():
    """2026-27 games from the tracker's picks log: date, home, away, scores (NaN until played), ESPN DK open/close, tip"""
    f = os.path.join(W, "state", "picks_log.csv")
    if not os.path.exists(f): return pd.DataFrame(columns=["date", "home", "away", "home_pts", "away_pts", "open_total", "close_total", "tip_et", "game_id"])
    L = pd.read_csv(f)
    L["date"] = pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
    return L.drop_duplicates(["date", "home", "away"])[["date", "home", "away", "home_pts", "away_pts", "open_total", "close_total", "tip_et", "game_id"]]


def live_files(days=None):
    fs = sorted(f for f in glob.glob(os.path.join(LIVE, "*.csv.gz")) if os.path.basename(f)[:10] <= f"{TODAY:%Y-%m-%d}")
    return fs if days is None else fs[-days:]


def pregame_rows(days=(-1, 0, 1, 2)):
    """Action Network pregame files (change-only rows) for game dates around today"""
    fs = [os.path.join(PREGAME, f"{(TODAY + pd.Timedelta(days=k)):%Y-%m-%d}.csv") for k in days]
    fs = [f for f in fs if os.path.exists(f)]
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def an_games(an):
    """date, home, away, tip of NBA games in the Action Network rows"""
    if not len(an): return pd.DataFrame(columns=["date", "home", "away", "tip"])
    g = an.drop_duplicates("an_game_id")[["date", "home", "away", "start_et"]].rename(columns={"start_et": "tip"})
    g["tip"] = pd.to_datetime(g.tip)
    return g[g.home.isin(set(C.NAME.values())) & g.away.isin(set(C.NAME.values()))]


def an_now():
    """current Action Network full-game totals for today's and tomorrow's games, as odds rows stamped now"""
    import pregame as PG
    rows = []
    for k in (0, 1):
        rows += PG.rows_for(PG.fetch(NOW + pd.Timedelta(days=k)))
    if not rows: return pd.DataFrame(columns=C.COLS)
    x = pd.DataFrame(rows)
    x = x[(x.period == "event") & (x.market == "total") & x.book.isin(C.AN_NAME) & x.side.isin(["over", "under"])].copy()
    inv = {v: k for k, v in C.NAME.items() if k != "LA Clippers"}
    x["home"] = x.home.map(inv); x["away"] = x.away.map(inv)
    x = x.dropna(subset=["home", "away", "value"])
    stamp = pd.Timestamp(NOW).tz_localize(ET).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    return pd.DataFrame(dict(snapshot_utc=stamp, event_id="an" + x.an_game_id.astype(str), commence_et=x.start_et.astype(str),
                             home=x.home, away=x.away, book=x.book.map(C.AN_NAME), market="totals",
                             outcome=x.side.str.capitalize(), price=x.odds, point=x.value))[C.COLS]


# ------------------------------------------------------------------ fit (morning)
def fit():
    hist = sorted(glob.glob(os.path.join(W, "data", "odds_history", "nba", "*.csv.gz")))
    d = C.read_odds(hist + live_files())
    games = C.first_close(d)
    R27 = results_2027()
    # upcoming games seen in the live feed (not yet in the picks log)
    up = games[pd.to_datetime(games.tip) > NOW - pd.Timedelta(hours=6)][["date", "home", "away"]]
    # the Odds API live feed paused Nov 5, 2026: upcoming games also come from Action Network and the picks log
    ag = an_games(pregame_rows())
    ag = ag[ag.tip > NOW - pd.Timedelta(hours=6)]
    pl = R27[pd.to_datetime(R27.tip_et, errors="coerce") > NOW - pd.Timedelta(hours=6)][["date", "home", "away"]]
    up = pd.concat([up, ag[["date", "home", "away"]], pl]).drop_duplicates()
    have0 = set(zip(games.date, games.home, games.away))
    newg = ag[[(a, b, c) not in have0 for a, b, c in zip(ag.date, ag.home, ag.away)]]
    if len(newg):
        games = pd.concat([games, newg.assign(tip=newg.tip)], ignore_index=True)
    tr0 = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
    res = pd.concat([tr0[["date", "home", "away", "home_pts", "away_pts"]], R27[["date", "home", "away", "home_pts", "away_pts"]],
                     up.assign(home_pts=np.nan, away_pts=np.nan)]).drop_duplicates(["date", "home", "away"], keep="first")
    # 2026-27 games before the live recorder started (Nov 2): DK open/close from ESPN, so team market memory is complete
    have = set(zip(games.date, games.home, games.away))
    extra = R27[[(a, b, c) not in have for a, b, c in zip(R27.date, R27.home, R27.away)]]
    if len(extra):
        extra = pd.DataFrame(dict(date=extra.date, home=extra.home, away=extra.away, tip=pd.to_datetime(extra.tip_et),
                                  dk_open_point=extra.open_total, dk_close_point=extra.close_total))
        games = pd.concat([games, extra], ignore_index=True)
    # games whose live Odds API file ended well before tip (feed paused Nov 5, 2026): their "close" is not a close; use ESPN's DK close
    stale = (games.date >= "2026-10-01") & (pd.to_numeric(games.get("dk_close_lead_h"), errors="coerce") > 1)
    if stale.any():
        cl = dict(zip(zip(R27.date, R27.home, R27.away), R27.close_total))
        games.loc[stale, "dk_close_point"] = [cl.get(k, np.nan) for k in zip(games.date[stale], games.home[stale], games.away[stale])]
    ps = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(W, "data", "player_stats", "season_*.csv.gz")))])
    G = C.build_games(games, ps, res)
    trn = G[(pd.to_datetime(G.date) < TODAY) & G.dk_open_point.notna() & G.dk_open_lead_h.notna() & G.fund_total.notna()
            & G.mkt_total.notna() & G.season.between(2022, 2027)]
    m = C.fit_opener(trn)
    m.update(fit_at_et=str(NOW)[:16], through=str(trn.date.max()))
    tmpj = os.path.join(SD, "opener_model.json.tmp"); json.dump(m, open(tmpj, "w")); os.replace(tmpj, os.path.join(SD, "opener_model.json"))
    U = G[(pd.to_datetime(G.tip) > NOW) & G.final_total.isna()]
    keep = ["date", "home", "away", "tip", "season", "ready"] + C.OPENER_BASE
    save_csv(U[keep], os.path.join(SD, "upcoming.csv"))
    p(f"opener model refit on {m['n']} games through {m['through']}; {len(U)} upcoming games, {int(U.ready.sum())} ready")


# ------------------------------------------------------------------ check (every 5 minutes)
def update_first_seen(an):
    """first DraftKings full-game total per game from the Action Network pregame files (its "opener" row when there is one,
    otherwise the earliest value seen), kept in a cache so it never changes once recorded"""
    path = os.path.join(SD, "dk_first_seen.csv")
    FS = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["key", "date", "home", "away", "tip", "point", "lead_h", "snap_et"])
    if not len(an): return FS
    x = an[(an.book == "DraftKings") & (an.period == "event") & (an.market == "total") & (an.side == "over")].dropna(subset=["value"]).copy()
    if not len(x): return FS
    x["snap"] = pd.to_datetime(x.seen_at_et); x["tip"] = pd.to_datetime(x.start_et)
    x = x[x.snap < x.tip]
    x["is_open"] = (x.line_status.astype(str) == "opener").astype(int)
    x = x.sort_values(["is_open", "snap"], ascending=[False, True]).groupby(["date", "home", "away"]).head(1)
    x["key"] = x.date + "|" + x.home + "|" + x.away
    x["point"] = x.value
    x["lead_h"] = (x.tip - x.snap).dt.total_seconds() / 3600
    new = x[~x.key.isin(set(FS.key))]
    if len(new):
        FS = pd.concat([FS, new.assign(snap_et=new.snap.astype(str).str[:19], tip=new.tip.astype(str))[FS.columns]], ignore_index=True)
        save_csv(FS, path)
    return FS


def load_alerts(name="movement_alerts.csv", cols=None):
    cols = A_COLS if cols is None else cols
    f = os.path.join(SD, name)
    A = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame(columns=cols)
    for c in cols:
        if c not in A: A[c] = np.nan
    for c in ("result", "reminded_at_et", "stopped_at_et", "skip_reason", "fd_line_txt", "pushed", "tier", "key", "snap_et",
              "alerted_at_et", "tip_et", "side"):
        A[c] = A[c].astype(object)                                 # text columns stay text even when empty (pandas 3)
    return A


def v4_alert(date, home, away):
    """latest sent totals BET alert from the main model (alert.py) for this game, unless it was stopped: (side, line) or None"""
    f = os.path.join(W, "state", "alerts.csv")
    if not os.path.exists(f): return None
    A = pd.read_csv(f)
    r = A[(A.date.astype(str) == date) & (A.home == home) & (A.away == away) & (A.market == "total")
          & (A.verdict.astype(str) == "BET") & A.sent.astype(str).isin(["True", "1", "1.0"])]
    if not len(r): return None
    r = r.iloc[-1]
    if isinstance(r.get("stopped_at_et"), str) and not isinstance(r.get("resumed_at_et"), str): return None
    return str(r.side).lower(), float(r.line)


def v4_now(date, home, away):
    """latest live v4 total (alert.py's model_total, logged in research/model/<game date>.csv) seen by now, or None"""
    f = os.path.join(W, "research", "model", f"{date}.csv")
    if not os.path.exists(f): return None
    try: M = pd.read_csv(f)
    except Exception: return None                                    # empty or half-written file: try again next check
    M = M[(M.home == home) & (M.away == away) & (pd.to_datetime(M.seen_at_et) <= NOW)].dropna(subset=["model_total"])
    return float(M.sort_values("seen_at_et").model_total.iloc[-1]) if len(M) else None


def logged(date, home, away, side=None):
    f = os.path.join(W, "state", "my_bets.csv")
    if not os.path.exists(f): return False
    B = pd.read_csv(f)
    m = (B.date.astype(str) == date) & (B.home == home) & (B.away == away) & (B.market == "total")
    if side: m &= B.pick.astype(str).str.lower() == side
    return bool(m.any())


def price_txt(px):
    try: return f" ({int(px):+d})"
    except Exception: return ""


_DK = {}
DK_NBA_PAGE = "https://sportsbook.draftkings.com/leagues/basketball/nba"
def dk_total_link(date, home, away, side, line):
    """DraftKings bet-slip link for a total (ESPN's odds feed; falls back to the game page). None if ESPN has no DraftKings link.
    Nov 5, 2026: movement / blend alerts had dk=None, so no DraftKings button."""
    try:
        import dk_direct
        lk = dk_direct.slip_link("nba", date, home, away, side)
        if lk: return lk
    except Exception: pass
    try:
        import espn
        if date not in _DK:
            _DK[date] = espn.lines([date], when=("current",))
        L = _DK[date]
        row = L[(L.home == home) & (L.away == away)] if len(L) and "home" in L else L.iloc[0:0]
        import alert as AL
        lk = AL.dk_link(row.iloc[0].to_dict(), "total", side, line) if len(row) else None
        # ESPN's odds feed lags Action Network by an hour or more on a new line (POR @ LAL, PHI @ CLE Nov 5: ESPN had no DraftKings
        # line yet), so there is no bet-slip link: fall back to DraftKings' NBA page rather than no button
        return lk or DK_NBA_PAGE
    except Exception as ex:
        print("[market models] DraftKings link unavailable:", type(ex).__name__, str(ex)[:80]); return DK_NBA_PAGE


def fd_extra(r, side, dk_line):
    """FanDuel button args for a reminder: only when FanDuel has a line for this total (Nov 5, 2026)"""
    try:
        import alert as AL
        _, fdl, best = AL.fanduel.compare("nba", r.date, r.home, r.away, "total", side, dk_line, None, label=side)
        return dict(fd=fdl, best=best)
    except Exception:
        return {}


def dk_confirmed(date, home, away, line):
    """True when ESPN's DraftKings feed shows the same total Action Network's DraftKings quote does. Nov 5, 2026: Action Network's
    DraftKings line for POR @ LAL (238.5, unchanged since Nov 3) and PHI @ CLE (234.5, 4 pts above every other book) was not on DraftKings'
    app; ESPN's DraftKings feed had nothing for either game. Such a line is not a bet, so no alert or reminder until ESPN agrees."""
    try:
        import dk_direct                                           # DraftKings' own feed first (Nov 5, 2026); ESPN only if that fetch fails
        if len(dk_direct.now("nba")):
            t = dk_direct.total("nba", date, home, away)
            return t is not None and abs(t[0] - float(line)) < 0.01
    except Exception as ex:
        print("[market models] direct DraftKings check failed:", type(ex).__name__, str(ex)[:80])
    try:
        import espn
        if date not in _DK: _DK[date] = espn.lines([date], when=("current",))
        L = _DK[date]
        row = L[(L.home == home) & (L.away == away)] if len(L) and "home" in L else L.iloc[0:0]
        if not len(row): return False
        r = row.iloc[0]
        return "draftkings" in str(r.get("book", "")).lower() and abs(float(r.get("current_total")) - float(line)) < 0.01
    except Exception as ex:
        print("[market models] DraftKings confirmation failed:", type(ex).__name__, str(ex)[:80]); return False


def check():
    up = os.path.join(SD, "upcoming.csv")
    om_path = os.path.join(SD, "opener_model.json")
    try: fit_at = pd.Timestamp(json.load(open(om_path))["fit_at_et"])
    except Exception: fit_at = None
    # refit when the files are missing or the last fit is over an hour old (file times can't be used: each Actions run checks out fresh)
    if not os.path.exists(up) or fit_at is None or (NOW - fit_at).total_seconds() > REFIT_MIN * 60:
        try: fit()
        except Exception as ex: p("refit failed:", type(ex).__name__, str(ex)[:120])
    if not (os.path.exists(os.path.join(SD, "opener_model.json")) and os.path.exists(up)):
        p("no opener model yet; nothing to check"); return
    if not os.path.exists(MOVE_MODEL): p("movement model file missing"); return
    FS = update_first_seen(pregame_rows())
    try:
        d = an_now()                                                   # fresh quotes from Action Network, this minute
    except Exception as ex:
        p("Action Network fetch failed:", type(ex).__name__, str(ex)[:100]); return
    if not len(d): p("no Action Network totals right now"); return
    om = json.load(open(os.path.join(SD, "opener_model.json"))); mm = json.load(open(MOVE_MODEL))
    U = pd.read_csv(os.path.join(SD, "upcoming.csv"))
    U = U[U.ready.astype(str).isin(["True", "1", "1.0"])]
    U["key"] = U.date + "|" + U.home + "|" + U.away
    U = U.merge(FS[["key", "point", "lead_h"]].rename(columns={"point": "dk_open_point", "lead_h": "dk_open_lead_h"}), on="key", how="inner")
    U[["dk_open_point", "dk_open_lead_h"]] = U[["dk_open_point", "dk_open_lead_h"]].apply(pd.to_numeric, errors="coerce")
    if not len(U): p("no upcoming games with a ready opener model and a DK first line"); return
    U["dk_opred"] = C.opener_pred(om, U)
    U["dk_close_point"] = np.nan; U["final_total"] = np.nan
    P = C.snapshot_panel(d, U[["date", "home", "away", "season", "final_total", "dk_open_point", "dk_close_point", "dk_opred"]],
                         books=C.AN_BOOKS)
    if not len(P): p("no current DK quotes for ready games"); return
    tips = d.drop_duplicates(["home", "away", "commence_et"]).assign(tip=lambda z: pd.to_datetime(z.commence_et))
    tips["date"] = tips.tip.dt.strftime("%Y-%m-%d"); tips["home"] = tips.home.map(C.NAME); tips["away"] = tips.away.map(C.NAME)
    P = P.merge(tips[["date", "home", "away", "tip"]].drop_duplicates(["date", "home", "away"]),
                                    on=["date", "home", "away"], how="left")
    P["lead_now"] = (P.tip - NOW).dt.total_seconds() / 3600
    P = P[(P.lead_now >= MIN_LEAD_H) & (P.lead_now <= MAX_LEAD_H)]
    if not len(P): p("no games 30 minutes to 48 hours from tip"); return
    P["pred"] = C.tree_predict(mm, C.move_design(P, mm["med"], mm["features"]))
    P["key"] = P.date + "|" + P.home + "|" + P.away
    # research log: every prediction at every new snapshot
    ld = os.path.join(W, "research", "market_models_live"); os.makedirs(ld, exist_ok=True)
    lp = os.path.join(ld, f"{TODAY:%Y-%m-%d}.csv.gz")                           # one file per day (kept small for the 5-min saves)
    LG = pd.read_csv(lp) if os.path.exists(lp) else pd.DataFrame(columns=["key", "snap_et"])
    out = P.assign(checked_at_et=str(NOW)[:16], snap_et=P.snap.astype(str).str[:19])[
        ["key", "checked_at_et", "snap_et", "lead_h", "dk_now", "price_o", "price_u", "pt_fanduel", "cons_gap", "n_books", "dk_open_point", "dk_opred", "pred"]]
    seen = set(zip(LG.key, LG.snap_et.astype(str)))
    out = out[[(k, s) not in seen for k, s in zip(out.key, out.snap_et)]]
    if len(out): save_csv(pd.concat([LG, out], ignore_index=True), lp, compression="gzip")

    A = load_alerts(); changed = False
    import alert as AL                                             # notify(), reminder spacing, price cap, FanDuel compare
    fanduel = AL.fanduel
    for r in P.itertuples():
        if r.key in set(A[~A.skip_reason.astype(str).str.startswith('DraftKings line not confirmed')].key): continue   # unconfirmed ones retry
        if abs(r.pred) < BET_MOVE: continue
        side = "over" if r.pred > 0 else "under"
        px = r.price_o if side == "over" else r.price_u
        tip_txt = f"{pd.Timestamp(r.tip):%a %-I:%M %p}"
        H, Aw = r.home.upper(), r.away.upper()
        skip = ""
        v4 = v4_alert(r.date, r.home, r.away)
        if v4 and v4[0] != side: skip = f"conflict: main totals model has a BET on {v4[0].upper()} {v4[1]:g}"
        elif v4: skip = f"same side as the main totals model's BET ({v4[0].upper()} {v4[1]:g}); not sent twice"
        elif not dk_confirmed(r.date, r.home, r.away, r.dk_now): skip = "DraftKings line not confirmed bettable (ESPN's DraftKings feed has no matching total)"
        fdt, fdl, best = None, None, None
        try:
            fdt, fdl, best = fanduel.compare("nba", r.date, r.home, r.away, "total", side, float(r.dk_now), px, label=side,
                                             edge=abs(r.pred), need=BET_MOVE)
        except Exception as ex:
            p("FanDuel compare failed:", type(ex).__name__)
        if not skip and px is not None and not pd.isna(px) and float(px) < AL.MAX_PRICE:
            ok = None
            try: ok = fanduel.same_or_better("nba", r.date, r.home, r.away, "total", side, float(r.dk_now), AL.MAX_PRICE)
            except Exception: pass
            if ok is None: skip = f"price {int(px):+d} worse than {AL.MAX_PRICE} and FanDuel no better"
        what = f"{side.upper()} {r.dk_now:g}{price_txt(px)}"
        sent = False
        if not skip:
            body = (f"PROVISIONAL (market models v1-an, line-movement bet; own record and stop rule). The movement model expects "
                    f"DraftKings' total to close about {abs(r.pred):.1f} pts {'HIGHER' if side == 'over' else 'LOWER'} than {r.dk_now:g}: "
                    f"bet {side.upper()} now, before it moves. Opened {r.dk_open_point:g} (opener formula {r.dk_opred:.1f}); "
                    f"FanDuel "
                    f"{('%g' % r.pt_fanduel) if not pd.isna(r.pt_fanduel) else '-'}. Tip {tip_txt}.\n"
                    f"Backtest 2025-26 (bets the live code could make): 385 bets, beat the close by 1.31 pts (break-even 1.07) but -10.8u. Unproven.")
            if fdt: body = fdt + "\n" + body
            try:
                sent = AL.notify(f"BET {what} (PROVISIONAL movement): {Aw} @ {H}, {tip_txt}", body, priority="high",
                                 tags="chart_with_upwards_trend" if side == "over" else "chart_with_downwards_trend",
                                 kind="bet", dk=dk_total_link(r.date, r.home, r.away, side, float(r.dk_now)), fd=fdl, best=best)
            except Exception as ex:
                skip = f"NOT sent: ntfy error ({type(ex).__name__})"
        gid = np.nan
        R27 = results_2027(); g = R27[(R27.date == r.date) & (R27.home == r.home) & (R27.away == r.away)]
        if len(g): gid = g.game_id.iloc[0]
        row = dict(key=r.key, date=r.date, home=r.home, away=r.away, tip_et=str(r.tip)[:16], game_id=gid, alerted_at_et=str(NOW)[:16],
                   snap_et=str(r.snap)[:19], lead_h=round(r.lead_now, 2), side=side, line=r.dk_now, price=px, pred_move=round(r.pred, 2),
                   dk_first_seen=r.dk_open_point, opener_pred=round(r.dk_opred, 2), pin_now=np.nan, fd_now=r.pt_fanduel,
                   fd_line_txt=(fdt or "")[:200], pushed=bool(sent), skip_reason=skip, tier=TIER)
        A = A[~((A.key == r.key) & A.skip_reason.astype(str).str.startswith('DraftKings line not confirmed'))]   # replace the earlier unconfirmed row
        A = pd.concat([A, pd.DataFrame([row])], ignore_index=True); changed = True
        p(("SENT " if sent else "RECORDED ") + f"{what} {Aw} @ {H} | predicted move {r.pred:+.2f}" + (f" | {skip}" if skip else ""))


    # ---------------- step 4 blend (PROVISIONAL): one decision per game, at the first check at or after 9 PM ET the night before
    # (or when DK first posts, if later). Fair = a + w_v4 * v4 + w_mkt * (DK now + expected move); BET when |fair - DK now| >= 2.
    if os.path.exists(BLEND):
        bw = json.load(open(BLEND)); BC = A_COLS + B_EXTRA
        B = load_alerts("blend_alerts.csv", BC); bchanged = False
        decided = set(B.key)
        for r in P.itertuples():
            if r.key in decided: continue
            if NOW < pd.Timestamp(r.date) - pd.Timedelta(hours=3): continue          # before 9 PM ET the night before
            v4 = v4_now(r.date, r.home, r.away)
            if v4 is None: continue                                                 # wait for the live model's number
            if not dk_confirmed(r.date, r.home, r.away, r.dk_now): continue         # Nov 5, 2026: not bettable at DraftKings yet; decide when it is
            fair = bw["a"] + bw["w_v4"] * v4 + bw["w_mkt_exp_close"] * (r.dk_now + r.pred)
            edge = fair - r.dk_now; side = "over" if edge > 0 else "under"
            px = r.price_o if side == "over" else r.price_u
            H, Aw = r.home.upper(), r.away.upper(); tip_txt = f"{pd.Timestamp(r.tip):%a %-I:%M %p}"
            skip = "" if abs(edge) >= bw.get("bet_edge", 2.0) else "no bet (edge under 2)"
            if not skip:
                m4 = v4_alert(r.date, r.home, r.away)
                mv = A[(A.key == r.key) & A.pushed.astype(str).isin(["True", "1", "1.0"])]
                if m4 and m4[0] != side: skip = f"conflict: main totals model has a BET on {m4[0].upper()} {m4[1]:g}"
                elif m4: skip = f"same side as the main totals model's BET ({m4[0].upper()} {m4[1]:g}); not sent twice"
                elif len(mv) and str(mv.side.iloc[-1]) != side: skip = f"conflict: movement rule has a BET on {str(mv.side.iloc[-1]).upper()}"
                elif len(mv): skip = "same side as the movement rule's BET; not sent twice"
            fdt, fdl, best = None, None, None
            if not skip:
                try:
                    fdt, fdl, best = fanduel.compare("nba", r.date, r.home, r.away, "total", side, float(r.dk_now), px, label=side,
                                                     edge=abs(edge), need=2.0)
                except Exception as ex:
                    p("FanDuel compare failed:", type(ex).__name__)
                if px is not None and not pd.isna(px) and float(px) < AL.MAX_PRICE:
                    ok = None
                    try: ok = fanduel.same_or_better("nba", r.date, r.home, r.away, "total", side, float(r.dk_now), AL.MAX_PRICE)
                    except Exception: pass
                    if ok is None: skip = f"price {int(px):+d} worse than {AL.MAX_PRICE} and FanDuel no better"
            what = f"{side.upper()} {r.dk_now:g}{price_txt(px)}"; sent = False
            if not skip:
                body = (f"PROVISIONAL (market models blend v1; own record and stop rule). Our model (v4) {v4:.1f} and the market's "
                        f"expected close {r.dk_now + r.pred:.1f} blend to a fair total of {fair:.1f}, {abs(edge):.1f} pts "
                        f"{'above' if edge > 0 else 'below'} DraftKings {r.dk_now:g}: bet {side.upper()}. Tip {tip_txt}.\n"
                        f"Backtest 2025-26 (honest timing): 257 bets, beat the close by 1.44 pts (break-even 1.07), +1.8u. Unproven.")
                if fdt: body = fdt + "\n" + body
                try:
                    sent = AL.notify(f"BET {what} (PROVISIONAL blend): {Aw} @ {H}, {tip_txt}", body, priority="high",
                                     tags="scales", kind="bet", dk=dk_total_link(r.date, r.home, r.away, side, float(r.dk_now)), fd=fdl, best=best)
                except Exception as ex:
                    skip = f"NOT sent: ntfy error ({type(ex).__name__})"
            gid = np.nan
            R27 = results_2027(); g = R27[(R27.date == r.date) & (R27.home == r.home) & (R27.away == r.away)]
            if len(g): gid = g.game_id.iloc[0]
            row = dict(key=r.key, date=r.date, home=r.home, away=r.away, tip_et=str(r.tip)[:16], game_id=gid, alerted_at_et=str(NOW)[:16],
                       snap_et=str(r.snap)[:19], lead_h=round(r.lead_now, 2), side=side, line=r.dk_now, price=px, pred_move=round(r.pred, 2),
                       dk_first_seen=r.dk_open_point, opener_pred=round(r.dk_opred, 2), pin_now=np.nan, fd_now=r.pt_fanduel,
                       fd_line_txt=(fdt or "")[:200], pushed=bool(sent), skip_reason=skip,
                       tier=BLEND_TIER if abs(edge) >= bw.get("bet_edge", 2.0) else "blend_no_bet",
                       v4=round(v4, 2), fair=round(fair, 2), edge=round(edge, 2))
            B = pd.concat([B, pd.DataFrame([row])], ignore_index=True); bchanged = True
            p("BLEND " + ("SENT " if sent else "RECORDED ") + f"{what} {Aw} @ {H} | fair {fair:.1f}, edge {edge:+.2f}" + (f" | {skip}" if skip else ""))
        # follow-ups for sent, unlogged blend bets: DON'T BET when the edge at DK now is under break-even, spaced reminders otherwise
        for i, r in B.iterrows():
            if str(r.pushed) not in ("True", "1", "1.0") or isinstance(r.stopped_at_et, str) or isinstance(r.result, str): continue
            if r.key not in set(P.key) or pd.Timestamp(r.tip_et) <= NOW or logged(r.date, r.home, r.away): continue
            q = P[P.key == r.key].iloc[0]; v4 = v4_now(r.date, r.home, r.away)
            if v4 is None: continue
            fair = bw["a"] + bw["w_v4"] * v4 + bw["w_mkt_exp_close"] * (q.dk_now + q.pred)
            e_side = (fair - q.dk_now) * (1 if r.side == "over" else -1)
            H, Aw = str(r.home).upper(), str(r.away).upper(); what = f"{str(r.side).upper()} {float(r.line):g}"
            if e_side < BLEND_STOP:
                AL.notify(f"DON'T BET - {what} (PROVISIONAL blend): {Aw} @ {H}",
                          f"DON'T BET: the blend's edge at DraftKings {q.dk_now:g} is now {e_side:+.1f} pts (alerted {float(r.line):g}, "
                          f"edge {abs(float(r.edge)):.1f}). No bet is logged for it. If you did bet it, log it and ignore this.",
                          priority="high", tags="no_entry", kind="stop")
                B.loc[i, "stopped_at_et"] = str(NOW)[:16]; bchanged = True; continue
            # reminder while the edge AT TODAY'S LINE is still 2+ (a 9 PM alert slept through still gets a 6 AM reminder, at the new line)
            if e_side < 2.0 or not (AL.REMIND_HOURS[0] <= NOW.hour < AL.REMIND_HOURS[1]): continue
            if not dk_confirmed(r.date, r.home, r.away, q.dk_now): continue
            lastr = r.reminded_at_et if isinstance(r.reminded_at_et, str) else r.alerted_at_et
            if (NOW - pd.Timestamp(lastr)).total_seconds() / 60 < AL.remind_gap_min(r.tip_et, NOW): continue
            AL.notify(f"REMINDER - BET {str(r.side).upper()} {q.dk_now:g} (PROVISIONAL blend): {Aw} @ {H}",
                      f"REMINDER: still a BET and not logged yet. DraftKings now {q.dk_now:g} (alerted {float(r.line):g}); blend edge "
                      f"{e_side:+.1f} pts. Tip {pd.Timestamp(r.tip_et):%a %-I:%M %p}. If you already bet it, log it to stop these.",
                      priority="default", tags="alarm_clock", kind="bet",
                      dk=dk_total_link(r.date, r.home, r.away, r.side, float(q.dk_now)),
                      **fd_extra(r, r.side, float(q.dk_now)))
            B.loc[i, "reminded_at_et"] = str(NOW)[:16]; bchanged = True
        if bchanged: save_csv(B[BC], os.path.join(SD, "blend_alerts.csv"))

    # follow-ups for sent, unlogged, not-stopped alerts: DON'T BET when the predicted move is gone, spaced reminders otherwise
    pred_now = dict(zip(P.key, P.pred)); line_now = dict(zip(P.key, P.dk_now))
    for i, r in A.iterrows():
        if str(r.pushed) not in ("True", "1", "1.0") or isinstance(r.stopped_at_et, str) or isinstance(r.result, str): continue
        if r.key not in pred_now: continue
        if pd.Timestamp(r.tip_et) <= NOW: continue
        if logged(r.date, r.home, r.away): continue
        sgn = 1 if r.side == "over" else -1
        mv = sgn * pred_now[r.key]; cur = line_now[r.key]
        H, Aw = str(r.home).upper(), str(r.away).upper()
        what = f"{str(r.side).upper()} {float(r.line):g}"
        if mv < STOP_MOVE:
            AL.notify(f"DON'T BET - {what} (PROVISIONAL movement): {Aw} @ {H}",
                      f"DON'T BET: the movement model no longer expects more movement your way from here (predicted {mv:+.1f} pts now; "
                      f"DraftKings {cur:g}, alerted {float(r.line):g}). No bet is logged for it. If you did bet it, log it and ignore this.",
                      priority="high", tags="no_entry", kind="stop")
            A.loc[i, "stopped_at_et"] = str(NOW)[:16]; changed = True; p("DON'T BET:", what, Aw, "@", H); continue
        worse = (cur > float(r.line)) if r.side == "over" else (cur < float(r.line))
        if mv < REMIND_MOVE or worse: continue
        if not dk_confirmed(r.date, r.home, r.away, cur): continue                 # Nov 5, 2026: no reminder for a line DraftKings doesn't offer
        if not (AL.REMIND_HOURS[0] <= NOW.hour < AL.REMIND_HOURS[1]): continue
        lastr = r.reminded_at_et if isinstance(r.reminded_at_et, str) else r.alerted_at_et
        if (NOW - pd.Timestamp(lastr)).total_seconds() / 60 < AL.remind_gap_min(r.tip_et, NOW): continue
        AL.notify(f"REMINDER - BET {str(r.side).upper()} {cur:g} (PROVISIONAL movement): {Aw} @ {H}",
                  f"REMINDER: still a BET and not logged yet. DraftKings now {cur:g} (alerted {float(r.line):g}); predicted move "
                  f"{mv:+.1f} pts your way. Tip {pd.Timestamp(r.tip_et):%a %-I:%M %p}. If you already bet it, log it to stop these.",
                  priority="default", tags="alarm_clock", kind="bet",
                  dk=dk_total_link(r.date, r.home, r.away, r.side, float(cur)), **fd_extra(r, r.side, float(cur)))
        A.loc[i, "reminded_at_et"] = str(NOW)[:16]; changed = True
    if changed: save_csv(A[A_COLS], os.path.join(SD, "movement_alerts.csv"))
    p(f"checked {len(P)} games; {int((P.pred.abs() >= BET_MOVE).sum())} at a 1.5+ predicted move")


# ------------------------------------------------------------------ grade (morning)
def grade(name="movement_alerts.csv", cols=None):
    cols = A_COLS if cols is None else cols
    A = load_alerts(name, cols)
    if not len(A): p(f"no rows to grade in {name}"); return
    todo = A[A.result.isna() & (pd.to_datetime(A.tip_et) < NOW)]
    if not len(todo): p("nothing to grade"); return
    R27 = results_2027()
    # DraftKings close = its last full-game total before tip in the Action Network pregame files (change-only, every minute)
    closes = {}
    dates = sorted({str(x)[:10] for x in todo.date})
    fs = [os.path.join(PREGAME, f"{x}.csv") for x in dates]
    an = pd.concat([pd.read_csv(f) for f in fs if os.path.exists(f)], ignore_index=True) if any(os.path.exists(f) for f in fs) else pd.DataFrame()
    if len(an):
        x = an[(an.book == "DraftKings") & (an.period == "event") & (an.market == "total") & (an.side == "over")].dropna(subset=["value"]).copy()
        x = x[pd.to_datetime(x.seen_at_et) < pd.to_datetime(x.start_et)]
        x["key"] = x.date + "|" + x.home + "|" + x.away
        closes = x.sort_values("seen_at_et").groupby("key").value.last().to_dict()
    for i, r in todo.iterrows():
        g = R27[(R27.date == r.date) & (R27.home == r.home) & (R27.away == r.away)]
        if not len(g) or pd.isna(g.home_pts.iloc[0]): continue
        hp, ap = float(g.home_pts.iloc[0]), float(g.away_pts.iloc[0]); tot = hp + ap
        close = closes.get(r.key, g.close_total.iloc[0])
        line = float(r.line); over = r.side == "over"
        res = "P" if tot == line else ("W" if (tot > line) == over else "L")
        px = r.price if not pd.isna(r.price) else -110
        u = 0.0 if res == "P" else ((px / 100 if px > 0 else 100 / -px) if res == "W" else -1.0)
        A.loc[i, ["home_pts", "away_pts", "result", "units", "closing_line"]] = [hp, ap, res, round(u, 3), close]
        A.loc[i, "clv_points"] = (close - line) if over else (line - close)
        if pd.isna(A.loc[i, "game_id"]): A.loc[i, "game_id"] = g.game_id.iloc[0]
    save_csv(A[cols], os.path.join(SD, name))
    g = A[A.result.isin(["W", "L", "P"]) & (A.tier.astype(str) != "blend_no_bet")]
    p(f"graded {name}: {len(g)} rows, {int((g.result == 'W').sum())}-{int((g.result == 'L').sum())}-{int((g.result == 'P').sum())}, "
      f"{g.units.astype(float).sum():+.2f}u, CLV {pd.to_numeric(g.clv_points).mean():+.2f}")




def grade_all():
    grade()
    grade("blend_alerts.csv", A_COLS + B_EXTRA)


if __name__ == "__main__":
    {"fit": fit, "check": check, "grade": grade_all}[MODE]()
