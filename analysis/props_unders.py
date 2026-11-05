"""NBA prop unders at the best book — as pre-registered in research/props/UNDERS_RULE_PREREG_2026-11-05.md.
  python analysis/props_unders.py WORKDIR -> analysis/props_unders_output.txt, analysis/props_unders_bets.csv.gz
Also exposes load_bp() / norm() for the props v2 backtest."""
import os, sys, re, glob, unicodedata
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]) if __name__ == "__main__" else None
BP_TEAM = {"BKN": "bkn", "GSW": "gs", "NOR": "no", "NYK": "ny", "PHO": "phx", "SAS": "sa", "UTH": "utah", "WAS": "wsh"}
BOOKS4 = ["draftkings", "fanduel", "betmgm", "caesars"]
PRIMARY = [2023, 2024, 2025]          # season = end year: 2022-23, 2023-24, 2024-25


def norm(n):
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"[.'`]", "", n).replace("-", " "); n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def dec(a): a = np.asarray(a, float); return np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))


def load_bp(W, books=BOOKS4 + ["consensus"]):
    fs = [f for f in sorted(glob.glob(os.path.join(W, "data", "props_history", "bettingpros", "*.csv.gz"))) if os.path.getsize(f) > 100]
    D = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    D = D[D.book.isin(books) & D.line.notna() & D.price.notna()].copy()
    D["home_c"] = D.home.map(lambda x: BP_TEAM.get(x, str(x).lower())); D["away_c"] = D.away.map(lambda x: BP_TEAM.get(x, str(x).lower()))
    D["tip"] = pd.to_datetime(D.scheduled); D["upd"] = pd.to_datetime(D.updated)
    D["hours_before"] = (D.tip - D.upd).dt.total_seconds() / 3600
    D["name"] = D.player.map(norm)
    d = pd.to_datetime(D.date); D["season"] = d.dt.year + (d.dt.month >= 8)
    return D


def box(W):
    """player box scores with the game's home/away team codes"""
    B = pd.concat([pd.read_csv(f, dtype={"player_id": str, "game_id": str}) for f in glob.glob(os.path.join(W, "data", "player_stats", "season_*.csv.gz"))])
    B["name"] = B.player.map(norm)
    h = B[B.home == 1].drop_duplicates("game_id").set_index("game_id").team; a = B[B.home == 0].drop_duplicates("game_id").set_index("game_id").team
    B["home_c"] = B.game_id.map(h); B["away_c"] = B.game_id.map(a)
    return B


def main():
    out = []
    def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
    rng = np.random.default_rng(1105)
    D = load_bp(W)
    say(f"BettingPros lines: {len(D)} rows, dates {D.date.min()}..{D.date.max()}, seasons {D.season.value_counts().sort_index().to_dict()}")
    B = box(W)
    U = D[(D.side == "under") & D.book.isin(BOOKS4) & (D.hours_before >= -0.25) & (D.hours_before <= 6)].copy()
    key = ["date", "home_c", "away_c", "name", "stat"]
    U = U.sort_values(["line", "price"], ascending=[False, False]).drop_duplicates(key)       # highest line, then best price
    J = U.merge(B[["date", "home_c", "away_c", "name", "min", "pts", "reb", "ast", "fg3m"]], on=["date", "home_c", "away_c", "name"], how="left")
    say(f"under bets: {len(U)}; matched to a box score: {J['min'].notna().mean()*100:.1f}%")
    J = J[J["min"].notna() & (J["min"] > 0)].copy()                                             # did not play = void
    J["actual"] = [getattr(r, r.stat) for r in J.itertuples()]
    J["res"] = np.where(J.actual < J.line, 1, np.where(J.actual > J.line, -1, 0))
    J["u"] = np.where(J.res > 0, dec(J.price) - 1, np.where(J.res < 0, -1.0, 0.0))
    # over-lean check from the consensus close, same games
    C = D[(D.book == "consensus")].pivot_table(index=key, columns="side", values=["line", "price"], aggfunc="first")
    C.columns = [f"{a}_{b}" for a, b in C.columns]; C = C.reset_index()
    C = C[C.line_over == C.line_under]; qo, qu = 1 / dec(C.price_over), 1 / dec(C.price_under); C["fair_over"] = qo / (qo + qu)
    C = C.merge(B[["date", "home_c", "away_c", "name", "min", "pts", "reb", "ast", "fg3m"]], on=["date", "home_c", "away_c", "name"])
    C = C[C["min"] > 0]; C["actual"] = [getattr(r, r.stat) for r in C.itertuples()]; C = C[C.actual != C.line_over]
    C["over_hit"] = (C.actual > C.line_over).astype(float)
    J.to_csv(os.path.join(W, "analysis", "props_unders_bets.csv.gz"), index=False)

    def boot(df, n=4000):
        g = df.groupby("date").u.agg(["sum", "count"]).values
        idx = rng.integers(0, len(g), (n, len(g))); m = g[idx, 0].sum(1) / g[idx, 1].sum(1)
        return np.percentile(m, 5), np.percentile(m, 95)
    def line_(df):
        lo, hi = boot(df) if df.date.nunique() >= 5 else (np.nan, np.nan)
        w = df[df.res != 0]
        return f"{len(df):6d} bets | win {(w.res > 0).mean()*100:5.1f}% | {df.u.sum():+8.1f}u | ROI {df.u.mean()*100:+.2f}% [{lo*100:+.2f}, {hi*100:+.2f}]"
    say("\n== By season (season = end year; primary = 2023, 2024, 2025) ==")
    for s, g in J.groupby("season"):
        c = C[C.season == s] if "season" in C else C[pd.to_datetime(C.date).dt.year + (pd.to_datetime(C.date).dt.month >= 8) == s]
        say(f"  {s}{' *' if s in PRIMARY else '  '}: {line_(g)} | consensus over-lean: priced {c.fair_over.mean()*100:.1f}% vs hit {c.over_hit.mean()*100:.1f}% (n {len(c)})")
    P = J[J.season.isin(PRIMARY)]
    if len(P):
        lo, hi = boot(P); seasons_pos = sum(J[J.season == s].u.sum() > 0 for s in PRIMARY if (J.season == s).any())
        n_seasons = sum((J.season == s).any() for s in PRIMARY)
        passed = lo > 0 and seasons_pos >= 2
        say(f"\nPRIMARY pooled: {line_(P)}; seasons positive {seasons_pos}/{n_seasons} -> {'PASS -> PROVISIONAL after Fable check' if passed else 'did not pass'}"
            + ("" if n_seasons == 3 else "  (NOT FINAL: primary seasons still downloading)"))
        say("\n== Descriptive (primary seasons) ==")
        for col in ("stat", "book"):
            for k, g in P.groupby(col): say(f"  {col}={k}: {line_(g)}")
        P = P.assign(size=pd.cut(P.line, [0, 2, 5, 10, 20, 60]))
        for k, g in P.groupby("size", observed=True): say(f"  line {k}: {line_(g)}")
        for b in BOOKS4:
            S1 = D[(D.side == "under") & (D.book == b) & (D.hours_before.between(-0.25, 6)) & D.season.isin(PRIMARY)].drop_duplicates(key)
            S1 = S1.merge(B[["date", "home_c", "away_c", "name", "min", "pts", "reb", "ast", "fg3m"]], on=["date", "home_c", "away_c", "name"])
            S1 = S1[S1["min"] > 0]; a = np.array([getattr(r, r.stat) for r in S1.itertuples()])
            u = np.where(a < S1.line, dec(S1.price) - 1, np.where(a > S1.line, -1.0, 0.0))
            say(f"  single book {b}: {len(S1)} unders, ROI {u.mean()*100:+.2f}%")
    open(os.path.join(W, "analysis", "props_unders_output.txt"), "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
