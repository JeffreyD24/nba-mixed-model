"""NBA moneyline from Model 1: win chance = logistic(a + b x model margin), a and b fit leaving the test season out; bet the
side with the larger expected value at DraftKings' OPENING moneyline (The Odds API history), 2023-24..2025-26.
Margins: base Model 1, and the live spread model (roster + last-10 form). Also the spread rules (home dogs, Feb-Apr traps).
  python analysis/nba_moneyline.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    P = P.merge(R[["date", "team", "delta"]].rename(columns={"team": side, "delta": f"{side}_rd"}), on=["date", side], how="left")
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), parse_dates=["t"])
def first(book, cols):
    d = O[O.book == book].dropna(subset=cols).sort_values("t").groupby(["date", "home", "away"])
    return d.head(1)[["date", "home", "away"] + cols], d.tail(1)[["date", "home", "away"] + cols]
dk_o, dk_c = first("draftkings", ["ml_h", "ml_a"]); pn_o, _ = first("pinnacle", ["ml_h", "ml_a"])
G = P.merge(dk_o, on=["date", "home", "away"]).merge(dk_c.rename(columns={"ml_h": "c_h", "ml_a": "c_a"}), on=["date", "home", "away"], how="left") \
     .merge(pn_o.rename(columns={"ml_h": "p_h", "ml_a": "p_a"}), on=["date", "home", "away"], how="left")
LS = pd.read_csv(os.path.join(W, "analysis", "late_season_games.csv"))[["date", "home", "away", "h_cat", "a_cat", "h_arr", "a_arr"]]
G = G.merge(LS, on=["date", "home", "away"], how="left")
G["m_live"] = G.pred_margin + 0.11 * G.sp_mg_10.fillna(0) + 0.57 * (G.home_rd - G.away_rd).fillna(0)
G["hw"] = (G.home_pts > G.away_pts).astype(float); G["late"] = pd.to_datetime(G.date).dt.month.isin([2, 3, 4])
dec = lambda o: np.where(o > 0, 1 + o / 100, 1 + 100 / np.abs(o))
def nv(a, b): ia, ib = 1 / dec(a), 1 / dec(b); return ia / (ia + ib)
from sklearn.linear_model import LogisticRegression
print("games:", G.groupby("season").size().to_dict())
def run(col, bar=0.06, label="", mask_fn=None):
    out = []; tn = tu = 0; br = []
    G["p"] = np.nan
    for s in SEAS:
        te = G.season == s
        m = LogisticRegression(C=100).fit(G.loc[~te, [col]], G.loc[~te, "hw"]); G.loc[te, "p"] = m.predict_proba(G.loc[te, [col]])[:, 1]
    dh, da = dec(G.ml_h), dec(G.ml_a); evh, eva = G.p * dh - 1, (1 - G.p) * da - 1
    home = evh >= eva; ev = np.maximum(evh, eva); won = np.where(home, G.hw == 1, G.hw == 0); u = np.where(won, np.where(home, dh, da) - 1, -1.0)
    k = ev >= bar
    if mask_fn is not None: k &= mask_fn(G, home)
    for s in SEAS:
        kk = k & (G.season == s); out.append(u[kk].sum())
    tn, tu = k.sum(), u[k].sum()
    brier = ((G.p - G.hw) ** 2).mean(); mkt = ((nv(G.ml_h, G.ml_a) - G.hw) ** 2).mean()
    print(f"  {label:52s} " + " ".join(f"{x:+6.1f}" for x in out) + f" | {tn:4d} bets {tu:+6.1f}u ({tu / max(tn, 1):+.1%})  Brier model {brier:.4f} vs DK open {mkt:.4f}")
    return home, ev, u, k
print("units by season (2023-24 2024-25 2025-26):")
run("pred_margin", label="base Model 1, EV 6%+")
for bar in (0.04, 0.06, 0.09, 0.12): h, ev, u, k = run("m_live", bar, f"live spread model (roster + form), EV {bar:.0%}+")
h, ev, u, k = run("m_live", 0.06, "live model, EV 6%+")
B = pd.DataFrame(dict(season=G.season, home=h, ev=ev, u=u, k=k, late=G.late, price=np.where(h, G.ml_h, G.ml_a),
                      our_cat=np.where(h, G.h_cat, G.a_cat), opp_cat=np.where(h, G.a_cat, G.h_cat), our_arr=np.where(h, G.h_arr, G.a_arr),
                      ready=(G[["h_n", "a_n"]].min(axis=1) >= 10) if "h_n" in G else True,
                      pin=np.where(h, nv(G.p_h, G.p_a) - nv(G.ml_h, G.ml_a), nv(G.ml_h, G.ml_a) - nv(G.p_h, G.p_a)),
                      clv=np.where(h, nv(G.c_h, G.c_a) - nv(G.ml_h, G.ml_a), nv(G.ml_h, G.ml_a) - nv(G.c_h, G.c_a))))
B = B[B.k]
def s_(g): return f"{len(g):4d} bets {g.u.sum():+6.1f}u ({g.u.sum() / max(len(g), 1):+.1%}) [" + " ".join(f"{s % 100}:{g[g.season == s].u.sum():+.1f}" for s in SEAS) + "]"
print("\nlive model, EV 6%+, by group:")
for lab, k in (("favorites", B.price < 0), ("underdogs +100..+199", (B.price > 0) & (B.price < 200)), ("underdogs +200 and longer", B.price >= 200),
               ("home", B.home), ("away", ~B.home), ("home underdogs", B.home & (B.price > 0)),
               ("Oct-Jan", ~B.late), ("Feb-Apr", B.late), ("Feb-Apr outside traps", B.late & ~((B.our_cat == "tanking") | (B.opp_cat == "middle") | (B.our_arr > 0))),
               ("Feb-Apr traps", B.late & ((B.our_cat == "tanking") | (B.opp_cat == "middle") | (B.our_arr > 0))),
               ("Pinnacle first price agrees/same", B.pin >= -0.005), ("Pinnacle first price against", B.pin < -0.005),
               ("price moved our way by the close", B.clv > 0), ("price moved against by the close", B.clv < 0)):
    print(f"  {lab:36s} {s_(B[k])}")
print("\nlive model, EV 6%+, with the spread rules:")
hd = B.home & (B.price > 0); trap = (B.our_cat == "tanking") | (B.opp_cat == "middle") | (B.our_arr > 0)
rule = ~hd & (~B.late | ~trap)
for lab, k in (("spread rules (no home dogs; Feb-Apr outside traps)", rule), ("  ... favorites only", rule & (B.price < 0)),
               ("  ... underdogs only", rule & (B.price > 0)), ("  ... + Pinnacle agrees/same (if waiting were free)", rule & (B.pin >= -0.005)),
               ("  ... Oct-Jan only", rule & ~B.late)):
    print(f"  {lab:52s} {s_(B[k])}")
# ---- blend: win chance = w x model + (1 - w) x DraftKings' no-vig opener, w fit leaving the season out (log-loss)
print("\nBLEND of model and DraftKings' opening price (weight on the model fit leaving the season out):")
G["mkt"] = nv(G.ml_h, G.ml_a)
from scipy.optimize import minimize_scalar
pm = {}
for s in SEAS:
    tr = G[G.season != s]; G_ = G[G.season == s]
    m = LogisticRegression(C=100).fit(tr[["m_live"]], tr.hw)
    ptr = m.predict_proba(tr[["m_live"]])[:, 1]
    ll = lambda w: -np.mean(tr.hw * np.log(np.clip(w * ptr + (1 - w) * tr.mkt, 1e-6, 1)) + (1 - tr.hw) * np.log(np.clip(1 - w * ptr - (1 - w) * tr.mkt, 1e-6, 1)))
    w = minimize_scalar(ll, bounds=(0, 1), method="bounded").x
    G.loc[G.season == s, "pb"] = w * m.predict_proba(G_[["m_live"]])[:, 1] + (1 - w) * G_.mkt; pm[s] = round(w, 2)
print("  weight on the model by test season:", pm, "| Brier blend", round(((G.pb - G.hw) ** 2).mean(), 4), "vs DK open", round(((G.mkt - G.hw) ** 2).mean(), 4))
dh, da = dec(G.ml_h), dec(G.ml_a); evh, eva = G.pb * dh - 1, (1 - G.pb) * da - 1; home = evh >= eva; ev = np.maximum(evh, eva)
won = np.where(home, G.hw == 1, G.hw == 0); u = np.where(won, np.where(home, dh, da) - 1, -1.0)
hdog = home & (G.ml_h > 0)
for bar in (0.01, 0.02, 0.03, 0.05):
    k = ev >= bar
    print(f"  blend EV {bar:.0%}+: {k.sum():4d} bets {u[k].sum():+6.1f}u [" + " ".join(f"{s % 100}:{u[k & (G.season == s).values].sum():+.1f}" for s in SEAS) + "]"
          + f" | no home dogs: {(k & ~hdog).sum()} bets {u[k & ~hdog].sum():+.1f}u [" + " ".join(f"{s % 100}:{u[k & ~hdog & (G.season == s).values].sum():+.1f}" for s in SEAS) + "]")
