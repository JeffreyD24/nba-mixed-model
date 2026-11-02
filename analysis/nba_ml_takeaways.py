"""What can we use from the NBA moneyline model? Price caps (no long shots), away/favorite splits, and the moneyline model as a
confirmation filter for the live spread bets. Live spread model margins, DraftKings openers, 2023-24..2025-26.
  python analysis/nba_ml_takeaways.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "analysis", "nba_moneyline.py")).read().split('print("units by season')[0]
exec(src.replace("W = os.path.abspath(sys.argv[1]); sys.argv = [\"x\", W]", "sys.argv = ['x', W]"))
G["p"] = np.nan
for s in SEAS:
    te = G.season == s; m = LogisticRegression(C=100).fit(G.loc[~te, ["m_live"]], G.loc[~te, "hw"]); G.loc[te, "p"] = m.predict_proba(G.loc[te, ["m_live"]])[:, 1]
dh, da = dec(G.ml_h), dec(G.ml_a); evh, eva = G.p * dh - 1, (1 - G.p) * da - 1
home = evh >= eva; ev = np.maximum(evh, eva); price = np.where(home, G.ml_h, G.ml_a)
won = np.where(home, G.hw == 1, G.hw == 0); u = np.where(won, np.where(home, dh, da) - 1, -1.0)
trap = np.where(home, G.h_cat == "tanking", G.a_cat == "tanking") | np.where(home, G.a_cat == "middle", G.h_cat == "middle") | (np.where(home, G.h_arr, G.a_arr) > 0)
hdog = home & (G.ml_h > 0); rules = ~hdog & (~G.late | ~trap)
def s_(k):
    k = np.asarray(k); per = [u[k & (G.season == s).values].sum() for s in SEAS]
    return f"{k.sum():4d} bets {u[k].sum():+6.1f}u ({u[k].sum() / max(k.sum(), 1):+.1%}) [" + " ".join(f"{s % 100}:{x:+.1f}" for s, x in zip(SEAS, per)) + f"]  {'ALL POSITIVE' if min(per) > 0 else ''}"
e6 = ev >= 0.06
print("MONEYLINE BETS, EV 6%+ (all games / with the spread rules)")
for lab, k in (("all", True), ("away only", ~home), ("home only", home), ("favorites only", price < 0),
               ("no long shots: price +150 or shorter", price <= 150), ("price -200..+150", (price >= -200) & (price <= 150)),
               ("underdogs +100..+150 only", (price > 0) & (price <= 150)), ("away, price +150 or shorter", ~home & (price <= 150)),
               ("away favorites", ~home & (price < 0)), ("long shots +200 or longer", price >= 200)):
    kk = e6 & np.asarray(k if not isinstance(k, bool) else np.ones(len(G), bool))
    print(f"  {lab:38s} {s_(kk)}  ||  rules: {s_(kk & rules.values)}")
# ---- as a confirmation filter for the live spread bets
OC = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv")); dko = OC[OC.book == "draftkings"][["date", "home", "away", "open_spread"]].rename(columns={"open_spread": "dko_sp"})
G2 = G.merge(dko, on=["date", "home", "away"], how="left")
spe = (G2.m_live + G2.dko_sp).values; cov = (G2.home_pts - G2.away_pts + G2.dko_sp).values
sp_bet = (np.abs(spe) >= 3) & ~((spe > 0) & (G2.dko_sp.values > 0)) & (~G2.late.values | ~trap)
sp_home = spe > 0; r = np.sign(spe) * cov
ml_agree = (home == sp_home) & (ev >= 0.0)
def t_(k):
    k = np.asarray(k) & (r != 0); per = [((r[k & (G2.season == s).values] > 0).sum() * 100 / 110 - (r[k & (G2.season == s).values] < 0).sum()) for s in SEAS]
    w = (r[k] > 0).sum(); return f"{k.sum():4d} bets {w / max(k.sum(), 1):.1%} {sum(per):+6.1f}u [" + " ".join(f"{s % 100}:{x:+.1f}" for s, x in zip(SEAS, per)) + "]"
print("\nSPREAD BETS under the live rules, split by what the moneyline model says")
print(f"  all live-rule spread bets                 {t_(sp_bet)}")
print(f"  moneyline also has value on our side      {t_(sp_bet & (home == sp_home) & (ev >= 0.03))}")
print(f"  moneyline has no value on our side        {t_(sp_bet & ~((home == sp_home) & (ev >= 0.03)))}")
print(f"  we'd be getting points (underdog)         {t_(sp_bet & (np.sign(spe) * G2.dko_sp.values > 0))}")
print(f"  we'd be laying points (favorite)          {t_(sp_bet & (np.sign(spe) * G2.dko_sp.values < 0))}")
aw = e6 & ~home & (price <= 150) & rules.values
print("\nAWAY moneyline, +150 or shorter, EV 6%+, live rules:")
print(f"  all                                       {s_(aw)}")
print(f"  games with NO live spread bet             {s_(aw & ~sp_bet)}")
print(f"  games that also have a live spread bet    {s_(aw & sp_bet)}")
print(f"  Oct-Jan                                   {s_(aw & ~G.late.values)}")
print(f"  Feb-Apr                                   {s_(aw & G.late.values)}")
