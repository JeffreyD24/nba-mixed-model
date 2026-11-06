"""Cap the "moved toward the model" BET rule at moves under 3 pts? (NBA spreads, NFL spreads, NFL totals; Nov 6, 2026)

Pre-registered: betting-goals/models/tests/MOVE_CAP_PREREG.md (pushed before this was graded). Lead: NBA totals 2023-26, first
snapshot moved 3+ toward the model with 3+ left: 242 bets 51.7% -2.9u vs moved 0.5-2.5: 675 bets 55.0% +34.6u
(analysis/fast_move_units.py). This checks markets the lead was NOT found in.

  python analysis/move_cap_test.py .  [--counts]   (run from nba-mixed-model; needs ../nfl-mixed-model next to it)
  -> analysis/move_cap_test_output.txt, analysis/move_cap_test_bets.csv.  --counts prints bet counts only (no grading)."""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
COUNTS = "--counts" in sys.argv
sys.path.insert(0, W)
from analysis.odds_openers import NAME as NBA_NAME  # noqa: E402
NFL = os.path.join(os.path.dirname(W), "nfl-mixed-model")
NFL_NAME = {"Arizona Cardinals": "ari", "Atlanta Falcons": "atl", "Baltimore Ravens": "bal", "Buffalo Bills": "buf",
            "Carolina Panthers": "car", "Chicago Bears": "chi", "Cincinnati Bengals": "cin", "Cleveland Browns": "cle",
            "Dallas Cowboys": "dal", "Denver Broncos": "den", "Detroit Lions": "det", "Green Bay Packers": "gb",
            "Houston Texans": "hou", "Indianapolis Colts": "ind", "Jacksonville Jaguars": "jax", "Kansas City Chiefs": "kc",
            "Los Angeles Chargers": "lac", "Los Angeles Rams": "lar", "Las Vegas Raiders": "lv", "Oakland Raiders": "lv",
            "Miami Dolphins": "mia", "Minnesota Vikings": "min", "New England Patriots": "ne", "New Orleans Saints": "no",
            "New York Giants": "nyg", "New York Jets": "nyj", "Philadelphia Eagles": "phi", "Pittsburgh Steelers": "pit",
            "San Francisco 49ers": "sf", "Seattle Seahawks": "sea", "Tampa Bay Buccaneers": "tb", "Tennessee Titans": "ten",
            "Washington Commanders": "was", "Washington Football Team": "was", "Washington Redskins": "was"}
TMP = os.path.join(W, "_tmp"); os.makedirs(TMP, exist_ok=True)
try:
    import derived; derived.ensure(W, ["dk_nba_snaps_2023-10-01.csv.gz", "dk_nfl_snaps_2020-08-01.csv.gz"])
except Exception:
    pass
BOOT, SEED, CUT, LEFT = 10000, 20261106, 3.0, 3.0


def load_dk(sport, start):
    """all DK pregame spread and total rows from the Odds API daily files on/after start"""
    cache = os.path.join(TMP, f"dk_{sport}_snaps_{start}.csv.gz")
    if os.path.exists(cache): return pd.read_csv(cache)
    parts = []
    for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", sport, "*.csv.gz"))):
        if os.path.basename(f)[:10] < start: continue
        d = pd.read_csv(f)
        d = d[(d.book == "draftkings") & d.market.isin(["spreads", "totals"])]
        if len(d): parts.append(d[["snapshot_utc", "event_id", "commence_et", "home", "away", "market", "outcome", "price", "point"]])
    S = pd.concat(parts, ignore_index=True).drop_duplicates()
    S.to_csv(cache, index=False, compression="gzip")
    return S


def to_snaps(S, names):
    """one row per event, market, snapshot: L on the model scale (home margin or total), home/over price, away/under price"""
    S = S.copy()
    S["t"] = pd.to_datetime(S.snapshot_utc, utc=True)
    S["tip"] = pd.to_datetime(S.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    S = S[S.t < S.tip]
    out = []
    sp = S[S.market == "spreads"]
    h = sp[sp.outcome == sp.home][["event_id", "t", "tip", "home", "away", "point", "price"]].rename(columns={"point": "hp", "price": "p_a"})
    a = sp[sp.outcome == sp.away][["event_id", "t", "point", "price"]].rename(columns={"point": "ap", "price": "p_b"})
    m = h.merge(a, on=["event_id", "t"]); m = m[m.hp == -m.ap]
    out.append(m.assign(market="spread", L=-m.hp).drop(columns=["hp", "ap"]))
    tt = S[S.market == "totals"]
    o = tt[tt.outcome == "Over"][["event_id", "t", "tip", "home", "away", "point", "price"]].rename(columns={"point": "L", "price": "p_a"})
    u = tt[tt.outcome == "Under"][["event_id", "t", "point", "price"]].rename(columns={"point": "pu", "price": "p_b"})
    m = o.merge(u, on=["event_id", "t"]); m = m[m.L == m.pu]
    out.append(m.assign(market="total").drop(columns="pu"))
    X = pd.concat(out, ignore_index=True).drop_duplicates(["event_id", "market", "t"]).sort_values(["event_id", "market", "t"])
    X["home"] = X.home.map(names); X["away"] = X.away.map(names)
    X["date"] = X.tip.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    return X


# ---- NBA spreads 2023-24..2025-26: Model 1 opener margin (every game with opener edge 3+)
P = pd.read_csv(os.path.join(W, "analysis", "spread_autopsy_bets.csv"))
P = P[["season", "date", "home", "away", "pred_margin", "home_pts", "away_pts"]].drop_duplicates(["date", "home", "away"])
nba = to_snaps(load_dk("nba", "2023-10-01"), NBA_NAME)
nba = nba[nba.market == "spread"].merge(P, on=["date", "home", "away"], how="inner")
nba = nba.assign(mkt="NBA spreads", M=nba.pred_margin, act=nba.home_pts - nba.away_pts)

# ---- NFL spreads and totals 2020-2025: walk-forward opener-time (early) model numbers
Q = pd.concat([pd.read_csv(os.path.join(NFL, "backtests", f"predictions_{y}.csv")) for y in range(2020, 2026)], ignore_index=True)
Q = Q[["season", "date", "home", "away", "pred_margin_early", "pred_total_early", "home_pts", "away_pts"]].dropna(subset=["home_pts"])
nfl = to_snaps(load_dk("nfl", "2020-08-01"), NFL_NAME)
# NFL dates: kickoff ET date can differ from the schedule date only for odd cases; match on teams within 1 day
nfl["d"] = pd.to_datetime(nfl.date); Q["d"] = pd.to_datetime(Q.date)
nfl = nfl.merge(Q.drop(columns="date"), on=["home", "away"], how="inner")
nfl = nfl[(nfl.d_x - nfl.d_y).abs() <= pd.Timedelta(days=1)].drop(columns=["d_x", "d_y"])
nfl["M"] = np.where(nfl.market == "spread", nfl.pred_margin_early, nfl.pred_total_early)
nfl["act"] = np.where(nfl.market == "spread", nfl.home_pts - nfl.away_pts, nfl.home_pts + nfl.away_pts)
nfl["mkt"] = np.where(nfl.market == "spread", "NFL spreads", "NFL totals")

cols = ["mkt", "season", "event_id", "date", "home", "away", "t", "tip", "L", "p_a", "p_b", "M", "act"]
S = pd.concat([nba[cols], nfl[cols]], ignore_index=True).sort_values(["mkt", "event_id", "t"])
g = S.groupby(["mkt", "event_id"])
S["open"] = g.L.transform("first"); S["t0"] = g.t.transform("first")
S["hrs"] = (S.t - S.t0).dt.total_seconds() / 3600
S["side"] = np.sign(S.M - S.open)
S = S[S.side != 0]
S["mv"] = (S.L - S.open) * S.side
S["left"] = (S.M - S.L) * S.side

B = S[(S.mv >= CUT) & (S.left >= LEFT)].groupby(["mkt", "event_id"]).first().reset_index().assign(design="B moved 3+")
Sm = S[(S.mv >= 0.5) & (S.mv < CUT) & (S.left >= LEFT)]
Sm = Sm.set_index(["mkt", "event_id"]); Sm = Sm[~Sm.index.isin(B.set_index(["mkt", "event_id"]).index)].reset_index()
Sm = Sm.groupby(["mkt", "event_id"]).first().reset_index().assign(design="S moved 0.5-2.5")
D = pd.concat([B, Sm], ignore_index=True)

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
MK = ["NBA spreads", "NFL spreads", "NFL totals"]
say("Move cap test (pre-registered: betting-goals/models/tests/MOVE_CAP_PREREG.md)")
for mk in MK:
    s = S[S.mkt == mk]
    say(f"  {mk}: {s.event_id.nunique()} games with snapshots + model number, seasons {sorted(s.season.unique())}, "
        f"median {s.groupby('event_id').size().median():.0f} snapshots/game")
say("\nBet counts (design x market):")
say(D.groupby(["design", "mkt"]).size().unstack(fill_value=0).to_string())
if COUNTS: sys.exit(0)


def dec(am):
    am = pd.Series(am).fillna(-110).values
    return np.where(am > 0, 1 + am / 100, 1 + 100 / -am)
def grade(G, at_open=False):
    line = G.open if at_open else G.L
    r = (G.side * (G.act - line)).values
    pr = np.full(len(G), -110.0) if at_open else np.where(G.side > 0, G.p_a, G.p_b)
    d = dec(pr)
    return r, np.where(r > 0, d - 1, np.where(r < 0, -1.0, 0.0))
D["res"], D["units"] = grade(D)
D["units_at_open"] = grade(D, at_open=True)[1]

def row(G, lab, at_open=False):
    if not len(G): say(f"  {lab:40s}    0 bets"); return
    r, u = grade(G, at_open); w, l = int((r > 0).sum()), int((r < 0).sum())
    say(f"  {lab:40s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {u.sum():+7.1f}u ({u.sum() / max(len(G), 1) * 100:+5.1f}/100)")

say("\nResults (graded at the snapshot line and DK price; 'at open' = same games at the DK opener, -110)")
for mk in MK + ["POOLED"]:
    say(f"\n{mk}")
    G = D if mk == "POOLED" else D[D.mkt == mk]
    row(G[G.design.str.startswith("B")], "B: first moved 3+ toward, 3+ left")
    row(G[G.design.str.startswith("B")], "   same B games at the opener", at_open=True)
    row(G[G.design.str.startswith("S")], "S: moved 0.5-2.5 toward, 3+ left")
    if mk != "POOLED":
        for s in sorted(G.season.unique()):
            Gs = G[G.season == s]
            row(Gs[Gs.design.str.startswith("B")], f"   {s} B"); row(Gs[Gs.design.str.startswith("S")], f"   {s} S")

say("\nB by edge left (pooled, descriptive)")
Bp = D[D.design.str.startswith("B")]
for lo, hi in [(3, 4), (4, 6), (6, 99)]:
    row(Bp[(Bp.left >= lo) & (Bp.left < hi)], f"  edge left {lo}-{hi if hi < 99 else '+'}")

# ---- primary test: pooled ROI(B) - ROI(S), bootstrap games within market
rng = np.random.default_rng(SEED)
def roi(G): return G.units.mean() if len(G) else np.nan
diffs = np.empty(BOOT)
parts = {(mk, d): D[(D.mkt == mk) & (D.design.str.startswith(d))].units.values for mk in MK for d in "BS"}
for i in range(BOOT):
    b = np.concatenate([rng.choice(parts[(mk, "B")], len(parts[(mk, "B")])) for mk in MK if len(parts[(mk, "B")])])
    s = np.concatenate([rng.choice(parts[(mk, "S")], len(parts[(mk, "S")])) for mk in MK if len(parts[(mk, "S")])])
    diffs[i] = b.mean() - s.mean()
GB, GS = D[D.design.str.startswith("B")], D[D.design.str.startswith("S")]
rB, rS = roi(GB), roi(GS)
wB = (GB.res > 0).sum() / max((GB.res != 0).sum(), 1)
p90 = np.percentile(diffs, 90)
mk_dir = sum(roi(GB[GB.mkt == mk]) < roi(GS[GS.mkt == mk]) for mk in MK if len(GB[GB.mkt == mk]) and len(GS[GS.mkt == mk]))
say("\nPRIMARY TEST (pooled ROI per bet, B minus S)")
say(f"  B {len(GB)} bets ROI {rB * 100:+.1f}/100, win {wB:.1%} | S {len(GS)} bets ROI {rS * 100:+.1f}/100")
say(f"  difference {(rB - rS) * 100:+.1f}/100; bootstrap 90% range {np.percentile(diffs, 5) * 100:+.1f} to {np.percentile(diffs, 95) * 100:+.1f}; "
    f"90th percentile {p90 * 100:+.1f}; share of draws >= 0: {(diffs >= 0).mean():.1%}")
say(f"  markets with B ROI < S ROI: {mk_dir} of 3")
if rB >= rS or wB >= 0.524: v = "REJECTED"
elif len(GB) >= 60 and rB < 0 and p90 < 0 and mk_dir >= 2: v = "CONFIRMED"
else: v = "INCONCLUSIVE"
say(f"  VERDICT (pre-registered rule): {v}")

D.to_csv(os.path.join(W, "analysis", "move_cap_test_bets.csv"), index=False)
open(os.path.join(W, "analysis", "move_cap_test_output.txt"), "w").write("\n".join(out) + "\n")
