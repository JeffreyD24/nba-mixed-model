"""Market models step 3: movement model for DraftKings NBA totals.
Follows research/market_models/STEP3_MOVEMENT_PREREG.md (written before fitting).
Run from repo root: python research/market_models/movement_model.py
"""
import glob, json, re
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

OUT = "research/market_models/"
BE_CLV = 1.07

# ---------- 0. walk-forward DK opener predictions for 2022-23..2025-26 (step 2 mixed model, lam 20) ----------
src = open(OUT + "opener_models.py").read().split("# ---------- 1. validation")[0]
import sys
NOINJ = "--no-injury" in sys.argv   # honest variant: opener model without the night-before injury report (it was not
SUF = "_noinj" if NOINJ else ""     #   out yet for about half the bets that fired before 8:30 PM the day before)
ns = {}
exec(src, ns)
if NOINJ:
    ns["BASE"] = [c for c in ns["BASE"] if c not in ns["INJ"]]
G0 = ns["G"]
opener_pred = pd.concat([ns["walk"]("mixed", s, "dk", 20) for s in (2023, 2024, 2025, 2026)])
G0["dk_opred"] = opener_pred
games = G0[["date", "home", "away", "season", "tip", "final_total", "dk_open_point", "dk_close_point", "dk_opred"]].copy()
games["dk_oresid"] = games.dk_open_point - games.dk_opred

# ---------- 1. snapshot panel: every book's quote at the same snapshot ----------
NAME = ns.get("NAME")
bsrc = open(OUT + "build_opener_data.py").read()
NAME = eval(re.search(r"NAME = (\{.*?\})", bsrc, re.S).group(1))
fs = sorted(glob.glob("data/odds_history/nba/*.csv.gz"))
d = pd.concat([pd.read_csv(f, usecols=["snapshot_utc", "event_id", "commence_et", "home", "away", "book",
                                      "market", "outcome", "price", "point"]) for f in fs])
d = d[d.market == "totals"]
d["snap"] = pd.to_datetime(d.snapshot_utc).dt.tz_convert("America/New_York").dt.tz_localize(None)
d["tipt"] = pd.to_datetime(d.commence_et)
d["lead_h"] = (d.tipt - d.snap).dt.total_seconds() / 3600
d = d[d.lead_h > 0]
d["date"] = d.tipt.dt.strftime("%Y-%m-%d")
d["home"] = d.home.map(NAME); d["away"] = d.away.map(NAME)
d = d.dropna(subset=["home", "away"])
ov = d[d.outcome == "Over"]; un = d[d.outcome == "Under"]
key = ["date", "home", "away", "snap", "book"]
q = ov[key + ["lead_h", "point", "price"]].merge(un[key + ["price"]], on=key, suffixes=("_o", "_u"), how="left")
q = q.drop_duplicates(key, keep="last")  # merged duplicate event IDs: one quote per book per snapshot


def imp(p):
    p = np.asarray(p, float)
    return np.where(p > 0, 100 / (100 + p), -p / (100 - p))


q["lean"] = imp(q.price_o) - imp(q.price_u)
pt = q.pivot_table(index=["date", "home", "away", "snap"], columns="book", values="point")
ld = q.pivot_table(index=["date", "home", "away", "snap"], columns="book", values="lean")
px = q[q.book == "draftkings"].set_index(["date", "home", "away", "snap"])[["price_o", "price_u", "lead_h"]]
P = px.join(pt.add_prefix("pt_")).join(ld[["draftkings", "pinnacle"]].add_prefix("lean_")).reset_index()
P = P.dropna(subset=["pt_draftkings"])
others = [c for c in pt.columns if c != "draftkings"]
P["cons_gap"] = P[["pt_" + c for c in others]].median(axis=1) - P.pt_draftkings
P["n_books"] = P[["pt_" + c for c in pt.columns]].notna().sum(axis=1)
P["pin_gap"] = P.pt_pinnacle - P.pt_draftkings
P["fd_gap"] = P.pt_fanduel - P.pt_draftkings
P = P.merge(games, on=["date", "home", "away"], how="inner").sort_values(["date", "home", "snap"])
P["dk_now"] = P.pt_draftkings
P["move_so_far"] = P.dk_now - P.dk_open_point
P["opener_view"] = P.dk_opred - P.dk_now
P["log_lead"] = np.log1p(P.lead_h)
P["pin_present"] = P.pin_gap.notna().astype(int)
P["target"] = P.dk_close_point - P.dk_now
# drop the closing snapshot itself and anything under 0.5 h
last = P.groupby(["date", "home"]).snap.transform("max")
P = P[(P.snap < last) & (P.lead_h >= 0.5)].copy()
P["w"] = 1 / P.groupby(["date", "home"]).snap.transform("count")
FEAT = ["log_lead", "move_so_far", "pin_gap", "fd_gap", "cons_gap", "n_books", "lean_draftkings", "lean_pinnacle",
        "dk_oresid", "opener_view", "pin_present"]
print("panel rows", len(P), "games", P.groupby(["date", "home"]).ngroups, "by season",
      P.drop_duplicates(["date", "home"]).season.value_counts().sort_index().to_dict())


# ---------- 2. models ----------
def design(df, med):
    X = df[FEAT].copy()
    for c in ["pin_gap", "fd_gap", "cons_gap", "lean_pinnacle"]:
        X[c] = X[c].fillna(0.0)  # missing book = no gap information (pin_present flags it)
    return X.fillna(med)


def fit(kind, tr):
    med = tr[FEAT].median()
    X = design(tr, med)
    if kind == "ridge":
        mu, sd = X.mean(), X.std() + 1e-9
        m = Ridge(alpha=10.0).fit((X - mu) / sd, tr.target, sample_weight=tr.w)
        return lambda df: m.predict((design(df, med) - mu) / sd), m, (mu, sd)
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                      l2_regularization=1.0, random_state=0).fit(X, tr.target, sample_weight=tr.w)
    return lambda df: m.predict(design(df, med)), m, None


def wmse(df, pred):
    return float(np.average((df.target - pred) ** 2, weights=df.w))


rep = {"validation_2024_25": {}, "test_2025_26": {}}
tr, va = P[P.season.isin([2023, 2024])], P[P.season == 2025]
rep["validation_2024_25"]["no_move"] = round(wmse(va, 0), 3)
for k in ("ridge", "boost"):
    f, _, _ = fit(k, tr); rep["validation_2024_25"][k] = round(wmse(va, f(va)), 3)
choice = min(("ridge", "boost"), key=lambda k: rep["validation_2024_25"][k])
rep["chosen"] = choice
print("validation:", rep["validation_2024_25"], "->", choice)

tr2, te = P[P.season.isin([2023, 2024, 2025])], P[P.season == 2026]
rep["test_2025_26"]["no_move"] = round(wmse(te, 0), 3)
preds = {}
for k in ("ridge", "boost"):
    f, m, sc = fit(k, tr2); preds[k] = f(te); rep["test_2025_26"][k] = round(wmse(te, preds[k]), 3)
    if k == "ridge":
        rep["ridge_weights_std"] = {c: round(float(v), 3) for c, v in zip(FEAT, m.coef_)}
te = te.assign(pred=preds[choice])
rep["test_error_removed_vs_no_move"] = round(1 - rep["test_2025_26"][choice] / rep["test_2025_26"]["no_move"], 3)
va = va.assign(pred=fit(choice, tr)[0](va))
print("test:", rep["test_2025_26"], "error removed:", rep["test_error_removed_vs_no_move"])


# ---------- 3. bet rule ----------
def am_units(p):
    p = -110 if pd.isna(p) else p
    return p / 100 if p > 0 else 100 / -p


def bets(S, thr, min_lead=0.5):
    S = S[S.lead_h >= min_lead].sort_values("snap")
    first = S[S.pred.abs() >= thr].groupby(["date", "home"]).head(1)
    if not len(first): return first, {"n": 0}
    over = first.pred > 0
    line, close, fin = first.dk_now, first.dk_close_point, first.final_total
    clv = np.where(over, close - line, line - close)
    win = np.where(over, fin > line, fin < line); push = fin == line
    pr = np.where(over, first.price_o, first.price_u)
    u = np.where(push, 0.0, np.where(win, [am_units(p) for p in pr], -1.0))
    first = first.assign(side=np.where(over, "Over", "Under"), clv=clv, units=u)
    return first, {"n": int(len(first)), "overs": int(over.sum()), "clv_pts": round(float(clv.mean()), 2),
                   "clv_se": round(float(clv.std() / np.sqrt(len(clv))), 2), "units": round(float(u.sum()), 1),
                   "roi": round(float(u.sum() / len(first)), 3), "win_rate": round(float(win[~push].mean()), 3),
                   "median_lead_h": round(float(first.lead_h.median()), 1)}


rep["bets"] = {}
for season, S in ((2025, va), (2026, te)):
    for thr in (1.0, 1.5, 2.0):
        b, r = bets(S, thr)
        tag = "PREREG" if (season == 2026 and thr == 1.5) else "exploratory"
        rep["bets"][f"{season}_thr{thr}"] = {**r, "status": tag}
        if tag == "PREREG":
            b[["date", "home", "away", "snap", "lead_h", "side", "dk_now", "dk_close_point", "final_total", "pred",
               "clv", "units"]].to_csv(OUT + f"movement_bets_2025_26{SUF}.csv", index=False)
            rep["prereg_by_lead"] = {lab: bets_s for lab, bets_s in (
                (lab, {"n": int(len(x)), "clv": round(float(x.clv.mean()), 2), "units": round(float(x.units.sum()), 1)})
                for lab, x in ((f"{lo}-{hi}h", b[(b.lead_h >= lo) & (b.lead_h < hi)]) for lo, hi in
                               [(0.5, 3), (3, 12), (12, 24), (24, 999)]) if len(x))}
    b, r = bets(S, 1.5, min_lead=3.0)
    rep["bets"][f"{season}_thr1.5_3h_plus"] = {**r, "status": "exploratory"}

# ---------- 4. exploratory: add our outcome model's edge (Model 3 at the opener report) ----------
mc = pd.concat([pd.read_csv(f"research/model_comparison/predictions_{s}.csv") for s in ("2024_25", "2025_26")])
mc = mc[["date", "home", "away", "m3_total_open_report"]]
PM = P.merge(mc, on=["date", "home", "away"], how="left")
PM["our_edge"] = PM.m3_total_open_report - PM.dk_now
FEAT_M = FEAT + ["our_edge"]
a, bb = PM[(PM.season == 2025) & PM.our_edge.notna()], PM[(PM.season == 2026) & PM.our_edge.notna()]
med = a[FEAT_M].median()
def dX(df):
    X = df[FEAT_M].copy()
    for c in ["pin_gap", "fd_gap", "cons_gap", "lean_pinnacle"]: X[c] = X[c].fillna(0.0)
    return X.fillna(med)
mu, sd = dX(a).mean(), dX(a).std() + 1e-9
rm = Ridge(alpha=10.0).fit((dX(a) - mu) / sd, a.target, sample_weight=a.w)
base = Ridge(alpha=10.0).fit((dX(a)[FEAT] - mu[FEAT]) / sd[FEAT], a.target, sample_weight=a.w)
rep["exploratory_our_edge"] = {
    "fit_2024_25_test_2025_26_mse_with": round(wmse(bb, rm.predict((dX(bb) - mu) / sd)), 3),
    "mse_without": round(wmse(bb, base.predict((dX(bb)[FEAT] - mu[FEAT]) / sd[FEAT])), 3),
    "our_edge_weight_std": round(float(rm.coef_[-1]), 3)}
b2, r2 = bets(bb.assign(pred=rm.predict((dX(bb) - mu) / sd)), 1.5)
rep["exploratory_our_edge"]["bets_2026_thr1.5"] = r2

json.dump(rep, open(OUT + f"movement_results{SUF}.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
