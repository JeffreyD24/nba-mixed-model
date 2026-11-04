"""Rule audit of the NFL alert path (Nov 4, 2026). Analysis only: nothing in nfl-mixed-model is changed.
For every gate in alert.py that blocks, delays or downgrades a bet, grade the bets it blocks vs the bets it keeps, using only
information available at the moment the bet would be placed:
  - the EARLY number (team model on the previous week's final report + player model) is what is known at the opener;
  - the FINAL number (this week's final injury report) only from final_report_due (Fri 4 PM ET for Sunday games);
  - lines are real DraftKings snapshots (data/odds_history/nfl/*.csv.gz, every ~3 h), taken at or before the bet time;
  - weather: 'no wx' = both components without weather (clean); 'gt wx' = game-time weather (leaks at the opener,
    roughly what a 1-2 day forecast knows on Friday/Sunday; MAV 1-day vs actual wind r=0.67).
Units at -110 unless stated; pushes dropped.
Finding added while writing this: 98% of DK "openers" are first seen ~a week BEFORE the early number can exist (it uses last week's
results via walk_forward's date < game date, and last week's final report), so the opener record is itself a look-ahead;
the first honest early bet is the Tuesday 10 AM ET line of game week (views 'tue' below).
  python analysis/rule_audit_nfl.py WORKDIR NFL_REPO  -> analysis/rule_audit_nfl_output.txt
Optional env RULE_AUDIT_CACHE=path.pkl caches the DraftKings snapshot table."""
import os, sys, glob
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
_argv = sys.argv[:]

# ---------------------------------------------------------------- 1. model numbers (reuse the leak test's exact construction)
src = open(os.path.join(W, "analysis", "nfl_weather_leak_test.py")).read().split("\nout = []")[0]
exec(src)                      # -> P with pt_w / pt_n (team model, EARLY number, +/- weather, late shrink), A_w / A_n (player model)
sys.argv = _argv
assert "pred_total" in P and "pred_margin" in P


def adjust_base(base_, feats):
    """same as the leak test's adjust(), on any base number (used for the FINAL-report team total)"""
    adj = base_.copy()
    for s in SEAS:
        te = P.season == s; tr = ~te
        a = base_[te].copy()
        if feats:
            b = np.linalg.lstsq(P.loc[tr, feats].values, (P.tp - base_)[tr].values, rcond=None)[0]; a = base_[te] + P.loc[te, feats].values @ b
        k_tr = tr & (P.late == 1); d_ = base_[k_tr] - P.o_tot[k_tr]; r_ = P.tp[k_tr] - P.o_tot[k_tr]; c = float((d_ * r_).sum() / (d_ * d_).sum())
        lt = te & (P.late == 1); a[lt] = P.o_tot[lt] + c * (a[lt] - P.o_tot[lt]); adj[te] = a
    return adj


baseF = P.pred_total.astype(float).fillna(P.pt)
P["ptF_w"] = adjust_base(baseF, ["wind_x", "cold_x"]); P["ptF_n"] = adjust_base(baseF, [])
for wx, a in (("w", "A_w"), ("n", "A_n")):
    P[f"tE_{wx}"] = (P[f"pt_{wx}"] + P[a]) / 2          # early blend (what the opener backtest uses)
    P[f"tF_{wx}"] = (P[f"ptF_{wx}"] + P[a]) / 2         # final-report blend (what the live alert has after Friday 4 PM)
P["mE"] = P.pm; P["mF"] = P.pred_margin.astype(float).fillna(P.pm)
P["margin"] = P.home_pts - P.away_pts

# ---------------------------------------------------------------- 2. DraftKings snapshots
NAME = {"Arizona Cardinals": "ari", "Atlanta Falcons": "atl", "Baltimore Ravens": "bal", "Buffalo Bills": "buf", "Carolina Panthers": "car",
        "Chicago Bears": "chi", "Cincinnati Bengals": "cin", "Cleveland Browns": "cle", "Dallas Cowboys": "dal", "Denver Broncos": "den",
        "Detroit Lions": "det", "Green Bay Packers": "gb", "Houston Texans": "hou", "Indianapolis Colts": "ind", "Jacksonville Jaguars": "jax",
        "Kansas City Chiefs": "kc", "Los Angeles Chargers": "lac", "Los Angeles Rams": "lar", "Las Vegas Raiders": "lv", "Oakland Raiders": "lv",
        "Miami Dolphins": "mia", "Minnesota Vikings": "min", "New England Patriots": "ne", "New Orleans Saints": "no", "New York Giants": "nyg",
        "New York Jets": "nyj", "Philadelphia Eagles": "phi", "Pittsburgh Steelers": "pit", "Seattle Seahawks": "sea", "San Francisco 49ers": "sf",
        "Tampa Bay Buccaneers": "tb", "Tennessee Titans": "ten", "Washington Football Team": "wsh", "Washington Commanders": "wsh", "Washington Redskins": "wsh"}
cache = os.environ.get("RULE_AUDIT_CACHE")
if cache and os.path.exists(cache):
    S = pd.read_pickle(cache)
else:
    parts = []
    for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nfl", "*.csv.gz"))):
        d = pd.read_csv(f, usecols=["snapshot_utc", "event_id", "commence_et", "home", "away", "book", "market", "outcome", "price", "point"])
        parts.append(d[(d.book == "draftkings") & d.market.isin(["spreads", "totals"])])
    d = pd.concat(parts).drop_duplicates(["snapshot_utc", "event_id", "market", "outcome"])
    d["t"] = pd.to_datetime(d.snapshot_utc, utc=True)
    d["tip"] = pd.to_datetime(d.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    d = d[d.t < d.tip]
    d["date"] = pd.to_datetime(d.commence_et).dt.strftime("%Y-%m-%d"); d["h"] = d.home.map(NAME); d["a"] = d.away.map(NAME)
    k = ["date", "h", "a", "t", "tip"]
    sp = d[(d.market == "spreads") & (d.outcome == d.home)][k + ["point", "price"]].rename(columns={"point": "sp", "price": "sp_ph"})
    spa = d[(d.market == "spreads") & (d.outcome == d.away)][k + ["price"]].rename(columns={"price": "sp_pa"})
    ov = d[(d.market == "totals") & (d.outcome == "Over")][k + ["point", "price"]].rename(columns={"point": "tot", "price": "po"})
    un = d[(d.market == "totals") & (d.outcome == "Under")][k + ["price"]].rename(columns={"price": "pu"})
    S = sp.merge(spa, on=k, how="outer").merge(ov, on=k, how="outer").merge(un, on=k, how="outer")
    S = S.rename(columns={"h": "home", "a": "away"}).sort_values("t").reset_index(drop=True)
    if cache: S.to_pickle(cache)
SN = {key: g.reset_index(drop=True) for key, g in S.groupby(["date", "home", "away"])}

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)


def due_utc(date):
    d = pd.Timestamp(date)
    t = d - pd.Timedelta(days=1 if d.dayofweek == 3 else 2) + pd.Timedelta(hours=16)       # alert.py / bif.final_report_due
    return t.tz_localize("America/New_York").tz_convert("UTC")


# ---------------------------------------------------------------- 3. per-game simulations
def won_units(r, px=None):
    if r > 0: return (100 / abs(px) if px is not None and px < 0 else (px / 100 if px is not None else 100 / 110))
    return -1.0 if r < 0 else 0.0


def price_of(row, market, side):
    if market == "total": return row.po if side > 0 else row.pu
    return row.sp_ph if side > 0 else row.sp_pa


def sim(market, model_early, model_final, thr, gate_against=True, use_early_after_due=False):
    """one row per game: opener bet (early number), and the live rule (first snapshot from final_report_due to kickoff
    with edge >= thr on the final number and, if gate_against, not moved 0.5+ against since the open)"""
    rows = []
    for i, g in P.iterrows():
        s = SN.get((g.date, g.home, g.away))
        if s is None: continue
        col = "tot" if market == "total" else "sp"
        s = s.dropna(subset=[col])
        if not len(s): continue
        y = g.tp if market == "total" else g.margin
        edge = (lambda m, L: m - L) if market == "total" else (lambda m, L: m + L)
        res = (lambda sg, L: sg * (y - L)) if market == "total" else (lambda sg, L: sg * (y + L))
        o = s.iloc[0]; L0 = float(o[col]); due = due_utc(g.date)
        r = dict(season=g.season, week=g.week, date=g.date, home=g.home, away=g.away, open=L0, close=float(s[col].iloc[-1]),
                 open_t=o.t, due=due)
        mE, mF = g[model_early], g[model_final]
        if pd.isna(mE) or pd.isna(mF): continue
        e0 = edge(mE, L0); sg0 = np.sign(e0)
        r.update(e_open=abs(e0), sg_open=sg0, res_open=res(sg0, L0), px_open=price_of(o, market, sg0),
                 clv_open=(sg0 * (r["close"] - L0) if market == "total" else sg0 * (L0 - r["close"])))
        # snapshot views at fixed times
        def at(T, forward=False):
            x = s[s.t >= T] if forward else s[s.t <= T]
            if not len(x): return None
            return x.iloc[0] if forward else x.iloc[-1]
        mid = at(due - pd.Timedelta(days=2))             # Wednesday 4 PM for Sunday games: early number only
        gd = pd.Timestamp(g.date)                        # Tuesday 10 AM ET of game week = first moment the EARLY number exists
        tue_t = (gd - pd.Timedelta(days=(gd.dayofweek - 1) % 7 or 7) + pd.Timedelta(hours=10)).tz_localize("America/New_York").tz_convert("UTC")
        r["tue_t"] = tue_t
        tue = at(tue_t)
        fri = at(due, forward=True)
        if fri is not None and fri.t >= fri.tip: fri = None
        pre = at(o.tip - pd.Timedelta(hours=3))
        for lab, row_, m in (("tue", tue, mE), ("mid", mid, mE), ("fri", fri, mF), ("pre", pre, mF), ("friE", fri, mE)):
            if row_ is None or (lab not in ("mid", "tue") and row_.t < due): r[f"e_{lab}"] = np.nan; continue
            L = float(row_[col]); e = edge(m, L); sg = np.sign(e)
            mv = (L - L0) if market == "total" else (L0 - L)          # + = moved toward the OVER / toward the HOME side... per side below
            smv = sg * mv if market == "total" else sg * (L - L0) * -1
            r.update({f"L_{lab}": L, f"e_{lab}": abs(e), f"sg_{lab}": sg, f"res_{lab}": res(sg, L), f"px_{lab}": price_of(row_, market, sg),
                      f"mv_{lab}": smv})
        # live rule: scan snapshots from due to kickoff
        after = s[s.t >= due]
        r["live"] = False
        for row_ in after.itertuples():
            L = float(getattr(row_, col)); e = edge(mE if use_early_after_due else mF, L); sg = np.sign(e)
            smv = sg * (L - L0) if market == "total" else -sg * (L - L0)
            if abs(e) < thr: continue
            if gate_against and smv <= -0.5: continue
            r.update(live=True, L_live=L, e_live=abs(e), sg_live=sg, res_live=res(sg, L), mv_live=smv, t_live=row_.t,
                     px_live=price_of(row_, market, sg))
            break
        # the bet the alert sends first after due with no move gate (to grade what the gate removes)
        r["anyb"] = False
        for row_ in after.itertuples():
            L = float(getattr(row_, col)); e = edge(mF, L); sg = np.sign(e)
            if abs(e) < thr: continue
            smv = sg * (L - L0) if market == "total" else -sg * (L - L0)
            r.update({"anyb": True, "L_any": L, "sg_any": sg, "res_any": res(sg, L), "mv_any": smv}); break
        rows.append(r)
    return pd.DataFrame(rows)


def rec(res, px=None):
    res = pd.Series(res).dropna()
    w, l = int((res > 0).sum()), int((res < 0).sum())
    if px is None: u = w * 100 / 110 - l
    else: u = sum(won_units(r_, p_) for r_, p_ in zip(res, pd.Series(px).loc[res.index]))
    return w, l, u


def line(lab, D, rcol, mask, px=None):
    x = D[mask]
    w, l, u = rec(x[rcol], x[px] if px else None)
    per = " ".join(f"{s % 100}:{rec(x[x.season == s][rcol], x[x.season == s][px] if px else None)[2]:+.1f}" for s in sorted(D.season.unique()))
    say(f"  {lab:52s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {u:+7.1f}u  [{per}]")


# ---------------------------------------------------------------- 4. TOTALS v2 (the live market)
for wx in ("n", "w"):
    T = sim("total", f"tE_{wx}", f"tF_{wx}", 2.0)
    wk = T.week.between(5, 14)
    say(f"\n================ TOTALS v2, weather = {'none (clean)' if wx == 'n' else 'game-time (leaks at the opener; ~forecast on Fri/Sun)'} ================")
    say(f"games with DK snapshots 2020-25: {len(T)}; Friday snapshot found after the report for {T.e_fri.notna().sum()}; "
        f"median opener posted {((T.due - T.open_t).dt.total_seconds() / 86400).median():.1f} days before the final report")
    say("R0 reproduction (opener = first DK snapshot, early number, edge 2+, weeks 5-14):")
    line("opener bet (what the backtest grades)", T, "res_open", wk & (T.e_open >= 2))
    say(f"  OPENER TIMING: DK opener first seen before Tue 10 AM of game week (i.e. before the previous week's games and final report "
        f"that the EARLY number uses) for {(T.open_t < T.tue_t).mean():.0%} of games; median {((T.tue_t - T.open_t).dt.total_seconds() / 86400).median():.1f} days earlier")
    say("R1 FINAL-INJURY-REPORT gate (no BET before final_report_due; opener can never be bet):")
    line("A. opener, early number (blocked live)", T, "res_open", wk & (T.e_open >= 2))
    line("A2. Tue 10 AM line, early number (first honest early bet)", T, "res_tue", wk & (T.e_tue >= 2))
    line("A3. opener bets, graded at the Tue 10 AM line instead", T.assign(rr=T.sg_open * T.res_tue * T.sg_tue), "rr", wk & (T.e_open >= 2))
    line("B. Wed 4 PM line, early number (also blocked)", T, "res_mid", wk & (T.e_mid >= 2))
    line("C. LIVE RULE: first check after report, final number, not vs", T, "res_live", wk & T.live)
    line("D. first check after report, final no., no move gate", T, "res_any", wk & T.anyb)
    line("E. Friday line, EARLY number (price effect only)", T, "res_friE", wk & (T.e_friE >= 2))
    line("F. opener bets that never become live bets", T, "res_open", wk & (T.e_open >= 2) & ~T.live)
    line("G. live bets that were NOT opener bets", T, "res_live", wk & T.live & (T.e_open < 2))
    say(f"  avg CLV of opener bets: {T[wk & (T.e_open >= 2)].clv_open.mean():+.2f} pts; share of opener bets still a live bet after the "
        f"report: {(T[wk & (T.e_open >= 2)].live).mean():.0%}; same side: {((T.sg_live == T.sg_open)[wk & (T.e_open >= 2) & T.live]).mean():.0%}")
    say("R2 AGAINST_MOVE 0.5 (PASS if moved 0.5+ against since open). Edge 2+ at that line; mv = move toward our side since open:")
    for lab, e, r_, m_ in (("Tue 10 AM, early number", "e_tue", "res_tue", "mv_tue"), ("Wed 4 PM, early number", "e_mid", "res_mid", "mv_mid"), ("first check after report, final number", "e_fri", "res_fri", "mv_fri"),
                           ("kickoff - 3 h, final number", "e_pre", "res_pre", "mv_pre")):
        say(f" {lab}:")
        base_m = wk & (T[e] >= 2)
        line("   moved 0.5+ AGAINST (gate blocks)", T, r_, base_m & (T[m_] <= -0.5))
        line("   unmoved (|move| < 0.5)", T, r_, base_m & (T[m_].abs() < 0.5))
        line("   moved 0.5+ TOWARD", T, r_, base_m & (T[m_] >= 0.5))
        line("   moved 1.5+ AGAINST", T, r_, base_m & (T[m_] <= -1.5))
    say("R3 EDGE THRESHOLD (TOTAL_THRESHOLD_BLEND 2.0), weeks 5-14:")
    for lab, e, r_ in (("opener/early", "e_open", "res_open"), ("Tue 10 AM/early", "e_tue", "res_tue"), ("after report/final (no move gate)", "e_fri", "res_fri")):
        for lo, hi in ((1.0, 1.5), (1.5, 2), (2, 2.5), (2.5, 3), (3, 4), (4, 99)):
            line(f"   {lab} edge {lo}-{hi}", T, r_, wk & T[e].between(lo, hi, inclusive="left"))
    say("R4 TOTAL_WEEKS 5-14 / LATE_WEEK 15 (weeks 1-4 and 15+ test-only), edge 2+:")
    for lab, m_ in (("weeks 1-4", T.week <= 4), ("weeks 5-14", wk), ("weeks 15-18", T.week.between(15, 18)), ("playoffs (19+)", T.week >= 19)):
        line(f"   opener/early  {lab}", T, "res_open", m_ & (T.e_open >= 2))
        line(f"   Tue 10 AM/early {lab}", T, "res_tue", m_ & (T.e_tue >= 2))
        line(f"   live rule     {lab}", T, "res_live", m_ & T.live)
    say("R5 MAX_PRICE -120 (live rule bets, actual DK price):")
    pxm = wk & T.live
    line("   live bets priced -120 or better (at price)", T, "res_live", pxm & (T.px_live >= -120), px="px_live")
    line("   live bets priced worse than -120 (blocked, at price)", T, "res_live", pxm & (T.px_live < -120), px="px_live")
    line("   opener bets priced worse than -120 (at price)", T, "res_open", wk & (T.e_open >= 2) & (T.px_open < -120), px="px_open")
    # R6 DON'T BET follow-up: live bets re-checked at kickoff - 3 h
    L_ = T[wk & T.live & T.e_pre.notna()].copy()
    L_["stop"] = (L_.sg_pre != L_.sg_live) | (L_.e_pre < 2) | (L_.mv_pre <= -0.5) | (L_.sg_live * (L_.L_pre - L_.L_live) <= -0.5)
    say("R6 DON'T BET follow-up (alerted, not yet bet; at kickoff - 3 h the edge fell under 2, side flipped, or line moved 0.5 against):")
    line("   stopped, graded at the alert line (had you bet at once)", L_, "res_live", L_.stop)
    L_["res_late_same"] = L_.sg_live * (L_.res_pre / L_.sg_pre)          # result of the ALERT side at the kickoff-3h line
    line("   stopped, alert side at the kickoff-3h line", L_, "res_late_same", L_.stop)
    line("   not stopped, graded at the alert line", L_, "res_live", ~L_.stop)
    if wx == "n": TN = T

# ---------------------------------------------------------------- 5. SPREADS (test-only), raw model, edge 3+
Sp = sim("spread", "mE", "mF", 3.0)
say("\n================ SPREADS (FULL_GAME_TEST_ONLY), edge 3+, all weeks 1-18 ================")
reg = Sp.week <= 18
line("opener, early number", Sp, "res_open", reg & (Sp.e_open >= 3))
line("Tue 10 AM line, early number", Sp, "res_tue", reg & (Sp.e_tue >= 3))
line("live rule (after report, final number, not moved against)", Sp, "res_live", reg & Sp.live)
line("after report, no move gate", Sp, "res_any", reg & Sp.anyb)
for lab, e, r_, m_ in (("Tue 10 AM, early", "e_tue", "res_tue", "mv_tue"), ("Wed 4 PM, early", "e_mid", "res_mid", "mv_mid"), ("after report, final", "e_fri", "res_fri", "mv_fri")):
    line(f"  {lab}: moved 0.5+ against", Sp, r_, reg & (Sp[e] >= 3) & (Sp[m_] <= -0.5))
    line(f"  {lab}: unmoved", Sp, r_, reg & (Sp[e] >= 3) & (Sp[m_].abs() < 0.5))
    line(f"  {lab}: moved 0.5+ toward", Sp, r_, reg & (Sp[e] >= 3) & (Sp[m_] >= 0.5))
line("weeks 5-14 opener", Sp, "res_open", Sp.week.between(5, 14) & (Sp.e_open >= 3))
line("weeks 15-18 opener", Sp, "res_open", Sp.week.between(15, 18) & (Sp.e_open >= 3))
line("weeks 5-14 Tue 10 AM", Sp, "res_tue", Sp.week.between(5, 14) & (Sp.e_tue >= 3))

# ---------------------------------------------------------------- 6. live firing counts this season (state/alerts.csv)
A = pd.read_csv(os.path.join(N, "state", "alerts.csv"))
say("\n================ LIVE: state/alerts.csv (2026, since Oct 30) ================")
say(f"rows {len(A)}; unique game-market rows {A.drop_duplicates(['game_id', 'market', 'skipped']).shape[0]} "
    f"(test-only rows are re-logged every check: {A[A.skipped.fillna('').str.startswith('test')].shape[0]} rows for "
    f"{A[A.skipped.fillna('').str.startswith('test')].game_id.nunique()} game)")
U = A.drop_duplicates(["game_id", "market", "skipped"]).copy()
U["gate"] = np.select([U.skipped.isna(), U.skipped.str.contains("final injury", na=False), U.skipped.str.contains("against", na=False),
                       U.skipped.str.startswith("test", na=False), U.skipped.str.contains("price", na=False), U.skipped.str.contains("ESPN", na=False)],
                      ["BET (pushed)", "final injury report not out", "moved 0.5+ against", "test-only", "price cap", "ESPN unavailable"], "other")
for (gname, mk), x in U.groupby(["gate", "market"]):
    gr = x[x.result.isin(["W", "L"])]
    say(f"  {gname:30s} {mk:6s} fired {len(x):3d}  graded {int((gr.result == 'W').sum())}-{int((gr.result == 'L').sum())}")
cl = U[U.gate == "final injury report not out"]
say(f"  of {len(cl)} report-gate cautions: later became a BET alert for the same game+market: "
    f"{sum(((A.game_id == r.game_id) & (A.market == r.market) & A.skipped.isna()).any() for r in cl.itertuples())}")
open(os.path.join(W, "analysis", "rule_audit_nfl_output.txt"), "w").write("\n".join(out) + "\n")
