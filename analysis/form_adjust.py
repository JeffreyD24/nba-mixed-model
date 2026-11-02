"""Recent-form adjustment for NBA Model 1, tested honestly: the weight is fit on OTHER seasons' predictions (residual = result
minus model, regressed on recent form), then applied to the test season. Seasons: 2023-24 (DraftKings openers), 2024-25 and
2025-26 (training openers). Forms (team's last k games minus its season-to-date level; home minus away for spreads, sum for totals):
  pts   = scoring margin (spreads) / total points (totals)
  qual  = shot-quality margin (expected FG points for minus against) / expected FG points both ways (no shooting luck)
Totals start from the live luck-corrected model.
  python analysis/form_adjust.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
T = pd.read_csv(os.path.join(W, "data", "training_games.csv")).sort_values("date").reset_index(drop=True)
TG = pd.read_csv(os.path.join(W, "analysis", "shot_quality_team_games.csv.gz"))
TG["date"] = pd.to_datetime(TG.date).dt.strftime("%Y-%m-%d")
# per team-game: points margin/total from results, shot-quality margin/total from shots
rows = []
for r in T.itertuples():
    rows += [dict(season=r.season, date=r.date, team=r.home, opp=r.away, side="h", mg=r.home_pts - r.away_pts, tp=r.home_pts + r.away_pts),
             dict(season=r.season, date=r.date, team=r.away, opp=r.home, side="a", mg=r.away_pts - r.home_pts, tp=r.home_pts + r.away_pts)]
L = pd.DataFrame(rows)
q = TG[["date", "team", "xpts", "opp_xpts", "luck", "opp_luck"]].copy()
q["date"] = pd.to_datetime(q.date).dt.strftime("%Y-%m-%d")
L = L.merge(q, on=["date", "team"], how="left")
L["qm"] = L.xpts - L.opp_xpts; L["qt"] = L.xpts + L.opp_xpts
L = L.sort_values(["season", "team", "date"]); g = L.groupby(["season", "team"])
L["n"] = g.cumcount()
for c in ("mg", "tp", "qm", "qt"):
    L[f"{c}_S"] = g[c].transform(lambda v: v.shift().expanding().mean())
    for k in (5, 10, 15):
        L[f"{c}_{k}"] = g[c].transform(lambda v: v.shift().rolling(k, min_periods=k // 2 + 1).mean())
        L[f"f_{c}_{k}"] = L[f"{c}_{k}"] - L[f"{c}_S"]
FORMS = {f"{c}_{k}": f"f_{c}_{k}" for c in ("mg", "tp", "qm", "qt") for k in (5, 10, 15)}
H = L[L.side == "h"].set_index(["date", "team"]); A = L[L.side == "a"].set_index(["date", "team"])

P1 = pd.read_csv(os.path.join(W, "_tmp", "model1_open_preds.csv")); P2 = pd.read_csv(os.path.join(W, "_tmp", "test_2024_games.csv"))
P2 = P2.assign(open_spread=P2.sp_open, open_total=P2.ov_open)
cols = ["date", "home", "away", "season", "pred_margin", "pred_total", "open_spread", "open_total", "home_pts", "away_pts"]
P = pd.concat([P1[cols], P2[cols]]); P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
# live luck correction for totals (league-relative, 0.5, both teams 5+ games)
Q = pd.read_csv(os.path.join(W, "analysis", "shot_quality_games.csv"))[["date", "home", "away", "h_pre_luck", "h_pre_opp_luck", "a_pre_luck", "a_pre_opp_luck", "L_total"]]
P = P.merge(Q, on=["date", "home", "away"], how="left")
lg = P.groupby("date")[["h_pre_luck", "a_pre_luck", "h_pre_opp_luck", "a_pre_opp_luck"]].transform("mean").mean(axis=1)
P["h_n"] = [H["n"].get((d, t), np.nan) for d, t in zip(P.date, P.home)]; P["a_n"] = [A["n"].get((d, t), np.nan) for d, t in zip(P.date, P.away)]
P["pt_live"] = P.pred_total + np.where((P.h_n >= 5) & (P.a_n >= 5), (-0.5 * (P.L_total - 4 * lg)).fillna(0), 0)
for nm, col in FORMS.items():
    hv = np.array([H[col].get((d, t), np.nan) for d, t in zip(P.date, P.home)]); av = np.array([A[col].get((d, t), np.nan) for d, t in zip(P.date, P.away)])
    P[f"sp_{nm}"] = hv - av; P[f"tot_{nm}"] = hv + av
P["margin"] = P.home_pts - P.away_pts; P["pts"] = P.home_pts + P.away_pts
P = P[(P.h_n >= 10) & (P.a_n >= 10)].dropna(subset=["open_spread", "open_total"]).copy()
SEAS = (2024, 2025, 2026)


def grade(e, res):
    m = e.abs() >= 3; r = np.sign(e[m]) * res[m]; w, l = (r > 0).sum(), (r < 0).sum()
    return w + l, w / max(w + l, 1), w * 100 / 110 - l


rows = []
for mk in ("sp", "tot"):
    base = P.pred_margin if mk == "sp" else P.pt_live
    y = P.margin if mk == "sp" else P.pts
    res = (P.margin + P.open_spread) if mk == "sp" else (P.pts - P.open_total)
    line = -P.open_spread if mk == "sp" else P.open_total
    for nm in ["none"] + [n for n in FORMS if (n.startswith(("mg", "qm")) if mk == "sp" else n.startswith(("tp", "qt")))]:
        out = dict(market=mk, form=nm)
        tot_u = 0; tot_b = 0
        for s in SEAS:
            te = P.season == s
            if nm == "none":
                adj = base[te]; c = 0.0
            else:
                f = P[f"{mk}_{nm}"].fillna(0)
                fit = P.season.isin([x for x in SEAS if x != s])    # weight from the other two seasons only
                rr = (y - base)[fit]; ff = f[fit]
                c = float((ff * (rr - rr.mean())).sum() / ((ff - ff.mean()) ** 2).sum())
                adj = base[te] + c * f[te]
            e = adj - line[te]
            n, wp, u = grade(e, res[te])
            out[f"{s}_c"] = round(c, 3); out[f"{s}_bets"] = n; out[f"{s}_win"] = round(wp, 3); out[f"{s}_units"] = round(u, 1)
            out[f"{s}_mae"] = round(float(np.abs(adj - y[te]).mean()), 3)
            tot_u += u; tot_b += n
        out["bets"] = tot_b; out["units"] = round(tot_u, 1)
        rows.append(out)
R = pd.DataFrame(rows); R.to_csv(os.path.join(W, "analysis", "form_adjust_results.csv"), index=False)
pd.set_option("display.width", 250)
for mk in ("sp", "tot"):
    print(R[R.market == mk][["form"] + [f"{s}_{x}" for s in SEAS for x in ("c", "units")] + ["bets", "units"] + [f"{s}_mae" for s in SEAS]].to_string(index=False))
print("\nWeights fit on all three seasons (for live use):")
for mk, nm in (("sp", "mg_10"), ("tot", "tp_10")):
    base = P.pred_margin if mk == "sp" else P.pt_live; y = P.margin if mk == "sp" else P.pts
    f = P[f"{mk}_{nm}"].fillna(0); rr = y - base
    c = float((f * (rr - rr.mean())).sum() / ((f - f.mean()) ** 2).sum())
    se = float(np.std(rr - c * f) / np.sqrt(((f - f.mean()) ** 2).sum()))
    print(f"  {mk} {nm}: c = {c:.3f} (se {se:.3f}); form SD {f.std():.2f} pts -> typical adjustment {c * f.std():.2f} pts")
    for s in SEAS:
        k = P.season == s; m = (base + c * f - (-P.open_spread if mk == "sp" else P.open_total))[k]
        print(f"     {s}: same-weight check {grade(m, ((P.margin + P.open_spread) if mk == 'sp' else (P.pts - P.open_total))[k])}")
