"""Leakage audit of the step 3a NBA news bets. Pre-registration: research/spreads/STEP3A_LEAK_AUDIT_PREREG.md (pushed first).
Reuses the step 3a / step 1 builds (B = lag 1 + previous game's report, C = lag 1 + 8 PM night-before report).
  python analysis/spreads_step3a_leak_audit.py WORKDIR -> analysis/spreads_step3a_leak_audit_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "analysis", "spreads_step3a_nba.py")).read()
exec(src.split('say("NBA spreads, injury news')[0])            # G, LT, B, C, build, T, TS, key, EDGE, SEAS, say, out ...
out.clear()
rng2 = np.random.default_rng(20261104)

# oracle: lag 1 + the game-day pre-tip report (latest report >= 60 min before tip) as today's injury input
TO = T.copy()
for side in ("home", "away"):
    for c in ("miss_off", "miss_def", "n_out"):
        TO[f"{side}_{c}_open"] = TO[f"{side}_{c}"]
TS_saved = TS; TS = TO; O_ = build(1, "prev"); TS = TS_saved

G = G.merge(B[key + ["sp_model"]].rename(columns={"sp_model": "sp_B"}), on=key, how="left") \
     .merge(O_[key + ["sp_model"]].rename(columns={"sp_model": "sp_O"}), on=key, how="left")
G["d"] = G.sp_model - G.sp_B              # the 8 PM report's adjustment (home margin pts)
G["d_O"] = G.sp_O - G.sp_B                # the game-day report's adjustment
for k_ in ("T0", "T1", "T2"):
    G[f"{k_}_sp"] = LT[k_].sp.reindex(pd.MultiIndex.from_frame(G[key])).values

def sel(sp, tk, need_news=True):
    """v2 bets with model sp at line tk; with need_news, only sides B did not bet at the opener."""
    ln = G[f"{tk}_sp"].values; e = sp + ln; home = e > 0
    res = np.where(home, G.margin + ln, -(G.margin + ln)); clv = np.where(home, ln - G.close_sp, G.close_sp - ln)
    mv = np.where(home, G.open_sp - ln, ln - G.open_sp)
    us = np.where(home, G.h_cat, G.a_cat); them = np.where(home, G.a_cat, G.h_cat); arr = pd.Series(np.where(home, G.h_arr, G.a_arr)).fillna(0).values
    late_ok = pd.notna(us) & pd.notna(them) & (us != "tanking") & (them != "middle") & (arr == 0)
    v2 = (np.abs(e) >= EDGE) & ~np.isnan(ln) & ~(home & (ln > 0)) & (~G.late.values | late_ok)
    m = v2 & (G.bside_B.values != np.sign(e)) if need_news else v2
    side = np.where(home, 1, -1)
    return pd.DataFrame(dict(m=m, res=res, clv=clv, mv=mv, side=side, e=e, season=G.season.values))

def rec(D, m=None):
    b = D[D.m] if m is None else D[D.m & m]
    w, l = int((b.res > 0).sum()), int((b.res < 0).sum())
    return w, l, w * 100 / 110 - l, b.clv.mean() if len(b) else np.nan, b.mv.mean() if len(b) else np.nan
def show(lab, D, m=None):
    w, l, u, c, mv = rec(D, m); n = w + l
    say(f"  {lab:<58} {w:3d}-{l:<3d} {w / max(n, 1):6.1%} {u:+6.1f}u  CLV {c:+.2f}  moved since open {mv:+.2f}")

say("Leakage audit of step 3a news bets (prereg research/spreads/STEP3A_LEAK_AUDIT_PREREG.md)")
say(f"games: {len(G)}; 8 PM report adjustment |d| mean {G.d.abs().mean():.2f} pts, share |d|>=1: {(G.d.abs() >= 1).mean():.0%};"
    f" game-day adjustment |d_O| mean {G.d_O.abs().mean():.2f}; corr(d, d_O) {G[['d', 'd_O']].corr().iloc[0, 1]:.2f}")

say("\n1. Reproduce N (C model, T1) and the no-report twin N_B (B model, T1)")
N = sel(G.sp_model.values, "T1"); NB = sel(G.sp_B.values, "T1")
show("N  (C, 8 PM report)", N)
show("N_B (B, no report)", NB)
show("N bets that are ALSO N_B bets (same side)", N, NB.m.values & (NB.side.values == N.side.values))
show("N bets that exist only because of the report", N, ~(NB.m.values & (NB.side.values == N.side.values)))
show("N_B bets the report removed", NB, ~(N.m.values & (N.side.values == NB.side.values)))
for k_ in ("T0", "T2"):
    show(f"N_B at {k_}", sel(G.sp_B.values, k_))

say("\n2. Placebo: 8 PM adjustment d shuffled across games within each season (1,000 shuffles), N rebuilt at T1")
w0 = rec(N)[0]; n0 = sum(rec(N)[:2]); sims = []
for _ in range(1000):
    dd = G.groupby("season").d.transform(lambda s: pd.Series(rng2.permutation(s.values), index=s.index)).values
    P = sel(G.sp_B.values + dd, "T1"); w, l = rec(P)[:2]; sims.append((w, l))
sims = np.array(sims); wr = sims[:, 0] / np.maximum(sims.sum(1), 1)
say(f"  observed {w0}-{n0 - w0} ({w0 / n0:.1%}); placebo win % median {np.median(wr):.1%} [5-95%: {np.percentile(wr, 5):.1%}, {np.percentile(wr, 95):.1%}],"
    f" bets median {int(np.median(sims.sum(1)))}; placebo p (win % >= observed) = {(wr >= w0 / n0).mean():.3f}")

say("\n3. Where the N wins come from")
b = N.m.values
agree = np.abs(G.d_O.values - G.d.values) < 0.5
toward = np.sign(G.d.values) == N.side.values           # report adjustment points to our side
big = np.abs(G.d.values) >= 1
close_away = N.clv.values <= 0
show("game-day report agreed with 8 PM (|d_O - d| < 0.5)", N, agree)
show("game-day report changed it", N, ~agree)
show("report pushes toward our side by 1+ pt", N, toward & big)
show("report small (<1 pt) or against our side", N, ~(toward & big))
show("CLV <= 0 (close did not move toward us)", N, close_away)
show("CLV > 0", N, ~close_away)
cell = agree & close_away
wins = (N.res.values > 0) & b
say(f"  leakage cell (report agreed with game day AND close did not move toward us): {int((wins & cell).sum())} of {int(wins.sum())} N wins"
    f" ({(wins & cell).sum() / max(wins.sum(), 1):.0%}); its record:")
show("  leakage cell", N, cell)
say("  per season:")
for s in SEAS: show(f"    {s}", N, G.season.values == s)

say("\n4. Oracle: game-day pre-tip report instead of the 8 PM report")
for k_ in ("T1", "T2"):
    show(f"oracle news bets at {k_} (O model, B had no opener bet)", sel(G.sp_O.values, k_))
show("8 PM news bets at T2 (C model), for comparison", sel(G.sp_model.values, "T2"))
say("\n  accuracy on all games (MAE vs final margin): "
    f"B {(G.sp_B - G.margin).abs().mean():.3f}, C 8 PM {(G.sp_model - G.margin).abs().mean():.3f}, oracle {(G.sp_O - G.margin).abs().mean():.3f};"
    f" DK close {(-G.close_sp - G.margin).abs().mean():.3f}")
m_ = N.m.values
say(f"  on the N games: B {(G.sp_B - G.margin).abs()[m_].mean():.2f}, C {(G.sp_model - G.margin).abs()[m_].mean():.2f},"
    f" oracle {(G.sp_O - G.margin).abs()[m_].mean():.2f}, DK T1 line {(-G.T1_sp - G.margin).abs()[m_].mean():.2f}, DK close {(-G.close_sp - G.margin).abs()[m_].mean():.2f}")
G.loc[m_, key + ["season", "T1_sp", "close_sp", "open_sp", "sp_B", "sp_model", "sp_O", "d", "d_O", "margin"]].assign(
    side=N.side.values[m_], res=N.res.values[m_], clv=N.clv.values[m_]).to_csv(os.path.join(W, "analysis", "spreads_step3a_leak_audit_bets.csv"), index=False)
open(os.path.join(W, "analysis", "spreads_step3a_leak_audit_output.txt"), "w").write("\n".join(out) + "\n")
