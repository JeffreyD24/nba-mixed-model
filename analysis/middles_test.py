"""Middles test (Nov 4, 2026). Pre-registered in analysis/MIDDLES_PREREG.md (commit 8f5f799) before any result.
  A. Book-gap middles: first pre-tip snapshot where two books in a group differ by g+ pts; 1 unit each leg at real prices.
  B. Middling our own bets: DraftKings opener bets (edge 3+, 2023-26); add the other side at the best CT line once it is g+ pts better.
  python analysis/middles_test.py WORKDIR -> analysis/middles_test_output.txt, analysis/middles_opps.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

GROUPS = {"CT (DraftKings + FanDuel)": ["draftkings", "fanduel"],
          "US regulated (DK, FD, BetMGM, Caesars, BetRivers)": ["draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers"],
          "all 10 books incl. offshore": None}
key = ["date", "home", "away"]
S = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"))
S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True)
S["tip0"] = S.groupby("event_id").tip.transform("min")      # Fable review: a moved tip let in-game quotes through; use the first tip
S = S[S.t < S.tip0]
MAX_GAP = 8.0                                                  # Fable review: gaps of 8+ pts are bad quotes (wrong game / live line)
TG = pd.read_csv(os.path.join(W, "data", "training_games.csv"))[key + ["season", "home_pts", "away_pts"]].drop_duplicates(key)
S = S.merge(TG, on=key, how="inner")
S["T"] = S.home_pts + S.away_pts; S["M"] = S.home_pts - S.away_pts
def okp(x): return x.between(-250, 200) & x.notna()

def pay(price):
    p = np.asarray(price, float); return np.where(p < 0, 100 / np.abs(p), p / 100)
def leg(x, price):          # x = margin vs the line from the bet's side (>0 win, 0 push)
    return np.where(x > 0, pay(price), np.where(x == 0, 0.0, -1.0))

def best(df, col, px, how):
    """per (event, t): best line for one side; ties broken by best price"""
    d = df[df[col].notna() & okp(df[px])][["event_id", "t", "book", col, px]]
    d = d.sort_values(["event_id", "t", col, px], ascending=[True, True, how == "min", False])
    return d.groupby(["event_id", "t"]).head(1).set_index(["event_id", "t"])

def summarize(R, label):
    say(f"  {label}")
    for g in (1.0, 1.5, 2.0, 2.5, 3.0):
        D = R[R.g == g]
        if not len(D): say(f"    gap {g:g}+: none"); continue
        u = D.units; mid = (D.both_win).mean()
        bys = " ".join(f"{s % 100}:{D[D.season == s].units.sum():+.1f}({(D.season == s).sum()})" for s in sorted(D.season.unique()))
        pos = sum(D[D.season == s].units.sum() > 0 for s in D.season.unique())
        say(f"    gap {g:g}+: {len(D):5d} games | middle hit {mid:5.1%} | a leg pushed {D.push.mean():4.1%} | pair units {u.sum():+7.1f} ({u.mean() * 100:+5.1f} per 100 pairs) | "
            f"seasons positive {pos}/{D.season.nunique()} | {bys}")

rows_all = []
say("A. BOOK-GAP MIDDLES (first pre-tip snapshot with a gap of g+ pts; 1 unit each leg at real prices)")
for gname, books in GROUPS.items():
    X = S if books is None else S[S.book.isin(books)]
    games = X.drop_duplicates("event_id").set_index("event_id")[["season", "date", "home", "away", "T", "M"]]
    # totals: lowest over line vs highest under line
    lo = best(X, "tot", "ov_px", "min").rename(columns={"tot": "a", "ov_px": "pa", "book": "book_a"})
    hi = best(X, "tot", "un_px", "max").rename(columns={"tot": "b", "un_px": "pb", "book": "book_b"})
    J = lo.join(hi, how="inner").reset_index(); J["gap"] = J.b - J.a; J["market"] = "total"; J = J[J.gap < MAX_GAP]
    # spreads (home view): home at the highest number, away at the lowest
    hs = best(X, "sp", "sp_px_h", "max").rename(columns={"sp": "a", "sp_px_h": "pa", "book": "book_a"})
    as_ = best(X, "sp", "sp_px_a", "min").rename(columns={"sp": "b", "sp_px_a": "pb", "book": "book_b"})
    K = hs.join(as_, how="inner").reset_index(); K["gap"] = K.a - K.b; K["market"] = "spread"; K = K[K.gap < MAX_GAP]
    Z = pd.concat([J, K], ignore_index=True).sort_values("t")
    for mk in ("total", "spread"):
        R = []
        for g in (1.0, 1.5, 2.0, 2.5, 3.0):
            F = Z[(Z.market == mk) & (Z.gap >= g - 0.01)].groupby("event_id").head(1).join(games, on="event_id")
            if mk == "total":
                la = leg(F["T"] - F.a, F.pa); lb = leg(F.b - F["T"], F.pb)
            else:
                la = leg(F["M"] + F.a, F.pa); lb = leg(-(F["M"] + F.b), F.pb)
            F = F.assign(g=g, units=la + lb, both_win=(la > 0) & (lb > 0), push=(la == 0) | (lb == 0), group=gname)
            R.append(F)
        R = pd.concat(R)
        rows_all.append(R)
        summarize(R, f"{gname} - {mk}s")
pd.concat(rows_all).to_csv(os.path.join(W, "analysis", "middles_opps.csv"), index=False)

# ------------------------------------------------------------------ B
say("\nB. MIDDLING OUR OWN BETS (DraftKings opener bet, edge 3+, 2023-26; other side added at the best CT line once g+ pts better)")
B = pd.read_csv(os.path.join(W, "analysis", "line_move_threshold_bets.csv"))
CT = S[S.book.isin(GROUPS["CT (DraftKings + FanDuel)"])]
idx = {k: g for k, g in CT.groupby(key)}
res = []
for r in B.itertuples(index=False):
    g_ = idx.get((r.date, r.home, r.away))
    if g_ is None or pd.isna(r.open_res): continue
    s = r.side
    if r.market == "total":
        col, px, how = ("tot", "un_px", "max") if s > 0 else ("tot", "ov_px", "min")
    else:
        col, px, how = ("sp", "sp_px_a", "min") if s > 0 else ("sp", "sp_px_h", "max")
    bb = best(g_, col, px, how).reset_index().sort_values("t")
    if not len(bb): continue
    if r.market == "total": gap = s * (bb[col] - r.open)
    else: gap = s * (r.open - bb[col])
    T_ = g_["T"].iloc[0]; M_ = g_["M"].iloc[0]
    own = float(leg(np.array([r.open_res]), np.array([-110.0]))[0])
    for g in (1, 2, 3, 4):
        h = np.where(gap.values >= g - 0.01)[0]
        if not len(h): continue
        L, P = bb[col].iloc[h[0]], bb[px].iloc[h[0]]
        if r.market == "total": x = (-s) * (T_ - L)
        else: x = (-s) * (M_ + L)
        hl = float(leg(np.array([x]), np.array([P]))[0])
        res.append(dict(market=r.market, season=r.season, g=g, own=own, hedge=hl, both=(own > 0) and (hl > 0)))
Q = pd.DataFrame(res)
for mk in ("total", "spread"):
    say(f"  {mk}s")
    for g in (1, 2, 3, 4):
        D = Q[(Q.market == mk) & (Q.g == g)]
        if not len(D): continue
        w, l = (D.hedge > 0).sum(), (D.hedge < 0).sum()
        bys = " ".join(f"{s % 100}:{D[D.season == s].hedge.sum():+.1f}" for s in (2024, 2025, 2026))
        say(f"    {g}+ pts better: {len(D):4d} hedges | hedge leg {w}-{l} ({w / max(w + l, 1):.1%}) {D.hedge.sum():+6.1f}u ({bys}) | "
            f"middle hit {D.both.mean():5.1%} | ride alone {D.own.sum():+6.1f}u vs ride + hedge {(D.own + D.hedge).sum():+6.1f}u")
open(os.path.join(W, "analysis", "middles_test_output.txt"), "w").write("\n".join(out) + "\n")
