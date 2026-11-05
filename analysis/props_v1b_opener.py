"""Props v1b at the OPENING line on past seasons — as pre-registered in research/props/PROPS_V1B_OPENER_PREREG_2026-11-05.md.
  python analysis/props_v1b_opener.py WORKDIR -> analysis/props_v1b_opener_output.txt, analysis/props_v1b_opener_bets.csv.gz
Needs _tmp/props_features.csv.gz (python analysis/props_v1.py WORKDIR features)."""
import os, sys, json
import numpy as np, pandas as pd
from scipy import stats, optimize
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, os.path.join(W, "analysis")); sys.path.insert(0, W)
import derived  # RULE 4: saved features in derived/ (restored to _tmp/props_features.csv if _tmp lacks the .gz)
FEAT = os.path.join(W, "_tmp", "props_features.csv.gz")
if not os.path.exists(FEAT): derived.ensure(W, ["props_features.csv"]); FEAT = os.path.join(W, "_tmp", "props_features.csv")
from props_unders import load_bp, dec
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1107)
P1 = json.load(open(os.path.join(W, "data", "props_v1b_params.json")))
STATS = ["pts", "reb", "ast", "fg3m"]; FIT, TEST = 2023, [2024, 2025]
key = ["date", "home_c", "away_c", "name", "stat"]

D = load_bp(W, books=["draftkings", "fanduel", "betmgm", "caesars", "betrivers", "bet365", "thescore", "fanatics", "hardrock", "consensus"])
# openers (same book and line for both sides; checked)
O = D.drop_duplicates(key + ["side"])[key + ["season", "side", "open_line", "open_price", "open_book", "open_time", "scheduled"]]
O = O.pivot_table(index=key + ["season", "open_book", "open_time", "scheduled"], columns="side", values=["open_line", "open_price"], aggfunc="first")
O.columns = [f"{a}_{b}" for a, b in O.columns]; O = O.reset_index()
O = O[(O.open_line_over == O.open_line_under) & O.open_price_over.notna() & O.open_price_under.notna()]
# bad-quote filter (MODEL_PLAYBOOK: check archives for bad quotes): real two-way prop prices sit within -1000..+1000, never between -100 and +100
for c in ("open_price_over", "open_price_under"): O = O[(O[c].abs() >= 100) & (O[c].abs() <= 1000)].rename(columns={"open_line_over": "line"})
O["open_t"] = pd.to_datetime(O.open_time); O["tip"] = pd.to_datetime(O.scheduled)
O["lead_h"] = (O.tip - O.open_t).dt.total_seconds() / 3600
O["open_date_et"] = O.open_t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
qo, qu = 1 / dec(O.open_price_over), 1 / dec(O.open_price_under); O["p_open"] = qo / (qo + qu)
say(f"openers: {len(O)}; by book {O.open_book.value_counts().head(6).to_dict()}")
# close at the opener's book
C = D[D.hours_before.between(-0.25, 6)].pivot_table(index=key + ["book"], columns="side", values=["line", "price"], aggfunc="first")
C.columns = [f"{a}_{b}" for a, b in C.columns]; C = C.reset_index()
C = C[C.line_over == C.line_under].rename(columns={"line_over": "c_line", "book": "open_book"})
qo, qu = 1 / dec(C.price_over), 1 / dec(C.price_under); C["c_fair"] = qo / (qo + qu)
# features (v1b mean) + previous game date for the timing guard
F = pd.read_csv(FEAT, dtype={"player_id": str})
F = F.sort_values(["player_id", "date"]); F["prev_date"] = F.groupby("player_id").date.shift()
F["home_c"] = np.where(F.home == 1, F.team, F.opp); F["away_c"] = np.where(F.home == 1, F.opp, F.team)
FL = pd.concat([F[["date", "home_c", "away_c", "name", "n_prev", "min_proj", "prev_date", s, f"mu_{s}"]].rename(columns={s: "actual", f"mu_{s}": "mu"}).assign(stat=s)
                for s in STATS], ignore_index=True)
X = O.merge(FL, on=key, how="inner")
say(f"openers matched to a played game: {len(X)}")
X = X[(X.n_prev >= 3) & (X.lead_h >= 1) & (X.prev_date.isna() | (X.prev_date < X.open_date_et))].copy()
say(f"after timing guard (prev game on an earlier day than the opener; opener 1h+ before tip; 3+ games): {len(X)}")
for s in STATS:
    m = X.stat == s; a, b = P1["var_ab"][s]; mu = X.loc[m, "mu"].clip(lower=0.05)
    ex = (a - 1) * mu + b * mu ** 2; r = np.where(ex > 1e-6, mu ** 2 / ex.clip(lower=1e-6), 1e6)
    X.loc[m, "p_model"] = 1 - stats.nbinom.cdf(np.floor(X.loc[m, "line"]), r, r / (r + mu)); X.loc[m, "sd"] = np.sqrt(mu + mu ** 2 / r)
X["y"] = np.where(X.actual > X.line, 1.0, np.where(X.actual < X.line, 0.0, np.nan))
X = X.merge(C[key + ["open_book", "c_line", "c_fair"]], on=key + ["open_book"], how="left")
mc = X.c_line + X.sd * stats.norm.ppf(X.c_fair.clip(0.01, 0.99))
X["c_over_here"] = np.where(X.c_line == X.line, X.c_fair, 1 - stats.norm.cdf((X.line - mc) / X.sd))

# close over-lean per season (all DK/FD close pairs vs actual), for the leave-one-season-out adjustment
Cl = C[C.open_book.isin(["draftkings", "fanduel"])].merge(FL[key + ["actual"]], on=key)
Cl = Cl[Cl.actual != Cl.c_line]; Cl["season"] = pd.to_datetime(Cl.date).dt.year + (pd.to_datetime(Cl.date).dt.month >= 8)
lean = (Cl.groupby("season").c_fair.mean() - (Cl.actual > Cl.c_line).groupby(Cl.season).mean()).to_dict()
loso = {s: np.mean([v for k, v in lean.items() if k != s]) for s in lean}
say("close over-lean by season (no-vig over minus actual): " + ", ".join(f"{k} {v*100:+.2f}" for k, v in sorted(lean.items())))

# blend weight on 2022-23 openers
Fi = X[(X.season == FIT) & X.y.notna()]
ll = lambda w: -np.mean(Fi.y * np.log(np.clip(w * Fi.p_model + (1 - w) * Fi.p_open, 1e-6, 1)) + (1 - Fi.y) * np.log(np.clip(1 - (w * Fi.p_model + (1 - w) * Fi.p_open), 1e-6, 1)))
w = float(optimize.minimize_scalar(ll, bounds=(0, 1), method="bounded").x)
say(f"FIT 2022-23: w = {w:.3f} (log loss opener {ll(0):.4f}, model {ll(1):.4f}, blend {ll(w):.4f}, n {len(Fi)})")


def bets(X, w, ev_min=0.05):
    p = w * X.p_model + (1 - w) * X.p_open
    rows = []
    for side in ("over", "under"):
        ps = p if side == "over" else 1 - p
        rows.append(X.assign(side=side, price=X[f"open_price_{side}"], p_side=ps, ev=ps * dec(X[f"open_price_{side}"]) - 1))
    B = pd.concat(rows).sort_values("ev", ascending=False).drop_duplicates(key)
    B = B[(B.ev >= ev_min) & B.open_book.isin(["draftkings", "fanduel"])].copy()
    won = np.where(B.side == "over", B.actual > B.line, B.actual < B.line)
    B["u"] = np.where(B.actual == B.line, 0.0, np.where(won, dec(B.price) - 1, -1.0))
    cs = np.where(B.side == "over", B.c_over_here, 1 - B.c_over_here)
    adj = B.season.map(loso).fillna(np.mean(list(lean.values())))
    B["clev"] = cs * dec(B.price) - 1
    B["clev_adj"] = (cs + np.where(B.side == "under", adj, -adj)) * dec(B.price) - 1
    B["move"] = np.where(B.side == "under", B.line - B.c_line, B.c_line - B.line)
    return B


def boot(df, col, n=3000):
    g = df.groupby("date")[col].agg(["sum", "count"]).values
    if len(g) < 5: return np.nan, np.nan
    idx = rng.integers(0, len(g), (n, len(g))); m = g[idx, 0].sum(1) / g[idx, 1].sum(1)
    return np.percentile(m, 5), np.percentile(m, 95)


def line_(B):
    if not len(B): return "0 bets"
    lo, hi = boot(B, "u"); c = B[B.clev.notna()]
    return (f"{len(B):5d} bets | win {(B.u > 0).sum() / max((B.u != 0).sum(), 1)*100:5.1f}% | {B.u.sum():+7.1f}u ROI {B.u.mean()*100:+.1f}% [{lo*100:+.1f}, {hi*100:+.1f}] | "
            f"close-EV raw {c.clev.mean()*100:+.2f}% lean-adj {c.clev_adj.mean()*100:+.2f}% (n {len(c)}) | line move our way {c.move.mean():+.2f}")


Bm = bets(X, w); B0 = bets(X, 0.0)
U = X[X.open_book.isin(["draftkings", "fanduel"])].assign(side="under", price=lambda d: d.open_price_under)
U["u"] = np.where(U.actual == U.line, 0.0, np.where(U.actual < U.line, dec(U.price) - 1, -1.0))
say("\n== Model rule (EV >= 5% at the opening price, DK/FD openers) by season ==")
for s in sorted(Bm.season.unique()):
    tag = " TEST" if s in TEST else (" fit" if s == FIT else " (descr.)")
    say(f"  {s}{tag}: {line_(Bm[Bm.season == s])}")
T = Bm[Bm.season.isin(TEST)]; T0 = B0[B0.season.isin(TEST)]; TU = U[U.season.isin(TEST)]
lo, hi = boot(T, "u")
c1 = all(Bm[Bm.season == s].u.sum() > 0 for s in TEST) and lo > 0
c2 = T[T.clev.notna()].clev_adj.mean() >= 0
c3 = T.u.sum() > T0.u.sum() and T.u.sum() > TU.u.sum()
say(f"\nTEST pooled: {line_(T)}")
say(f"simple (a) same rule, no model (w=0): {line_(T0)}")
say(f"simple (b) every under at DK/FD openers: {len(TU)} bets, {TU.u.sum():+.1f}u ROI {TU.u.mean()*100:+.2f}%")
say(f"checks: 1 unseen seasons {'PASS' if c1 else 'fail'} | 2 lean-adjusted close-EV >= 0 {'PASS' if c2 else 'fail'} | 3 beats simple versions {'PASS' if c3 else 'fail'}"
    f" -> {'ALL PASS: Fable review next, then Jeffrey decides' if (c1 and c2 and c3) else 'does not qualify'}")
say("\n== Descriptive (test seasons) ==")
for thr in (0.03, 0.08, 0.12):
    b = bets(X, w, thr); say(f"  EV >= {int(thr*100)}%: {line_(b[b.season.isin(TEST)])}")
for col in ("stat", "side", "open_book"):
    for k, g in T.groupby(col): say(f"  {col}={k}: {line_(g)}")
T = T.assign(lead=pd.cut(T.lead_h, [1, 4, 12, 24, 48]))
for k, g in T.groupby("lead", observed=True): say(f"  opener posted {k} h before tip: {line_(g)}")
pd.concat([Bm.assign(rule="model"), B0.assign(rule="no_model")]).to_csv(os.path.join(W, "analysis", "props_v1b_opener_bets.csv.gz"), index=False)
open(os.path.join(W, "analysis", "props_v1b_opener_output.txt"), "w").write("\n".join(out) + "\n")
