"""NBA totals STACK: a side-by-side record next to the live totals model (v4). Started Nov 3, 2026 (user approved). v4 is unchanged.
The stack is the tournament's pick for totals (research/tournament/NBA_RESULTS.md: beat DraftKings' openers out of sample 2023-26,
1,647 bets 53.7% +42.5u, closing line moved +1.38 pts toward the bets). Coefficients frozen in data/stack_totals.json (fit on 2014-2022):
    edge = b0 + b1 (Model 1 - opener) + b2 (season avg game total - opener) + b3 form + b4 altitude + b5 both rested
    bet the over if edge >= threshold, the under if edge <= -threshold; graded at the DraftKings opener, 1 unit at -110.
Inputs, all known before the opener (results through two nights before the game, as in the backtest):
    Model 1 = the locked number in state/picks_log.csv (pred_total). Difference from the backtest: the live Model 1 includes the injury
              report; the backtested one had no injury features. Recorded here so the record can be read honestly.
    season avg game total = mean of (points for + against) per team this season, averaged over the two teams;
    form = sum over both teams of (last-10 mean game total - season mean); altitude = home team DEN or UTA;
    rested = neither team played the day before. Only games where both teams have 10+ games this season.
Writes state/picks_log_stack.csv and prints the stack record and the same-game comparison with v4's total alerts (state/alerts.csv).
  python stack_record.py WORKDIR"""
import os, sys, json
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); STATE = os.path.join(W, "state")
cfg = json.load(open(os.path.join(W, "data", "stack_totals.json"))); b = cfg["coef"]; thr = cfg["edge_threshold"]
P = pd.read_csv(os.path.join(STATE, "picks_log.csv"))
P["d"] = pd.to_datetime(P.date)
P = P.sort_values(["d", "game_id"]).drop_duplicates("game_id", keep="last").reset_index(drop=True)

# team game history from finished games in the log (this season only)
done = P[P.home_pts.notna() & P.away_pts.notna()]
hist = pd.concat([pd.DataFrame(dict(team=done.home, d=done.d, tot=done.home_pts + done.away_pts)),
                  pd.DataFrame(dict(team=done.away, d=done.d, tot=done.home_pts + done.away_pts))]).sort_values("d")
played = set(zip(pd.concat([P.home, P.away]), pd.concat([P.d, P.d])))      # schedule, finished or not


def team_stats(t, d):
    h = hist[(hist.team == t) & (hist.d < d - pd.Timedelta(days=1))].tot.values
    if not len(h): return 0, np.nan, np.nan
    return len(h), h.mean(), h[-10:].mean() - h.mean()


rows = []
for r in P.itertuples():
    nh, mh, fh = team_stats(r.home, r.d); na, ma, fa = team_stats(r.away, r.d)
    rested = float(((r.home, r.d - pd.Timedelta(days=1)) not in played) and ((r.away, r.d - pd.Timedelta(days=1)) not in played))
    alt = float(r.home in cfg["altitude_homes"])
    L = r.open_total
    ok = nh >= cfg["min_games_each"] and na >= cfg["min_games_each"] and pd.notna(L) and pd.notna(r.pred_total)
    edge = (b["intercept"] + b["model1_minus_line"] * (r.pred_total - L) + b["simple_minus_line"] * ((mh + ma) / 2 - L)
            + b["form"] * (fh + fa) + b["altitude"] * alt + b["rested"] * rested) if ok else np.nan
    side = "over" if ok and edge >= thr else ("under" if ok and edge <= -thr else "")
    res = ""
    if side and pd.notna(r.home_pts):
        pts = r.home_pts + r.away_pts
        res = "P" if pts == L else ("W" if (pts > L) == (side == "over") else "L")
    clv = (np.sign(edge) * (r.close_total - L)) if side and pd.notna(r.close_total) else np.nan
    rows.append(dict(game_id=r.game_id, date=r.date, home=r.home, away=r.away, pick_type=r.pick_type, open_total=L, close_total=r.close_total,
                     model1_total=r.pred_total, season_avg_total=round((mh + ma) / 2, 2) if nh and na else np.nan, form=round(fh + fa, 2) if nh and na else np.nan,
                     altitude=alt, rested=rested, n_home=nh, n_away=na, stack_edge=round(edge, 3) if ok else np.nan, threshold=thr,
                     side=side, result=res, clv_points=clv))
S = pd.DataFrame(rows)
S.to_csv(os.path.join(STATE, "picks_log_stack.csv"), index=False)

for lab, sub in (("all", S), ("live only", S[S.pick_type != "backfilled"])):
    bb = sub[sub.result.isin(["W", "L"])]
    w_, l_ = int((bb.result == "W").sum()), int((bb.result == "L").sum())
    print(f"NBA totals stack ({lab}): {w_}-{l_}, {w_ * 100 / 110 - l_:+.1f}u, CLV {bb.clv_points.mean():+.2f} pts "
          f"({int((sub.side != '').sum())} picks; games eligible {int(sub.stack_edge.notna().sum())} of {len(sub)})")

# same games, v4 total alerts that were sent (the live record), for the side-by-side view
try:
    A = pd.read_csv(os.path.join(STATE, "alerts.csv"))
    A = A[(A.market == "total") & (A.sent.astype(str) == "True")].drop_duplicates("game_id", keep="first")
    M = S[S.side != ""].merge(A[["game_id", "side", "result", "clv_points"]], on="game_id", how="outer", suffixes=("_stack", "_v4"))
    both = M.side_stack.notna() & M.side_v4.notna()
    print(f"same-game view: stack picks {int(M.side_stack.notna().sum())}, v4 alerts {int(M.side_v4.notna().sum())}, both {int(both.sum())} "
          f"(same side {int((both & (M.side_stack == M.side_v4)).sum())})")
    # checkpoint scoreboard (research/tournament/STACK_VS_V4_CHECKPOINT.md): stack-eligible games only, CLV in points
    elig = S[S.stack_edge.notna()][["game_id", "date", "side", "clv_points"]]
    V = A[A.game_id.isin(elig.game_id)][["game_id", "side", "clv_points"]].rename(columns={"side": "side_v4", "clv_points": "clv_v4"})
    C = elig.merge(V, on="game_id", how="left")
    so = C[(C.side != "") & C.side_v4.isna()].dropna(subset=["clv_points"])
    vo = C[(C.side == "") & C.side_v4.notna()].dropna(subset=["clv_v4"])
    st = C[C.side != ""].dropna(subset=["clv_points"]); v4 = C[C.side_v4.notna()].dropna(subset=["clv_v4"])
    print(f"checkpoint scoreboard: stack-only {len(so)} bets CLV {so.clv_points.mean():+.2f}, v4-only {len(vo)} bets CLV {vo.clv_v4.mean():+.2f}; "
          f"overall stack {len(st)} CLV {st.clv_points.mean():+.2f}, v4 {len(v4)} CLV {v4.clv_v4.mean():+.2f}")
    if len(so) >= 2 and len(vo) >= 2:
        rng = np.random.default_rng(7); days = np.union1d(so.date.unique(), vo.date.unique())
        a = so.groupby("date").clv_points.agg(["sum", "count"]).reindex(days, fill_value=0).values
        c = vo.groupby("date").clv_v4.agg(["sum", "count"]).reindex(days, fill_value=0).values
        diff = []
        for _ in range(4000):
            k = rng.integers(0, len(days), len(days))
            diff.append(a[k, 0].sum() / max(a[k, 1].sum(), 1) - c[k, 0].sum() / max(c[k, 1].sum(), 1))
        lo, hi = np.percentile(diff, [5, 95]); enough = len(so) >= 100 and len(vo) >= 100
        call = ("SWITCH to the stack (needs user approval)" if lo > 0 and st.clv_points.mean() >= v4.clv_v4.mean() else "keep v4") if enough else "not enough bets yet (100 each)"
        print(f"  stack-only minus v4-only CLV {so.clv_points.mean() - vo.clv_v4.mean():+.2f} [90% {lo:+.2f},{hi:+.2f}] -> {call}")
except Exception as e:
    print("v4 comparison skipped:", e)
