"""NBA player props v1 (points, rebounds, assists, threes) — as pre-registered in research/props/PROPS_V1_PREREG_2026-11-05.md.
  python analysis/props_v1.py WORKDIR features   -> _tmp/props_features.csv.gz   (box scores only; no prop lines)
  python analysis/props_v1.py WORKDIR backtest [v1|v1b]  -> analysis/props_{v}_output.txt, analysis/props_{v}_bets.csv.gz
v1b (amendment, written before any results): variance = a*mu + b*mu^2 per stat (fit on 2023-24 box), negative binomial with r(mu).
"""
import os, sys, re, glob, unicodedata
import numpy as np, pandas as pd
from scipy import stats, optimize
W = os.path.abspath(sys.argv[1]); MODE = sys.argv[2]; sys.path.insert(0, W)
STATS = {"player_points": "pts", "player_rebounds": "reb", "player_assists": "ast", "player_threes": "fg3m"}
PACE = {"pts": True, "ast": True, "fg3m": True, "reb": False}
HL_MIN, HL_RATE, PRIOR_GAMES, PRIOR_MIN, K_OPP = 5, 20, 5, 150, 15
FIT, TEST = 2025, 2026          # season labels; amendment 2: FIT = 2025-10-21..2026-01-15, TEST = 2026-01-16..2026-04-12
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1105)


def norm(n):
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"[.'`]", "", n).replace("-", " ")
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


# ------------------------------------------------------------------ features (box only)
def features():
    B = pd.concat([pd.read_csv(f, dtype={"game_id": str, "player_id": str}) for f in sorted(glob.glob(os.path.join(W, "data", "player_stats", "season_20*.csv.gz")))
                   if int(re.search(r"(\d{4})", os.path.basename(f)).group(1)) in (2022, 2023, 2024, 2025, 2026)], ignore_index=True)
    B = B[B["min"] > 0].copy(); B["d"] = pd.to_datetime(B.date)
    B = B.sort_values(["player_id", "season", "d"]).reset_index(drop=True)
    # last-season priors
    agg = B.groupby(["player_id", "season"]).agg(g=("min", "size"), m=("min", "sum"), **{s: (s, "sum") for s in STATS.values()}).reset_index()
    lg = agg.groupby("season").sum(numeric_only=True)
    league_rate = {(s, st): lg.loc[s, st] / lg.loc[s, "m"] for s in lg.index for st in STATS.values()}
    agg["season"] += 1
    agg = agg.set_index(["player_id", "season"])
    # recursive weighted sums over each player's season, using games before the current one
    dm, dr = 0.5 ** (1 / HL_MIN), 0.5 ** (1 / HL_RATE)
    cols = {c: np.full(len(B), np.nan) for c in ["n_prev", "min_proj"] + [f"rate_{s}" for s in STATS.values()]}
    for (pid, season), idx in B.groupby(["player_id", "season"]).indices.items():
        pr = agg.loc[(pid, season)] if (pid, season) in agg.index else None
        p_mpg = pr.m / pr.g if pr is not None else 18.0
        p_rate = {s: (pr[s] / pr.m if pr is not None and pr.m >= 300 else league_rate.get((season - 1, s), league_rate.get((season, s)))) for s in STATS.values()}
        Sm = Sw = 0.0; Sr = {s: 0.0 for s in STATS.values()}; Srm = 0.0
        mins = B["min"].values[idx]; vals = {s: B[s].values[idx] for s in STATS.values()}
        for k, i in enumerate(idx):
            cols["n_prev"][i] = k
            cols["min_proj"][i] = (Sm + PRIOR_GAMES * p_mpg) / (Sw + PRIOR_GAMES)
            for s in STATS.values():
                cols[f"rate_{s}"][i] = (Sr[s] + PRIOR_MIN * p_rate[s]) / (Srm + PRIOR_MIN)
            Sm = Sm * dm + mins[k]; Sw = Sw * dm + 1
            Srm = Srm * dr + mins[k]
            for s in STATS.values(): Sr[s] = Sr[s] * dr + vals[s][k]
    for c, v in cols.items(): B[c] = v
    # opponent factor: stat allowed per game by the opponent before this date, shrunk k=15 games, vs the league per game
    TG = B.groupby(["season", "d", "game_id", "team"])[list(STATS.values())].sum().reset_index()
    opp = TG.merge(TG, on=["season", "d", "game_id"], suffixes=("", "_o")); opp = opp[opp.team != opp.team_o]
    opp = opp.sort_values("d")   # row: team, and what its opponent (team_o) scored against it
    fac = {}
    for s in STATS.values():
        lgpg = opp.groupby("season")[f"{s}_o"].mean().to_dict()
        g = opp.groupby(["season", "team"])
        csum = g[f"{s}_o"].cumsum() - opp[f"{s}_o"]; cnt = g.cumcount()
        base = opp.season.map(lambda x: lgpg.get(x - 1, lgpg[x]))
        opp[f"allow_{s}"] = ((csum + K_OPP * base) / (cnt + K_OPP)) / base
    A = opp[["season", "d", "team"] + [f"allow_{s}" for s in STATS.values()]].rename(columns={"team": "opp"})
    B = B.merge(TG[["season", "d", "game_id", "team"]].merge(TG[["game_id", "team"]].rename(columns={"team": "opp"}), on="game_id").query("team != opp")[["game_id", "team", "opp"]],
                on=["game_id", "team"], how="left")
    B = B.merge(A, on=["season", "d", "opp"], how="left")
    # pace: DraftKings full-game opener total vs the running season average of openers before that date
    O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv")); O = O[O.book == "draftkings"].drop_duplicates(["date", "home", "away"])
    O["d"] = pd.to_datetime(O.date); O = O.sort_values("d"); O["season"] = O.d.dt.year + (O.d.dt.month >= 8)
    O["run"] = O.groupby("season").open_total.transform(lambda v: v.shift().expanding().mean())
    O["run"] = O.run.fillna(O.groupby("season").open_total.transform("mean").shift().bfill())
    O["pace"] = O.open_total / O.run
    pc = pd.concat([O[["d", "home", "pace"]].rename(columns={"home": "team"}), O[["d", "away", "pace"]].rename(columns={"away": "team"})])
    B = B.merge(pc.drop_duplicates(["d", "team"]), on=["d", "team"], how="left")
    B["pace"] = B.pace.fillna(1.0)
    for s in STATS.values():
        B[f"mu_{s}"] = B.min_proj * B[f"rate_{s}"] * B[f"allow_{s}"].fillna(1.0) * (B.pace if PACE[s] else 1.0)
    B["name"] = B.player.map(norm)
    keep = ["season", "date", "game_id", "team", "opp", "home", "player_id", "player", "name", "starter", "min", "n_prev", "min_proj", "pace"] + \
           list(STATS.values()) + [f"mu_{s}" for s in STATS.values()] + [f"rate_{s}" for s in STATS.values()] + [f"allow_{s}" for s in STATS.values()]
    B = B[B.season >= 2023]   # 2021-22 is loaded only as the prior for 2022-23 (fix Nov 5, 2026: before this, 2022-23 had no prior season)
    B[keep].to_csv(os.path.join(W, "_tmp", "props_features.csv.gz"), index=False)
    say(f"features: {len(B)} player-games, seasons {B.season.value_counts().sort_index().to_dict()}")
    for s in STATS.values():
        F = B[(B.season == 2024) & (B.n_prev >= 3)]
        say(f"  2023-24 box check {s}: corr(mu, actual) {np.corrcoef(F[f'mu_{s}'], F[s])[0,1]:.3f}, mean mu {F[f'mu_{s}'].mean():.2f} vs actual {F[s].mean():.2f}")


# ------------------------------------------------------------------ negative binomial helpers
def nb_r(mu, y):
    """one dispersion r (variance = mu + mu^2 / r) by maximum likelihood"""
    f = lambda lr: -stats.nbinom.logpmf(y, np.exp(lr), np.exp(lr) / (np.exp(lr) + mu)).sum()
    return float(np.exp(optimize.minimize_scalar(f, bounds=(-3, 6), method="bounded").x))


def p_over(mu, r, line):
    return 1 - stats.nbinom.cdf(np.floor(line), r, r / (r + mu))


def dec(a): a = np.asarray(a, float); return np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))


# ------------------------------------------------------------------ backtest
def lines():
    import espn
    FULL = {"Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
            "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det", "Golden State Warriors": "gs",
            "Houston Rockets": "hou", "Indiana Pacers": "ind", "LA Clippers": "lac", "Los Angeles Clippers": "lac", "Los Angeles Lakers": "lal",
            "Memphis Grizzlies": "mem", "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min", "New Orleans Pelicans": "no",
            "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl", "Philadelphia 76ers": "phi", "Phoenix Suns": "phx",
            "Portland Trail Blazers": "por", "Sacramento Kings": "sac", "San Antonio Spurs": "sa", "Toronto Raptors": "tor", "Utah Jazz": "utah",
            "Washington Wizards": "wsh"}
    P = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(W, "data", "props_history", "nba", "*.csv.gz")))], ignore_index=True)
    P = P[P.market.isin(STATS) & P.side.isin(["Over", "Under"]) & P.point.notna()]
    P["date"] = pd.to_datetime(P.commence, utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    P["home_c"] = P.home.map(FULL); P["away_c"] = P.away.map(FULL); P["name"] = P.player.map(norm); P["stat"] = P.market.map(STATS)
    # one over/under pair per (date, game, book, stat, player, snap): keep the pair at the same point
    P = P.drop_duplicates(["date", "event_id", "book", "stat", "name", "snap", "side"], keep="last")
    Wd = P.pivot_table(index=["date", "home_c", "away_c", "book", "stat", "name", "snap"], columns="side", values=["point", "price"], aggfunc="first")
    Wd.columns = [f"{a}_{b.lower()}" for a, b in Wd.columns]; Wd = Wd.reset_index()
    Wd = Wd[(Wd.point_over == Wd.point_under) & Wd.price_over.notna() & Wd.price_under.notna()].rename(columns={"point_over": "line"}).drop(columns="point_under")
    qo, qu = 1 / dec(Wd.price_over), 1 / dec(Wd.price_under); Wd["fair_over"] = qo / (qo + qu)
    return Wd


def backtest():
    F = pd.read_csv(os.path.join(W, "_tmp", "props_features.csv.gz"), dtype={"player_id": str, "game_id": str})
    Fr = F[(F.season == 2024) & (F.n_prev >= 3)]
    R = {s: nb_r(Fr[f"mu_{s}"].clip(lower=0.05).values, Fr[s].values) for s in STATS.values()}
    say("negative-binomial dispersion r (2023-24 box only): " + ", ".join(f"{k} {v:.2f}" for k, v in R.items()))
    AB = {}
    for st in STATS.values():
        mu = Fr[f"mu_{st}"].clip(lower=0.05).values; e2 = (Fr[st].values - mu) ** 2
        AB[st] = np.linalg.lstsq(np.column_stack([mu, mu ** 2]), e2, rcond=None)[0]
    if VAR == "v1b": say("v1b variance = a*mu + b*mu^2 (2023-24 box): " + ", ".join(f"{k} a {v[0]:.2f} b {v[1]:.4f}" for k, v in AB.items()))
    Wd = lines(); say(f"prop line pairs: {len(Wd)}; dates {Wd.date.min()}..{Wd.date.max()}")
    F["home_c"] = np.where(F.home == 1, F.team, F.opp); F["away_c"] = np.where(F.home == 1, F.opp, F.team)
    long = []
    for s in STATS.values():
        x = F[["season", "date", "home_c", "away_c", "name", "player", "team", "n_prev", "min_proj", "min", f"mu_{s}", s]].rename(columns={f"mu_{s}": "mu", s: "actual"})
        long.append(x.assign(stat=s))
    Fl = pd.concat(long, ignore_index=True)
    J = Wd.merge(Fl, on=["date", "home_c", "away_c", "name", "stat"], how="left")
    am = J[J.snap == "am"]
    say(f"am line pairs matched to a box-score player: {am.actual.notna().mean()*100:.1f}% (unmatched are mostly players who did not play -> void)")
    J = J[J.actual.notna() & (J.n_prev >= 3)].copy()
    mu = J.mu.clip(lower=0.05)
    if VAR == "v1b":
        a = J.stat.map({k: v[0] for k, v in AB.items()}); b = J.stat.map({k: v[1] for k, v in AB.items()})
        ex = (a - 1) * mu + b * mu ** 2
        J["r"] = np.where(ex > 1e-6, mu ** 2 / ex.clip(lower=1e-6), 1e6)
    else:
        J["r"] = J.stat.map(R)
    J["p_model"] = p_over(mu, J.r, J.line)
    J["sd"] = np.sqrt(mu + mu ** 2 / J.r)
    # market at 11 AM: DraftKings no-vig, FanDuel if DK missing
    key = ["date", "home_c", "away_c", "stat", "name"]
    A = J[J.snap == "am"]; C = J[J.snap == "close"]
    mk = A[A.book == "draftkings"].set_index(key).fair_over.combine_first(A[A.book == "fanduel"].set_index(key).fair_over).rename("p_mkt")
    mk_line = A[A.book == "draftkings"].set_index(key).line.combine_first(A[A.book == "fanduel"].set_index(key).line).rename("mkt_line")
    A = A.join(mk, on=key).join(mk_line, on=key)
    # market prob at THIS row's line (books can differ by a half point): normal shift with the model's sd
    m_imp = A.mkt_line + A.sd * stats.norm.ppf(A.p_mkt.clip(0.01, 0.99))
    A["p_mkt_here"] = 1 - stats.norm.cdf((A.line - m_imp) / A.sd)
    A["season_l"] = np.where(A.date <= "2026-01-15", 2025, 2026)          # amendment 2: within-season split
    A = A[A.book.isin(["draftkings", "fanduel"]) & A.p_mkt_here.notna()].copy()
    A["over_hit"] = (A.actual > A.line).astype(float); A.loc[A.actual == A.line, "over_hit"] = np.nan
    # FIT: blend weight on 2024-25 by log loss
    Fi = A[(A.season_l == FIT) & A.over_hit.notna()].drop_duplicates(key)
    if len(Fi) < 500:
        say(f"only {len(Fi)} 2024-25 rows yet: blend weight cannot be fit; stopping."); return
    ll = lambda w: -np.mean(Fi.over_hit * np.log(np.clip(w * Fi.p_model + (1 - w) * Fi.p_mkt_here, 1e-6, 1)) +
                           (1 - Fi.over_hit) * np.log(np.clip(1 - (w * Fi.p_model + (1 - w) * Fi.p_mkt_here), 1e-6, 1)))
    wopt = float(optimize.minimize_scalar(ll, bounds=(0, 1), method="bounded").x)
    say(f"FIT 2024-25: blend weight on the model w = {wopt:.3f} (log loss: market {ll(0):.4f}, model {ll(1):.4f}, blend {ll(wopt):.4f}, n {len(Fi)})")
    A["p"] = wopt * A.p_model + (1 - wopt) * A.p_mkt_here
    # candidate bets: each side at DK and FD; keep the better price per side, then the better side
    rows = []
    for side in ("over", "under"):
        pr = A[f"price_{side}"]; ps = A.p if side == "over" else 1 - A.p
        rows.append(A.assign(side=side, price=pr, p_side=ps, ev=ps * dec(pr) - 1))
    Cand = pd.concat(rows, ignore_index=True).sort_values("ev", ascending=False).drop_duplicates(key + ["side"]).drop_duplicates(key)
    # close at the same book (fallback: the other one), converted to our line
    Cl = C[C.book.isin(["draftkings", "fanduel"])][key + ["book", "line", "fair_over"]].rename(columns={"line": "c_line", "fair_over": "c_fair"})
    Cand = Cand.merge(Cl, on=key + ["book"], how="left")
    oth = Cl.assign(book=Cl.book.map({"draftkings": "fanduel", "fanduel": "draftkings"})).rename(columns={"c_line": "c_line2", "c_fair": "c_fair2"})
    Cand = Cand.merge(oth, on=key + ["book"], how="left")
    Cand["c_line"] = Cand.c_line.fillna(Cand.c_line2); Cand["c_fair"] = Cand.c_fair.fillna(Cand.c_fair2)
    mc = Cand.c_line + Cand.sd * stats.norm.ppf(Cand.c_fair.clip(0.01, 0.99))
    Cand["c_over_here"] = np.where(Cand.c_line == Cand.line, Cand.c_fair, 1 - stats.norm.cdf((Cand.line - mc) / Cand.sd))
    Cand["c_side"] = np.where(Cand.side == "over", Cand.c_over_here, 1 - Cand.c_over_here)
    Cand["clev"] = Cand.c_side * dec(Cand.price) - 1
    won = np.where(Cand.side == "over", Cand.actual > Cand.line, Cand.actual < Cand.line); push = Cand.actual == Cand.line
    Cand["u"] = np.where(push, 0.0, np.where(won, dec(Cand.price) - 1, -1.0)); Cand["won"] = np.where(push, np.nan, won.astype(float))
    Cand["tier"] = pd.cut(Cand.min_proj, [0, 20, 30, 60], labels=["<20 min", "20-30", "30+"])
    Cand["moved_toward"] = np.where(Cand.side == "over", Cand.c_line > Cand.line, Cand.c_line < Cand.line)
    Cand.to_csv(os.path.join(W, "analysis", f"props_{VAR}_bets.csv.gz"), index=False)

    def boot(df, col, n=3000):
        g = df.groupby("date")[col].agg(["sum", "count"]).values
        if len(g) < 5: return np.nan, np.nan
        idx = rng.integers(0, len(g), (n, len(g))); m = g[idx, 0].sum(1) / g[idx, 1].sum(1)
        return np.percentile(m, 5), np.percentile(m, 95)
    def line_(df):
        d = df[df.clev.notna()]; lo, hi = boot(d, "clev"); ulo, uhi = boot(df, "u")
        return (f"{len(df):5d} bets | closing-line EV {d.clev.mean()*100:+.2f}% [{lo*100:+.2f}, {hi*100:+.2f}] (n {len(d)}) | "
                f"win {df.won.mean()*100:.1f}% | {df.u.sum():+.1f}u ({df.u.mean()*100:+.1f}% [{ulo*100:+.1f}, {uhi*100:+.1f}])")
    for season, lab in ((FIT, "FIT Oct 21 - Jan 15 (in-sample for w only)"), (TEST, "TEST Jan 16 - Apr 12")):
        S = Cand[Cand.season_l == season]
        say(f"\n== {lab} ==")
        for thr in (0.03, 0.05, 0.08, 0.12):
            say(f"  EV >= {int(thr*100):2d}%{' (rule)' if thr == 0.05 else '       '}: {line_(S[S.ev >= thr])}")
        if season == TEST:
            T = S[S.ev >= 0.05]
            d = T[T.clev.notna()]; lo, _ = boot(d, "clev")
            passed = (lo > 0) and (T.u.sum() > 0)
            say(f"  VERDICT: {'PASS -> PROVISIONAL after Fable check' if passed else 'did not pass'}")
            for col in ("stat", "book", "side", "tier", "moved_toward"):
                for k, g in T.groupby(col, observed=True):
                    say(f"    {col}={k}: {line_(g)}")
            Tt = A[(A.season_l == TEST) & A.over_hit.notna()].drop_duplicates(key)
            lls = lambda p: -np.mean(Tt.over_hit * np.log(np.clip(p, 1e-6, 1)) + (1 - Tt.over_hit) * np.log(np.clip(1 - p, 1e-6, 1)))
            cl = Tt.merge(C[C.book == "draftkings"][key + ["fair_over", "line"]].rename(columns={"fair_over": "cf", "line": "cl"}), on=key, how="left")
            cl = cl[cl.cl == cl.line]
            say(f"  log loss 2025-26 (n {len(Tt)}): market 11 AM {lls(Tt.p_mkt_here):.4f}, model {lls(Tt.p_model):.4f}, blend {lls(Tt.p):.4f}; "
                f"DK close on same-line rows (n {len(cl)}) {(-np.mean(cl.over_hit*np.log(cl.cf)+(1-cl.over_hit)*np.log(1-cl.cf))):.4f}")
    open(os.path.join(W, "analysis", f"props_{VAR}_output.txt"), "w").write("\n".join(out) + "\n")


VAR = sys.argv[3] if len(sys.argv) > 3 else "v1"
if __name__ == "__main__":
    os.makedirs(os.path.join(W, "_tmp"), exist_ok=True)
    features() if MODE == "features" else backtest()
