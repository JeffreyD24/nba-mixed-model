"""Spreads step 3a (NBA): injury news after the opener, graded at the DraftKings line when it can be acted on.
Pre-registration: research/spreads/STEP3A_NBA_INJURY_NEWS_PREREG.md (pushed before this ran).
Reuses the model build from analysis/spreads_step1_nba.py (B = lag 1 + previous report, C = lag 1 + 8 PM report).
  python analysis/spreads_step3a_nba.py WORKDIR -> analysis/spreads_step3a_nba_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
step1 = open(os.path.join(W, "analysis", "spreads_step1_nba.py")).read().split("V = {")[0]
exec(step1)                       # defines build(), key, LINES, T, say(), out, rng ...
out.clear()
B, C = build(1, "prev"), build(1, "8pm")

# report snapshot used for the 8 PM-side inputs (home team): keep 8 PM / 9 PM night-before only
SN = pd.read_csv(os.path.join(W, "data", "training_games.csv"))[key + ["snap_open_home"]]
SN["ok"] = SN.snap_open_home.astype(str).str.endswith(("_08PM", "_09PM"))
# DraftKings spread at given hours relative to game-day midnight
S2 = S.copy(); S2["et"] = S2.t.dt.tz_convert("America/New_York").dt.tz_localize(None); S2["gd"] = pd.to_datetime(S2.date)
def line_at(h):
    x = S2[S2.et <= S2.gd + pd.Timedelta(hours=h)].groupby(key).tail(1)
    return x.set_index(key)[["sp", "sp_px_h", "sp_px_a"]]
LT = {"T0": line_at(-4.0), "T1": line_at(-2.0), "T2": line_at(7.0)}

G = C.merge(SN[key + ["ok"]], on=key, how="left").merge(B[key + ["e", "v2"]].rename(columns={"e": "e_B", "v2": "v2_B"}), on=key, how="left")
G = G[G.ok.fillna(False)].copy()
G["bside_B"] = np.where(G.v2_B.fillna(False), np.sign(G.e_B), 0)
idx = pd.MultiIndex.from_frame(G[key])
for k, L_ in LT.items():
    G[f"{k}_sp"] = L_.sp.reindex(idx).values

def bets(tk):
    ln = G[f"{tk}_sp"]; e = G.sp_model + ln; home = e > 0
    res = np.where(home, G.margin + ln, -(G.margin + ln)); clv = np.where(home, ln - G.close_sp, G.close_sp - ln)
    mv = np.where(home, G.open_sp - ln, ln - G.open_sp)          # + = line moved toward the bet since the open (price got worse)
    home_dog = home & (ln > 0)
    us = np.where(home, G.h_cat, G.a_cat); them = np.where(home, G.a_cat, G.h_cat); arr = pd.Series(np.where(home, G.h_arr, G.a_arr)).fillna(0).values
    late_ok = pd.notna(us) & pd.notna(them) & (us != "tanking") & (them != "middle") & (arr == 0)
    v2 = (e.abs() >= EDGE) & ln.notna() & ~home_dog & (~G.late | late_ok)
    news = v2 & (G.bside_B != np.sign(e))                        # B made no v2 bet on this side at the opener
    against = mv <= -0.5
    return pd.DataFrame(dict(season=G.season.values, res=res, clv=clv, mv=mv, v2=v2.values, news=news.values, against=against, e=e.values), index=G.index)

def summ(D, m):
    b = D[m]; w, l = int((b.res > 0).sum()), int((b.res < 0).sum()); n = w + l
    r = np.where(b.res > 0, 100 / 110, np.where(b.res < 0, -1.0, 0.0))
    bs = np.array([rng.choice(r, len(r)).mean() * 100 for _ in range(2000)]) if len(r) else np.array([np.nan])
    cb = np.array([rng.choice(b.clv.values, len(b)).mean() for _ in range(2000)]) if len(b) else np.array([np.nan])
    return n, w / max(n, 1), w * 100 / 110 - l, np.percentile(bs, 5), np.percentile(bs, 95), b.clv.mean(), np.percentile(cb, 5), np.percentile(cb, 95), b.mv.mean()
def row(lab, D, m):
    n, wp, u, lo, hi, c, clo, chi, mv = summ(D, m)
    per = " ".join(f"{s}:{summ(D, m & (D.season == s))[2]:+.1f}" for s in SEAS)
    say(f"  {lab:<44} {n:4d} {wp:.1%} {u:+6.1f}u  [{lo:+5.1f},{hi:+5.1f}]/100  CLV {c:+.2f} [{clo:+.2f},{chi:+.2f}]  moved since open {mv:+.2f} | {per}")

say("NBA spreads, injury news after the opener (prereg research/spreads/STEP3A_NBA_INJURY_NEWS_PREREG.md)")
say(f"games with an 8/9 PM night-before report (home side): {len(G)} of {len(C)}; line found T0 {G.T0_sp.notna().mean():.0%}, T1 {G.T1_sp.notna().mean():.0%}, T2 {G.T2_sp.notna().mean():.0%}")
say("columns: bets, win %, units at -110, 90% units/100, CLV vs DK close [90%], avg pts the line moved toward the bet since the open | per season")
D = {k: bets(k) for k in LT}
for k, lab in (("T1", "T1 10 PM night before"), ("T2", "T2 7 AM game day"), ("T0", "T0 8 PM, before the report (diagnostic, not bettable)")):
    d = D[k]; say(f"\n{lab}")
    row("N news bets (PRIMARY)" if k != "T0" else "N news bets", d, d.news)
    row("  N, line not moved 0.5+ against since open", d, d.news & ~d.against)
    row("W all v2 bets at this line, minus moved-against", d, d.v2 & ~d.against)
    row("W, all v2 bets at this line", d, d.v2)
# step-1 B at the opener on the same games (for W comparison) and B + N
Bs = B.merge(G[key], on=key)
say("\nComparison on the same games")
bres = Bs[Bs.v2]; w, l = int((bres.res > 0).sum()), int((bres.res < 0).sum())
say(f"  B v2 at the opener: {w + l} {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+.1f}u CLV {bres.clv.mean():+.2f}")
for k in ("T1", "T2"):
    d = D[k]; nb = d[d.news & ~G.v2_B.fillna(False).values]          # one bet per game: N only where B did not bet the game
    w2, l2 = int((nb.res > 0).sum()), int((nb.res < 0).sum())
    say(f"  B + N at {k}: {w + l + w2 + l2} bets, {(w * 100 / 110 - l) + (w2 * 100 / 110 - l2):+.1f}u (N added {w2 + l2} bets {w2 * 100 / 110 - l2:+.1f}u, CLV {nb.clv.mean():+.2f})")
open(os.path.join(W, "analysis", "spreads_step3a_nba_output.txt"), "w").write("\n".join(out) + "\n")
