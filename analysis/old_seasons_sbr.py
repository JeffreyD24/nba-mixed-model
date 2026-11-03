"""NBA Model 1 on ten older seasons graded at SBR OPENING lines (Nov 3, 2026, job 4 of research/HANDOFF_TO_OPUS.md).
Data: data/external/sbr/sbr_nba_2011_2021_clean.csv.gz (finals, opening and closing spread and total; prices not recorded,
graded at -110). Model 1 WITHOUT injury features (no reports that far back), walk-forward with the one-day lag (results through
two nights before, like the live morning lock), trained on up to 4 earlier seasons. Test seasons 2013-14 .. 2021-22.
  python analysis/old_seasons_sbr.py WORKDIR predict     -> _tmp/old_sbr_preds_{season}.csv
  python analysis/old_seasons_sbr.py WORKDIR score       -> analysis/old_seasons_sbr_output.txt, analysis/old_seasons_sbr_bets.csv
Season labels here are END years (2014 = 2013-14), as in the rest of the repo; SBR uses START years."""
import os, sys, io, contextlib, json
import numpy as np, pandas as pd
from scipy.stats import norm
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
TMP = os.path.join(W, "_tmp"); os.makedirs(TMP, exist_ok=True)
NICK = {"Hawks": "atl", "Nets": "bkn", "NewJersey": "bkn", "Celtics": "bos", "Hornets": "cha", "Bulls": "chi", "Cavaliers": "cle",
        "Mavericks": "dal", "Nuggets": "den", "Pistons": "det", "Warriors": "gs", "Golden State": "gs", "Rockets": "hou", "Pacers": "ind",
        "Clippers": "lac", "LA Clippers": "lac", "Lakers": "lal", "Grizzlies": "mem", "Heat": "mia", "Bucks": "mil", "Timberwolves": "min",
        "Pelicans": "no", "Knicks": "ny", "Thunder": "okc", "Oklahoma City": "okc", "Magic": "orl", "Seventysixers": "phi", "Suns": "phx",
        "Trailblazers": "por", "Spurs": "sa", "Kings": "sac", "Raptors": "tor", "Jazz": "utah", "Wizards": "wsh"}
REG_END = {2012: "2012-04-26", 2013: "2013-04-17", 2014: "2014-04-16", 2015: "2015-04-15", 2016: "2016-04-13", 2017: "2017-04-12",
           2018: "2018-04-11", 2019: "2019-04-10", 2020: "2020-08-14", 2021: "2021-05-16", 2022: "2022-04-10"}
TESTS = list(range(2014, 2023))


def build():
    S = pd.read_csv(os.path.join(W, "data/external/sbr/sbr_nba_2011_2021_clean.csv.gz"))
    S["date"] = pd.to_datetime(S.date)
    rep = []
    bub = (S.season == 2019) & (S.date < "2019-10-01")          # 2020 bubble games dated a year early in SBR
    S.loc[bub, "date"] = S.loc[bub, "date"] + pd.DateOffset(years=1); rep.append(f"bubble rows shifted +1 year: {bub.sum()}")
    S["home"] = S.home_team.map(NICK); S["away"] = S.away_team.map(NICK)
    assert S.home.notna().all() and S.away.notna().all(), set(S.home_team[S.home.isna()]) | set(S.away_team[S.away.isna()])
    S["season"] = S.season + 1
    S = S[S.date <= pd.to_datetime(S.season.map(REG_END))].copy()   # regular season only
    D = pd.DataFrame(dict(date=S.date.dt.strftime("%Y-%m-%d"), season=S.season, home=S.home, away=S.away, home_pts=S.home_final,
                          away_pts=S.away_final, spread=S.home_close_spread, total=S.close_over_under, open_spread=S.home_open_spread,
                          open_total=S.open_over_under, spread_trusted=S.spread_trusted, total_trusted=S.total_trusted,
                          open_ok=S.open_ok, close_ok=S.close_ok))
    D = D.drop_duplicates(["date", "home", "away"])
    for s, g in D.groupby("season"):
        n = pd.concat([g.home, g.away]).value_counts()
        rep.append(f"  {s}: {len(g)} games, games per team {n.min()}-{n.max()}")
    # sanity: Charlotte 2011-12 went 7-59, New Orleans 21-45 (checks the Hornets/Pelicans mapping)
    g = D[D.season == 2012]
    for t in ("cha", "no"):
        w = ((g.home == t) & (g.home_pts > g.away_pts)).sum() + ((g.away == t) & (g.away_pts > g.home_pts)).sum()
        rep.append(f"  2011-12 {t} wins: {w}")
    return D, rep


def predict():
    D, rep = build(); print("\n".join(rep))
    src = open(os.path.join(W, "nba_mixed_model.py")).read()
    ns = {"__name__": "nm_lag"}
    exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=1)]"), "nm_lag", "exec"), ns)
    for test in TESTS:
        train = [s for s in range(max(2012, test - 4), test)]
        with contextlib.redirect_stdout(io.StringIO()):
            _, P = ns["run"](D[D.season.isin(train + [test])], train, test)
        P["season"] = test
        P.to_csv(os.path.join(TMP, f"old_sbr_preds_{test}.csv"), index=False)
        print(test, "train", train, flush=True)


def score():
    Z = norm.ppf(110 / 210); out = []
    def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
    P = pd.concat([pd.read_csv(os.path.join(TMP, f"old_sbr_preds_{s}.csv")) for s in TESTS], ignore_index=True)
    P["margin"] = P.home_pts - P.away_pts; P["pts"] = P.home_pts + P.away_pts
    def parts(D, mk, line):
        L = -D[f"{line}spread"] if mk == "spread" else D[f"{line}total"]
        pred = D.pred_margin if mk == "spread" else D.pred_total
        act = D.margin if mk == "spread" else D.pts
        return (pred - L).values, (act - L).values
    def g3(x, y, thr=3.0):
        m = (np.abs(x) >= thr) & ~np.isnan(y) & ~np.isnan(x); r = np.sign(x[m]) * y[m]; w, l = int((r > 0).sum()), int((r < 0).sum())
        return w, l, w * 100 / 110 - l
    def slope(x, y):
        m = ~(np.isnan(x) | np.isnan(y)); x, y = x[m], y[m]; b = (x @ y) / (x @ x); r = y - b * x
        return b, np.sqrt(r @ r / (len(x) - 1) / (x @ x)), np.std(y - b * x, ddof=1)
    bets = []
    for mk in ("spread", "total"):
        trust = "spread_trusted" if mk == "spread" else "total_trusted"
        say(f"\n== {mk.upper()}: Model 1 (no injuries, one-day lag), edge 3+ at -110")
        for rows_lab, D in (("all rows", P), ("trusted rows", P[P[trust] == 1])):
            say(f"  {rows_lab}:")
            for line, lab in (("open_", "opener"), ("", "close")):
                per, T = [], [0, 0, 0.0]
                for s in TESTS:
                    x, y = parts(D[D.season == s], mk, line); w, l, u = g3(x, y)
                    per.append(f"{s % 100}:{u:+.0f}"); T[0] += w; T[1] += l; T[2] += u
                say(f"    at the {lab:6s}: {T[0]}-{T[1]} ({T[0] / max(T[0] + T[1], 1):.1%}) {T[2]:+.1f}u   [{' '.join(per)}]")
        D = P[P[trust] == 1]
        x, y = parts(D, mk, "open_"); b, se, _ = slope(x, y); xc, yc = parts(D, mk, "")
        per = " ".join(f"{s % 100}:{slope(*parts(D[D.season == s], mk, 'open_'))[0]:+.2f}" for s in TESTS)
        say(f"  weight on Model 1 vs the opener (trusted): {b:+.2f} (+/- {se:.2f}); vs the close {slope(xc, yc)[0]:+.2f}\n    by season: {per}")
        T = [0, 0, 0.0]
        for s in TESTS:
            tr, te = D[D.season != s], D[D.season == s]
            ws, _, sds = slope(*parts(tr, mk, "open_"))
            xt, yt = parts(te, mk, "open_"); w, l, u = g3(ws * xt, yt, Z * sds); T[0] += w; T[1] += l; T[2] += u
        say(f"  shrunk rule (weight from the other seasons, bet when it beats -110): {T[0]}-{T[1]} ({T[0] / max(T[0] + T[1], 1):.1%}) {T[2]:+.1f}u")
        x, y = parts(P, mk, "open_")
        m = np.abs(x) >= 3
        bets.append(pd.DataFrame(dict(season=P.season[m], date=P.date[m], home=P.home[m], away=P.away[m], market=mk, edge=x[m],
                                      side=np.where(mk == "spread", np.where(x[m] > 0, "home", "away"), np.where(x[m] > 0, "over", "under")),
                                      result=np.sign(np.sign(x[m]) * y[m]), trusted=P[trust][m])))
    # accuracy against the opener
    say("\n== Accuracy (mean absolute error, trusted rows)")
    for mk, pc, ac, lc in (("margin", "pred_margin", "margin", "open_spread"), ("total", "pred_total", "pts", "open_total")):
        D = P[P[("spread" if mk == "margin" else "total") + "_trusted"] == 1]
        L = -D[lc] if mk == "margin" else D[lc]; Lc = -D.spread if mk == "margin" else D.total
        say(f"  {mk}: Model 1 {np.abs(D[pc] - D[ac]).mean():.2f} | opener {np.abs(L - D[ac]).mean():.2f} | close {np.abs(Lc - D[ac]).mean():.2f}")
    pd.concat(bets).to_csv(os.path.join(W, "analysis", "old_seasons_sbr_bets.csv"), index=False)
    open(os.path.join(W, "analysis", "old_seasons_sbr_output.txt"), "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    predict() if sys.argv[2] == "predict" else score()
