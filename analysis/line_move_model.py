"""NBA line-move model: does the game-day injury report predict DraftKings' remaining spread / total move, and can we bet it at +15 min?
Rules: research/spreads/LINE_MOVE_MODEL_PREREG.md (pushed before any result).   python3 analysis/line_move_model.py"""
import os, numpy as np, pandas as pd
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *p: os.path.join(W, *p)
out = []; say = lambda s="": (print(s), out.append(s))
key = ["date", "home", "away"]

T = pd.read_csv(J("data", "training_games.csv"))
T = T[T.snap_open_home.astype(str).str.endswith(("_08PM", "_09PM"))].copy()
T["slot"] = pd.to_datetime(T.snap_pretip_home, format="%Y-%m-%d_%I%p", errors="coerce")
T = T[T.slot.notna() & (T.slot.dt.strftime("%Y-%m-%d") == T.date)].copy()
T["slot_utc"] = T.slot.dt.tz_localize("America/New_York").dt.tz_convert("UTC")
d = {f"d{k}_{s}": T[f"{s}_miss_{k}"] - T[f"{s}_miss_{k}_open"] for k in ("off", "def") for s in ("home", "away")}
T["N_sp"] = -(d["doff_home"] + d["ddef_home"]) + (d["doff_away"] + d["ddef_away"])
T["N_tot"] = -(d["doff_home"] + d["doff_away"]) + (d["ddef_home"] + d["ddef_away"])

S = pd.read_csv(J("data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "t", "tip", "book", "sp", "tot", "date"])
S = S[S.book == "draftkings"]; S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True)
S = S[S.t < S.tip].sort_values("t")
S = S.merge(T[key + ["slot_utc"]], on=key)
ACT = pd.Timedelta(minutes=15)
rows = {}
for mk, col in (("sp", "sp"), ("tot", "tot")):
    s = S.dropna(subset=[col]); g = s.groupby(key)
    o = g.head(1).set_index(key)[col].rename(f"{mk}_open"); c = g.tail(1).set_index(key)[col].rename(f"{mk}_close")
    pre = s[s.t <= s.slot_utc].groupby(key).tail(1).set_index(key)[col].rename(f"{mk}_pre")
    a = s[s.t >= s.slot_utc + ACT].groupby(key).head(1).set_index(key)
    rows[mk] = pd.concat([o, pre, a[col].rename(f"{mk}_act"), a.t.rename(f"{mk}_act_t"), c], axis=1)
G = T.merge(rows["sp"].reset_index(), on=key).merge(rows["tot"].reset_index(), on=key)
for mk in ("sp", "tot"): G = G[G[f"{mk}_act"].notna() & G[f"{mk}_pre"].notna()]
# spreads as home margin L = -spread
for t in ("open", "pre", "act", "close"): G[f"L_{t}"] = -G[f"sp_{t}"]; G[f"Q_{t}"] = G[f"tot_{t}"]
G["margin"] = G.home_pts - G.away_pts; G["pts"] = G.home_pts + G.away_pts
G["split"] = np.where(G.season.isin([2022, 2023]), "build", "test")
say("# NBA line-move model (game-day report -> DraftKings move), results"); say()
say(f"games with 8/9 PM open report, game-day pretip slot and DK lines at every point: {len(G)} "
    + str(G.groupby("season").size().to_dict()))
say(f"minutes from slot to the act line: median {((G.sp_act_t - G.slot_utc).dt.total_seconds()/60).median():.0f}, "
    f"90th pct {((G.sp_act_t - G.slot_utc).dt.total_seconds()/60).quantile(.9):.0f}; slot hour counts {G.slot.dt.hour.value_counts().to_dict()}")
say()

def ols(y, X):
    X = np.column_stack([np.ones(len(X))] + [np.asarray(x, float) for x in X]); b, *_ = np.linalg.lstsq(X, np.asarray(y, float), rcond=None)
    r = np.asarray(y) - X @ b; s2 = r @ r / (len(y) - X.shape[1]); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X))); return b, se
B = G.split == "build"
RES = {}
for mk, Lp, N, outc, lab in (("sp", "L", "N_sp", "margin", "SPREADS (home margin)"), ("tot", "Q", "N_tot", "pts", "TOTALS")):
    say(f"## {lab}")
    G[f"{mk}_moved"] = G[f"{Lp}_act"] - G[f"{Lp}_open"]; G[f"{mk}_after"] = G[f"{Lp}_close"] - G[f"{Lp}_act"]
    b, se = ols(G.loc[B, f"{mk}_after"], [G.loc[B, N], G.loc[B, f"{mk}_moved"]])
    say(f"build fit: move after act = {b[0]:+.3f} + {b[1]:+.3f} x N (se {se[1]:.3f}) + {b[2]:+.3f} x moved so far (se {se[2]:.3f})")
    bf, sef = ols(G.loc[B, f"{Lp}_close"] - G.loc[B, f"{Lp}_open"], [G.loc[B, N]])
    say(f"build: full open-to-close move per point of news {bf[1]:+.3f} (se {sef[1]:.3f})")
    G[f"{mk}_R"] = b[1] * G[N] + b[2] * G[f"{mk}_moved"]
    # break-even CLV on build: logistic of (outcome beats act line for the home side / over) on CLV of that side
    import statsmodels.api as sm
    win = (G[outc] > G[f"{Lp}_act"]).astype(float); push = G[outc] == G[f"{Lp}_act"]
    clv_home = G[f"{Lp}_close"] - G[f"{Lp}_act"]
    m = sm.Logit(win[B & ~push], sm.add_constant(clv_home[B & ~push])).fit(disp=0)
    be = (np.log(0.5238 / 0.4762) - m.params.iloc[0]) / m.params.iloc[1]
    say(f"break-even CLV (build, win chance 52.38%): {be:+.2f} pts (slope {m.params.iloc[1]:+.3f} logit per pt)")
    # bets
    def bets(mask, th):
        g = G[mask & (G[f"{mk}_R"].abs() >= th)]; side = np.sign(g[f"{mk}_R"])
        clv = side * (g[f"{Lp}_close"] - g[f"{Lp}_act"]); res = side * (g[outc] - g[f"{Lp}_act"])
        u = np.where(res > 0, 100 / 110, np.where(res < 0, -1.0, 0.0))
        return pd.DataFrame(dict(season=g.season, clv=clv, u=u, w=res > 0, push=res == 0, N=g[N], moved=g[f"{mk}_moved"], side=side))
    def line(D, lab):
        if D.empty: return f"| {lab} | 0 | | | | |"
        per = D.groupby("season").agg(u=("u", "sum"), c=("clv", "mean"), n=("u", "size"))
        wp = D.w.sum() / max(1, (~D.push).sum()) * 100
        return (f"| {lab} | {len(D)} | {D.clv.mean():+.2f} | {D.u.sum():+.1f}u ({D.u.mean()*100:+.1f}%) | {wp:.1f}% | "
                + " ".join(f"{s%100:02d}: {r.n} bets {r.u:+.1f}u CLV {r.c:+.2f}" for s, r in per.iterrows()) + " |")
    say("| Set | Bets | CLV | Units | Win % | By season |"); say("|---|---|---|---|---|---|")
    cand = []
    for th in (0.5, 0.75, 1.0):
        D = bets(B, th); say(line(D, f"build, theta {th}"))
        if len(D) >= 50: cand.append((D.clv.mean(), th))
    TH = max(cand)[1] if cand else 0.5
    D = bets(~B, TH); say(line(D, f"**TEST 2023-26, theta {TH} (chosen on build)**"))
    pos = (D.groupby("season").clv.mean() > 0).sum()
    verdict = ("PASS" if (D.clv.mean() >= be and D.u.sum() > 0 and pos >= 2) else
               "PARTIAL" if D.clv.mean() > 0 else "FAIL")
    say(f"verdict: **{verdict}** (CLV {D.clv.mean():+.2f} vs break-even {be:+.2f}; units {D.u.sum():+.1f}; CLV positive in {pos} of 3 seasons)")
    RES[mk] = dict(verdict=verdict, D=D, be=be)
    say(); say("Absorption, |N| >= 1.5 (share of the build-fitted full move; descriptive):")
    big = G[G[N].abs() >= 1.5]; full = bf[1] * big[N]
    for t in ("pre", "act", "close"):
        sh = (big[f"{Lp}_{t}"] - big[f"{Lp}_open"]) / full
        say(f"  {t:>5}: median {sh.median():.0%} (IQR {sh.quantile(.25):.0%} to {sh.quantile(.75):.0%}), n {len(big)}")
    say()
    # exploratory split (labelled): bets where most of the predicted move comes from news vs from momentum
    D2 = bets(~B, TH); say("Exploratory, test seasons: news share of R")
    nshare = (b[1] * D2.N).abs() >= (b[2] * D2.moved).abs()
    say("| Set | Bets | CLV | Units | Win % | By season |"); say("|---|---|---|---|---|---|")
    say(line(D2[nshare], "mostly news")); say(line(D2[~nshare], "mostly momentum (moved-so-far term)")); say()

G.to_csv(J("analysis", "line_move_model_games.csv.gz"), index=False)
open(J("analysis", "line_move_model_output.txt"), "w").write("\n".join(out) + "\n")
