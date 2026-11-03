"""NBA model tournament (pre-registered in research/tournament/NBA_PREREG.md, commit 1fa4f26).
  python research/tournament/nba_tournament.py WORKDIR predict   # Model 1 (no injuries, one-day lag) for 2023-26 too -> _tmp
  python research/tournament/nba_tournament.py WORKDIR choose    # BUILD + CHOOSE results only (lockbox untouched)
  python research/tournament/nba_tournament.py WORKDIR lockbox   # score the picks on 2023-26 ONCE (refuses without picks file)
Needs analysis/old_seasons_sbr.py predict first (Model 1 preds 2014-2022 at SBR lines)."""
import os, sys, io, contextlib, json
import numpy as np, pandas as pd
from scipy.stats import norm
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W); sys.path.insert(0, os.path.join(W, "analysis"))
TMP = os.path.join(W, "_tmp"); OUT = os.path.join(W, "research", "tournament")
BUILD, CHOOSE, LOCK = [2014, 2015, 2016, 2017, 2018], [2019, 2020, 2021, 2022], [2023, 2024, 2025, 2026]
Z = norm.ppf(110 / 210)
sys.argv = [sys.argv[0], W, "x"] + sys.argv[2:]
import old_seasons_sbr as osb                       # reuse its SBR build (names, bubble dates, regular season)
MODE = sys.argv[3]


def games():
    """one row per regular-season game 2012-2026: scores, opener, closer (SBR <= 2022, DraftKings >= 2023)"""
    D, _ = osb.build()
    D = D.rename(columns={"spread": "close_spread", "total": "close_total"})
    T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
    T = T[T.season >= 2023][["date", "season", "home", "away", "home_pts", "away_pts"]]
    O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
    dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total", "close_spread", "close_total"]].drop_duplicates(["date", "home", "away"])
    T = T.merge(dk, on=["date", "home", "away"], how="left")
    T["spread_trusted"] = T.open_spread.notna().astype(int); T["total_trusted"] = T.open_total.notna().astype(int)
    G = pd.concat([D, T], ignore_index=True)
    G["date"] = pd.to_datetime(G.date)
    return G.sort_values("date").reset_index(drop=True)


def predict():
    G = games(); G["date"] = G.date.dt.strftime("%Y-%m-%d")
    src = open(os.path.join(W, "nba_mixed_model.py")).read()
    ns = {"__name__": "nm_lag"}
    exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=1)]"), "nm_lag", "exec"), ns)
    for test in LOCK:
        train = list(range(test - 4, test))
        D = G[G.season.isin(train + [test])].rename(columns={"close_spread": "spread", "close_total": "total"})
        with contextlib.redirect_stdout(io.StringIO()):
            _, P = ns["run"](D, train, test)
        P["season"] = test; P.to_csv(os.path.join(TMP, f"old_sbr_preds_{test}.csv"), index=False); print(test, flush=True)


# ---------------------------------------------------------------- candidates from box scores (all lagged one day)
def elo_and_simple(G):
    """Elo (538 NBA defaults, untuned) and season-to-date averages, each as of two nights before the game"""
    elo = {}; snap = []                                  # (date, dict copy) after each date
    hist = {}                                            # (season, team) -> list of (date, margin, pts_for, pts_against)
    rows = []
    last_season = None
    dates = sorted(G.date.unique())
    snaps = {}
    for d in dates:
        g = G[G.date == d]
        s = int(g.season.iloc[0])
        if s != last_season:                             # new season: 25% back toward 1505
            elo = {t: 0.75 * v + 0.25 * 1505 for t, v in elo.items()}; last_season = s
        snaps[d] = dict(elo)                             # ratings BEFORE this date's games
        for r in g.itertuples():
            eh, ea = elo.get(r.home, 1505.0), elo.get(r.away, 1505.0)
            if pd.isna(r.home_pts): continue
            mov = r.home_pts - r.away_pts
            exp = 1 / (1 + 10 ** (-(eh + 100 - ea) / 400))
            winner_diff = (eh + 100 - ea) if mov > 0 else (ea - eh - 100)
            mult = (abs(mov) + 3) ** 0.8 / (7.5 + 0.006 * winner_diff)
            ch = 20 * mult * ((mov > 0) - exp)
            elo[r.home] = eh + ch; elo[r.away] = ea - ch
            for t, m, pf, pa in ((r.home, mov, r.home_pts, r.away_pts), (r.away, -mov, r.away_pts, r.home_pts)):
                hist.setdefault((s, t), []).append((d, m, pf, pa))
    snap_dates = np.array(sorted(snaps))
    def elo_at(d):                                       # ratings before games of (d - 1 day): i.e. results through d - 2
        i = np.searchsorted(snap_dates, d - pd.Timedelta(days=1), side="right") - 1
        return snaps[snap_dates[max(i, 0)]]
    def team(s, t, d):
        h = [x for x in hist.get((s, t), []) if x[0] < d - pd.Timedelta(days=1)]
        if not h: return 0, np.nan, np.nan, np.nan, np.nan
        a = np.array([x[1:] for x in h], float)
        m10 = a[-10:, 0].mean() - a[:, 0].mean(); t10 = (a[-10:, 1] + a[-10:, 2]).mean() - (a[:, 1] + a[:, 2]).mean()
        return len(h), a[:, 0].mean(), (a[:, 1] + a[:, 2]).mean(), m10, t10
    for r in G.itertuples():
        e = elo_at(r.date); s = int(r.season)
        nh, mh, th, fmh, fth = team(s, r.home, r.date); na, ma, ta, fma, fta = team(s, r.away, r.date)
        rows.append(dict(i=r.Index, elo_margin=(e.get(r.home, 1505) + 100 - e.get(r.away, 1505)) / 28, n_home=nh, n_away=na,
                         simple_margin_raw=mh - ma, simple_total=(th + ta) / 2, form_sp=fmh - fma, form_tot=fth + fta))
    return G.join(pd.DataFrame(rows).set_index("i"))


def table():
    G = games()
    P = pd.concat([pd.read_csv(os.path.join(TMP, f"old_sbr_preds_{s}.csv")) for s in BUILD + CHOOSE + LOCK], ignore_index=True)
    P["date"] = pd.to_datetime(P.date)
    G = elo_and_simple(G)
    G = G.merge(P[["date", "home", "away", "pred_margin", "pred_total", "b2b_home", "b2b_away"]], on=["date", "home", "away"], how="inner")
    G = G[(G.n_home >= 10) & (G.n_away >= 10)].copy()
    hb = G[G.season.isin(BUILD)]; G["simple_margin"] = G.simple_margin_raw + float(((hb.home_pts - hb.away_pts) - hb.simple_margin_raw).mean())
    G["m1f_margin"] = G.pred_margin + 0.11 * G.form_sp; G["m1f_total"] = G.pred_total + 0.20 * G.form_tot
    G["alt"] = G.home.isin(["den", "utah"]).astype(float); G["rested"] = ((G.b2b_home == 0) & (G.b2b_away == 0)).astype(float)
    G["margin"] = G.home_pts - G.away_pts; G["pts"] = G.home_pts + G.away_pts
    return G


CANDS = {"spread": [("1 opener", None), ("2 Elo", "elo_margin"), ("3 simple averages", "simple_margin"), ("4 Model 1", "pred_margin"),
                    ("5 Model 1 + form", "m1f_margin"), ("6 stack", "STACK")],
         "total": [("1 opener", None), ("3 simple averages", "simple_total"), ("4 Model 1", "pred_total"),
                   ("5 Model 1 + form", "m1f_total"), ("6 stack", "STACK")]}
SIMPLICITY = {"3 simple averages": 1, "2 Elo": 2, "4 Model 1": 3, "5 Model 1 + form": 4, "6 stack": 5}


def mk_xy(D, mk):
    L = (-D.open_spread if mk == "spread" else D.open_total).values
    Lc = (-D.close_spread if mk == "spread" else D.close_total).values
    y = ((D.margin if mk == "spread" else D.pts).values - L)
    return L, Lc, y


def stack_X(D, mk, L):
    if mk == "spread":
        cols = [D.pred_margin.values - L, D.elo_margin.values - L, D.simple_margin.values - L, D.form_sp.values, D.rested.values]
    else:
        cols = [D.pred_total.values - L, D.simple_total.values - L, D.form_tot.values, D.alt.values, D.rested.values]
    return np.column_stack([np.ones(len(D))] + cols)


def fit(Dtr, mk, col):
    L, _, y = mk_xy(Dtr, mk); ok = ~np.isnan(y)
    if col is None: return ("none", 0.0, np.nanstd(y, ddof=1))
    if col == "STACK":
        X = stack_X(Dtr, mk, L); ok &= ~np.isnan(X).any(1)
        b = np.linalg.lstsq(X[ok], y[ok], rcond=None)[0]; return ("stack", b, np.std(y[ok] - X[ok] @ b, ddof=1))
    x = Dtr[col].values - L; ok &= ~np.isnan(x)
    w = (x[ok] @ y[ok]) / (x[ok] @ x[ok]); return ("w", w, np.std(y[ok] - w * x[ok], ddof=1))


def apply(Dte, mk, col, f):
    L, _, _ = mk_xy(Dte, mk)
    if f[0] == "none": return np.zeros(len(Dte))
    if f[0] == "stack": return stack_X(Dte, mk, L) @ f[1]
    return f[1] * (Dte[col].values - L)


def score(Dte, mk, edge, sd, n_boot=2000, seed=11):
    """edge = anchored number minus the opener (predicted result - opener)"""
    L, Lc, y = mk_xy(Dte, mk); ok = ~np.isnan(y) & ~np.isnan(edge)
    e, y, Lc, L, dd = edge[ok], y[ok], Lc[ok], L[ok], Dte.date.values[ok]
    d_mse = y ** 2 - (y - e) ** 2                    # per-game improvement over the opener alone
    days = pd.Series(d_mse).groupby(dd); sums, cnts = days.sum().values, days.size().values
    rng = np.random.default_rng(seed); k = len(sums)
    bs = np.array([(lambda i: sums[i].sum() / cnts[i].sum())(rng.integers(0, k, k)) for _ in range(n_boot)])
    m = np.abs(e) >= Z * sd; r = np.sign(e[m]) * y[m]; w, l = int((r > 0).sum()), int((r < 0).sum())
    clv = np.nanmean(np.sign(e[m]) * (Lc[m] - L[m])) if m.any() else np.nan
    return dict(games=int(ok.sum()), dmse=float(d_mse.mean()), lo=float(np.percentile(bs, 5)), hi=float(np.percentile(bs, 95)),
                p_neg=float((bs < 0).mean()), mse_open=float((y ** 2).mean()), bets=w + l, win=w / max(w + l, 1),
                units=w * 100 / 110 - l, clv=float(clv))


def run_choose():
    G = table(); rows = []; picks = {}
    lines = []
    def say(s): lines.append(s); print(s, flush=True)
    for mk in ("spread", "total"):
        tr = G[G.season.isin(BUILD) & (G[f"{mk}_trusted"] == 1)]
        ch = G[G.season.isin(CHOOSE) & (G[f"{mk}_trusted"] == 1)]
        say(f"\n== {mk.upper()}  (BUILD {BUILD[0]}-{BUILD[-1]} games {len(tr)}, CHOOSE {CHOOSE[0]}-{CHOOSE[-1]} games {len(ch)})")
        say(f"{'candidate':20s} {'weight':>7s} | {'BUILD dMSE':>10s} | {'CHOOSE dMSE':>11s} {'90% range':>17s} {'P<0':>5s} | {'bets':>5s} {'win%':>6s} {'units':>7s} {'CLV':>6s} | pass")
        best = None
        for name, col in CANDS[mk]:
            f = fit(tr, mk, col)
            sb = score(tr, mk, apply(tr, mk, col, f), f[2], n_boot=200)
            sc = score(ch, mk, apply(ch, mk, col, f), f[2])
            ok = col is not None and sc["lo"] > 0 and sc["clv"] > 0
            wtxt = "stack" if f[0] == "stack" else f"{f[1]:.2f}"
            say(f"{name:20s} {wtxt:>7s} | {sb['dmse']:+10.2f} | {sc['dmse']:+11.2f} [{sc['lo']:+6.2f},{sc['hi']:+6.2f}] {sc['p_neg']:5.2f} |"
                f" {sc['bets']:5d} {sc['win']:6.1%} {sc['units']:+7.1f} {sc['clv']:+6.2f} | {'PASS' if ok else '-'}")
            rows.append(dict(market=mk, candidate=name, weight=wtxt, build_dmse=sb["dmse"], **{f"choose_{k}": v for k, v in sc.items()}, passes=ok))
            if ok and (best is None or sc["dmse"] > best[1]["dmse"]): best = (name, sc, col)
        if best:                                          # simpler candidate within the best one's interval wins
            for name, col in CANDS[mk]:
                r = [x for x in rows if x["market"] == mk and x["candidate"] == name][0]
                if r["passes"] and SIMPLICITY.get(name, 9) < SIMPLICITY.get(best[0], 9) and r["choose_dmse"] >= best[1]["lo"]:
                    best = (name, None, col); break
            picks[mk] = dict(candidate=best[0], col=best[2])
            say(f"PICK for {mk}: {best[0]}")
        else:
            say(f"PICK for {mk}: none (nothing beats the opener on CHOOSE)")
    if "stack" in "".join(p["candidate"] for p in picks.values()) or True:
        for mk in ("spread", "total"):
            f = fit(G[G.season.isin(BUILD) & (G[f"{mk}_trusted"] == 1)], mk, "STACK")
            names = ["intercept", "Model1-line", "Elo-line", "simple-line", "form", "rested"] if mk == "spread" else \
                    ["intercept", "Model1-line", "simple-line", "form", "altitude", "rested"]
            say(f"stack coefficients ({mk}, BUILD): " + ", ".join(f"{n} {v:+.3f}" for n, v in zip(names, f[1])))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "nba_choose_results.csv"), index=False)
    json.dump(picks, open(os.path.join(OUT, "nba_picks.json"), "w"), indent=1)
    open(os.path.join(OUT, "nba_choose_output.txt"), "w").write("\n".join(lines) + "\n")


def run_lockbox():
    pf = os.path.join(OUT, "nba_picks.json"); assert os.path.exists(pf), "run choose first"
    lf = os.path.join(OUT, "nba_lockbox_output.txt"); assert not os.path.exists(lf), "lockbox already opened"
    picks = json.load(open(pf)); G = table(); lines = []
    def say(s): lines.append(s); print(s, flush=True)
    for mk, p in picks.items():
        tr = G[G.season.isin(BUILD + CHOOSE) & (G[f"{mk}_trusted"] == 1)]
        lk = G[G.season.isin(LOCK) & (G[f"{mk}_trusted"] == 1)]
        f = fit(tr, mk, p["col"]); sc = score(lk, mk, apply(lk, mk, p["col"], f), f[2])
        ok = sc["lo"] > 0 and sc["clv"] > 0
        say(f"LOCKBOX {mk}: {p['candidate']} refit on 2014-2022 -> dMSE {sc['dmse']:+.2f} [{sc['lo']:+.2f},{sc['hi']:+.2f}] P<0 {sc['p_neg']:.2f};"
            f" {sc['bets']} bets {sc['win']:.1%} {sc['units']:+.1f}u CLV {sc['clv']:+.2f} -> {'PASS' if ok else 'FAIL'}")
        for s in LOCK:
            x = score(lk[lk.season == s], mk, apply(lk[lk.season == s], mk, p["col"], f), f[2], n_boot=200)
            say(f"   {s}: dMSE {x['dmse']:+.2f}, {x['bets']} bets {x['win']:.1%} {x['units']:+.1f}u CLV {x['clv']:+.2f}")
    open(lf, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    {"predict": predict, "choose": run_choose, "lockbox": run_lockbox}[MODE]()
