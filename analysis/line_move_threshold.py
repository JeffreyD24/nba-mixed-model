"""Line-move threshold test (Nov 4, 2026). Pre-registered in analysis/LINE_MOVE_PREREG.md (commit f60b0e5) before any result.
Question: the live rule passes when the line moved 0.5+ against the model since DraftKings' open. Too strict? Does an early move
differ from a later one? Do lines that move against us swing back?

Main set: DraftKings 2023-24..2025-26 (descriptive, these seasons built the live models), live totals number and live spread number
from _tmp/rule_audit_R8.csv (analysis/rule_audit_injury_timing.py) and the spread rules of analysis/rule_audit_spreads.py.
Line path: DraftKings rows of data/odds_history/nba_snapshots.csv.gz. Out of sample: SBR 2013-14..2021-22 open/close with Model 1.

Coordinates: every line is measured in "points toward our bet" from the opener (positive = the market moved to the model, negative =
moved against). Bet side is fixed at the opener (edge 3+ with the previous game's report). Grading at -110; CLV = how far the close
moved toward the bet beyond the line we bet.
  python analysis/line_move_threshold.py WORKDIR -> analysis/line_move_threshold_output.txt, analysis/line_move_threshold_bets.csv"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

# ------------------------------------------------------------------ DraftKings line paths
R = pd.read_csv(os.path.join(W, "_tmp", "rule_audit_R8.csv"))
key = ["date", "home", "away"]
S = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "t", "tip", "book", "tot", "sp", "date"])
S = S[S.book == "draftkings"].copy()
S["t"] = pd.to_datetime(S.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
S["tip"] = pd.to_datetime(S.tip, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
S = S[S.t < S.tip].sort_values("t")

def paths(col):
    x = S[S[col].notna()][key + ["t", "tip", col]]
    return {k: g for k, g in x.groupby(key)}
PT, PS = paths("tot"), paths("sp")

# ------------------------------------------------------------------ spread model + live windows (copied from rule_audit_spreads.py)
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
FORM_W, ROSTER_W = 0.11, 0.57
rows = []
for r in T.itertuples():
    rows += [dict(season=r.season, date=r.date, team=r.home, mg=r.home_pts - r.away_pts),
             dict(season=r.season, date=r.date, team=r.away, mg=r.away_pts - r.home_pts)]
L = pd.DataFrame(rows); L["d"] = pd.to_datetime(L.date)
hist = {k: g.sort_values("d") for k, g in L.groupby(["season", "team"])}
def form(season, team, d):
    g = hist.get((season, team)); g = g[g.d < d - pd.Timedelta(days=1)]
    return (g.mg.tail(10).mean() - g.mg.mean()) if len(g) >= 10 else np.nan
R["d"] = pd.to_datetime(R.date)
R["fm"] = [form(s, h, d) - form(s, a, d) for s, h, a, d in zip(R.season, R.home, R.away, R.d)]
RS = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))[["date", "team", "delta", "games"]]
for side in ("home", "away"):
    R = R.merge(RS.rename(columns={"team": side, "delta": f"{side}_rd", "games": f"{side}_rg"}), on=["date", side], how="left")
R["adj"] = FORM_W * R.fm.fillna(0) + ROSTER_W * (R.home_rd - R.away_rd).fillna(0)
ready = R.fm.notna() & (R.home_rg >= 10) & (R.away_rg >= 10)
R["m8"] = R.pred_margin + R.adj; R["ms"] = R.pm_stale + R.adj
G = pd.read_csv(os.path.join(W, "analysis", "late_season_games.csv"))[key + ["h_cat", "a_cat", "h_arr", "a_arr"]]
R = R.merge(G, on=key, how="left")
late = R.d.dt.month.isin([2, 3, 4])
e0 = R.ms + R.open_spread; home = e0 > 0
dog = home & (R.open_spread > 0)
us_cat = np.where(home, R.h_cat, R.a_cat); them_cat = np.where(home, R.a_cat, R.h_cat); us_arr = np.where(home, R.h_arr, R.a_arr)
trap = (us_cat == "tanking") | (them_cat == "middle") | (pd.Series(us_arr).fillna(0).values > 0)
R["sp_ok"] = (ready & ((~late & ~dog) | (late & ~trap))).values

# ------------------------------------------------------------------ one row per bet
def build(market):
    bets = []
    for r in R.itertuples(index=False):
        if market == "total":
            if pd.isna(r.tot_stale) or pd.isna(r.open_total): continue
            e_open = r.tot_stale - r.open_total
            if abs(e_open) < 3: continue
            s = np.sign(e_open); tow = lambda ln: s * (ln - r.open_total)              # +: line moved to the model
            res = lambda ln: s * (r.act - ln); edge_now = lambda ln: s * (r.tot_model - ln); edge_stale = lambda ln: s * (r.tot_stale - ln)
            news = s * (r.tot_model - r.tot_stale); P = PT.get((r.date, r.home, r.away)); col = "tot"; o = r.open_total
        else:
            if not r.sp_ok or pd.isna(r.ms) or pd.isna(r.open_spread): continue
            e_open = r.ms + r.open_spread
            if abs(e_open) < 3: continue
            s = np.sign(e_open); tow = lambda ln: -s * (ln - r.open_spread)
            res = lambda ln: s * ((r.home_pts - r.away_pts) + ln); edge_now = lambda ln: s * (r.m8 + ln); edge_stale = lambda ln: s * (r.ms + ln)
            news = s * (r.m8 - r.ms); P = PS.get((r.date, r.home, r.away)); col = "sp"; o = r.open_spread
        if P is None or len(P) == 0: continue
        t0 = P.t.iloc[0]; first = P[col].iloc[0]
        gd = pd.Timestamp(r.date)
        def at(ts):                       # last line at or before ts
            q = P[P.t <= ts]; return q[col].iloc[-1] if len(q) else np.nan
        early_q = P[(P.t >= t0 + pd.Timedelta(minutes=30)) & (P.t <= t0 + pd.Timedelta(minutes=90))]
        early = early_q[col].iloc[0] if len(early_q) else np.nan
        mv = np.array([tow(v) for v in P[col].values])
        hit = np.where(mv <= -0.5)[0]
        t_against = (P.t.iloc[hit[0]] - t0).total_seconds() / 60 if len(hit) else np.nan
        row = dict(market=market, season=r.season, date=r.date, home=r.home, away=r.away, side=s, open=o, snap_open=first,
                   open_t=t0, tip=P.tip.iloc[0], news=news, mins_to_against=t_against, n_snaps=len(P),
                   min_tow=mv.min(), max_tow=mv.max())
        for name, ln in [("early", early), ("l9pm", at(gd - pd.Timedelta(hours=3))), ("l9am", at(gd + pd.Timedelta(hours=9))),
                         ("close", P[col].iloc[-1])]:
            row[f"{name}_line"] = ln; row[f"{name}_tow"] = tow(ln) if pd.notna(ln) else np.nan
            row[f"{name}_res"] = res(ln) if pd.notna(ln) else np.nan
            row[f"{name}_edge"] = (edge_stale(ln) if name == "early" else edge_now(ln)) if pd.notna(ln) else np.nan   # early lines mostly precede the 8 PM report
        row["open_res"] = res(o); row["close_tow_open"] = tow(P[col].iloc[-1])
        bets.append(row)
    B = pd.DataFrame(bets)
    for name in ("early", "l9pm", "l9am"):
        B[f"{name}_clv"] = B.close_tow - B[f"{name}_tow"]
    B["open_clv"] = B.close_tow
    return B

B = pd.concat([build("total"), build("spread")], ignore_index=True)
B.to_csv(os.path.join(W, "analysis", "line_move_threshold_bets.csv"), index=False)

def grade(res, clv=None, season=None):
    res = res.dropna(); w, l = int((res > 0).sum()), int((res < 0).sum()); u = w * 100 / 110 - l
    by = ""
    if season is not None:
        bys = []
        for s in (2024, 2025, 2026):
            rs = res[season.loc[res.index] == s]; bys.append(f"{int((rs > 0).sum()) * 100 / 110 - int((rs < 0).sum()):+.1f}")
        by = f"  seasons {', '.join(bys)}"
    c = f"  CLV {clv.loc[res.index].mean():+.2f}" if clv is not None and len(res) else ""
    return f"{w + l:5d} bets {w / max(w + l, 1):6.1%} {u:+7.1f}u ({u / max(w + l, 1) * 100:+5.1f}/100){c}{by}"

BUCKETS = [("unmoved", 0.0, 0.0), ("toward 0.5+", 0.5, 99), ("against 0.5", -0.5, -0.5), ("against 1.0", -1.0, -1.0),
           ("against 1.5", -1.5, -1.5), ("against 2.0-2.5", -2.5, -2.0), ("against 3+", -99, -3.0)]
def bucket_mask(tow, lo, hi):
    if lo == hi: return (tow - lo).abs() < 0.26
    return (tow >= min(lo, hi) - 0.01) & (tow <= max(lo, hi) + 0.01)

for mk in ("total", "spread"):
    D = B[B.market == mk]
    say(f"\n================ NBA {mk.upper()}S, DraftKings 2023-26 (in-sample), {len(D)} opener bets with edge 3+ ================")
    say(f"snapshot opener matches the recorded opener: {(D.snap_open == D.open).mean():.0%}; early line (30-90 min after open) found: "
        f"{D.early_line.notna().mean():.0%}; median snapshots per game {D.n_snaps.median():.0f}")
    say(f"reference: bet every opener: {grade(D.open_res, D.open_clv, D.season)}")
    say("\nT1 size of the move since the open, betting the line at that time (side fixed at the opener; model edge must still be 3+ same side)")
    for name, lab in [("early", "early line (30-90 min after open)"), ("l9pm", "9 PM night before"), ("l9am", "9 AM game day"), ("close", "closing line")]:
        say(f"  {lab}")
        for bl, lo, hi in BUCKETS:
            m = bucket_mask(D[f"{name}_tow"], lo, hi) & (D[f"{name}_edge"] >= 3)
            clv = D[f"{name}_clv"] if name != "close" else None
            say(f"    {bl:<16} {grade(D[f'{name}_res'][m], clv, D.season)}")
    say("\n  decision buckets (pre-registered: '0.5 to under X against', bet at the line when FIRST seen at the early, 9 PM or 9 AM check)")
    for X in (1.0, 1.5, 2.0):
        res_, clv_, idx_ = [], [], []
        for i, r_ in D.iterrows():
            for name in ("early", "l9pm", "l9am"):
                tw_ = r_[f"{name}_tow"]
                if pd.notna(tw_) and tw_ <= -0.5 and tw_ > -X and r_[f"{name}_edge"] >= 3:
                    res_.append(r_[f"{name}_res"]); clv_.append(r_[f"{name}_clv"]); idx_.append(i); break
        say(f"    0.5 to under {X} against: {grade(pd.Series(res_, index=idx_), pd.Series(clv_, index=idx_), D.season)}")
    res_, clv_, idx_ = [], [], []
    for i, r_ in D.iterrows():
        for name in ("early", "l9pm", "l9am"):
            tw_ = r_[f"{name}_tow"]
            if pd.notna(tw_) and tw_ <= -0.5 and r_[f"{name}_edge"] >= 3:
                if abs(tw_ + 1.0) < 0.26: res_.append(r_[f"{name}_res"]); clv_.append(r_[f"{name}_clv"]); idx_.append(i)
                break
    say(f"    exactly 1.0 against when first seen (added after review, the live-relevant step): {grade(pd.Series(res_, index=idx_, dtype=float), pd.Series(clv_, index=idx_, dtype=float), D.season)}")
    say("    (DraftKings has posted only half-point totals and spreads since Oct 2025, so live moves come in whole points: a 0.5 move")
    say("     cannot happen any more and the smallest real loosening is to allow 1.0-pt moves, i.e. X=1.5.)")
    say("\nT2 timing: when did the line first reach 0.5+ against? (graded at the 9 AM line and at the close; edge 3+ at that line)")
    ag = D.mins_to_against.notna()
    for lab, m in [("within 90 min of the open", ag & (D.mins_to_against <= 90)), ("90 min to 6 h", ag & (D.mins_to_against > 90) & (D.mins_to_against <= 360)),
                   ("6 h+ after the open", ag & (D.mins_to_against > 360)), ("never moved 0.5 against", ~ag)]:
        m9 = m & (D.l9am_edge >= 3); mc = m & (D.close_edge >= 3)
        say(f"  {lab:<28} n={int(m.sum()):4d} | 9 AM: {grade(D.l9am_res[m9], D.l9am_clv, D.season)}")
        say(f"  {'':<28}        | close: {grade(D.close_res[mc], None, D.season)} | at the opener: {grade(D.open_res[m])}")
    say("\nT3 swing-back: lines 0.5+ against at the early line (30-90 min after open)")
    E = D[D.early_tow <= -0.5]
    if len(E):
        say(f"  n={len(E)}; by the close: back to the opener or better {(E.close_tow >= 0).mean():.0%}, partly back {((E.close_tow > E.early_tow) & (E.close_tow < 0)).mean():.0%}, "
            f"same {(E.close_tow == E.early_tow).mean():.0%}, further against {(E.close_tow < E.early_tow).mean():.0%}")
        say(f"  avg CLV of betting the early moved line: {E.early_clv.mean():+.2f} pts (positive = the line came back after we bet)")
        say(f"  bet the early moved line: {grade(E.early_res[E.early_edge >= 3], E.early_clv, D.season)}")
        say(f"  wait and bet the close:   {grade(E.close_res[E.close_edge >= 3], None, D.season)}")
    U = D[D.early_tow.abs() < 0.5]
    say(f"  reference, unmoved at the early line (n={len(U)}): close back below the opener {(U.close_tow < 0).mean():.0%}, above {(U.close_tow > 0).mean():.0%}")
    say("\nT4 news: lines 0.5+ against at 9 AM, split by whether the 8 PM report moved the model 1+ pt the same way as the line")
    A = D[(D.l9am_tow <= -0.5) & (D.l9am_edge >= 3)]
    for lab, m in [("news (model also moved against 1+)", A.news <= -1), ("no news (model steady or moved toward)", A.news > -1)]:
        say(f"  {lab:<40} {grade(A.l9am_res[m], A.l9am_clv, A.season)}")
    say(f"  (all 9 AM against-moved lines with edge still 3+ on the 8 PM report: {grade(A.l9am_res, A.l9am_clv, A.season)})")
    say(f"  news share among against-moved: {(A.news <= -1).mean():.0%}; among unmoved/toward at 9 AM: "
        f"{(D[(D.l9am_tow > -0.5)].news <= -1).mean():.0%}")

# ------------------------------------------------------------------ out of sample: SBR open -> close, Model 1, 2013-14..2021-22
src = open(os.path.join(W, "analysis", "old_seasons_sbr.py")).read().split("\ndef predict")[0]
ns = {"__name__": "sbr", "sys": sys}
argv = sys.argv; sys.argv = [argv[0], W]
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "sbr", "exec"), ns)
sys.argv = argv
with contextlib.redirect_stdout(io.StringIO()): SB, _ = ns["build"]()
OB = pd.read_csv(os.path.join(W, "analysis", "old_seasons_sbr_bets.csv"))
OB = OB[OB.trusted == 1].merge(SB, on=["season", "date", "home", "away"], how="left")
s = np.sign(OB.edge)
OB["tow"] = np.where(OB.market == "total", s * (OB.total - OB.open_total), -s * (OB.spread - OB.open_spread))
OB["res_close"] = np.where(OB.market == "total", s * (OB.home_pts + OB.away_pts - OB.total), s * (OB.home_pts - OB.away_pts + OB.spread))
OB["edge_close"] = np.abs(OB.edge) - OB.tow          # Model 1 edge at the close, same side
def g2(r):
    r = r.dropna(); w, l = int((r > 0).sum()), int((r < 0).sum()); u = w * 100 / 110 - l
    return f"{w + l:5d} bets {w / max(w + l, 1):6.1%} {u:+7.1f}u ({u / max(w + l, 1) * 100:+5.1f}/100)"
say("\n================ OUT OF SAMPLE: SBR 2013-14..2021-22, Model 1 (no injuries), opener edge 3+, move open -> close ================")
for mk in ("total", "spread"):
    for lab, X in [("all seasons", OB.season > 0), ("without 2019-20 and 2020-21", ~OB.season.isin([2020, 2021]))]:
        D = OB[(OB.market == mk) & X]
        say(f"  {mk.upper()}S, {lab}: {len(D)} bets; at the opener {g2(D.result)}")
        for bl, lo, hi in BUCKETS:
            m = bucket_mask(D.tow, lo, hi) & (D.edge_close >= 3)
            say(f"    {bl:<16} bet at the close: {g2(D.res_close[m])}   (same games at the opener: {g2(D.result[bucket_mask(D.tow, lo, hi)])})")
        for X_ in (1.0, 1.5, 2.0):
            m = (D.tow <= -0.5) & (D.tow > -X_) & (D.edge_close >= 3)
            say(f"    decision bucket 0.5 to under {X_} against, at the close: {g2(D.res_close[m])}")
open(os.path.join(W, "analysis", "line_move_threshold_output.txt"), "w").write("\n".join(out) + "\n")
