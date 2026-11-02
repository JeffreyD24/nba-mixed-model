"""Add schedule/travel effects to the models, each weight fit leaving the test season out:
  NBA totals (live model, luck + form): altitude (DEN/UTA), away back-to-back, away team's time-zone move (east +)
  NBA spreads (live spread model, roster + form): home back-to-back, away team moved west, home team back from a 5+ game trip
  NHL moneyline (shot model, DK opener, EV 6%+): away-only back-to-back, home-only back-to-back, away team moved west
  python analysis/travel_fixes.py WORKDIR NHL_REPO"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    P = P.merge(R[["date", "team", "delta"]].rename(columns={"team": side, "delta": f"{side}_rd"}), on=["date", side], how="left")
TR = pd.read_csv(os.path.join(W, "analysis", "travel_nba_games.csv"))
OC = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv")); dk = OC[OC.book == "draftkings"][["date", "home", "away", "open_spread", "open_total"]].rename(columns={"open_spread": "dk_sp", "open_total": "dk_tot"})
G = P.merge(TR[["date", "home", "away", "altitude", "h_rest", "a_rest", "a_tz_move", "h_trip_len_before"]], on=["date", "home", "away"]).merge(dk, on=["date", "home", "away"])
G["tot_m"] = G.pt_live + 0.20 * G.tot_tp_10.fillna(0)
G["sp_m"] = G.pred_margin + 0.11 * G.sp_mg_10.fillna(0) + 0.57 * (G.home_rd - G.away_rd).fillna(0)
G["f_alt"] = G.altitude.astype(float); G["f_ab2b"] = ((G.a_rest == 1) & (G.h_rest > 1)).astype(float); G["f_hb2b"] = ((G.h_rest == 1) & (G.a_rest > 1)).astype(float)
G["f_east"] = G.a_tz_move.clip(lower=0); G["f_west"] = (-G.a_tz_move).clip(lower=0); G["f_back5"] = (G.h_trip_len_before >= 5).astype(float)
G["early"] = pd.to_datetime(G.date).dt.month.isin([10, 11, 12, 1])
def s_(r): w, l = (r > 0).sum(), (r < 0).sum(); return w + l, w, w * 100 / 110 - l
def run(mk, feats, live_filter=False):
    base = G.tot_m if mk == "tot" else G.sp_m; y = G.pts if mk == "tot" else G.margin
    adj = base.copy(); out = []; tu = tn = tw = 0
    for s in SEAS:
        te = G.season == s
        if feats:
            X = np.column_stack([G.loc[~te, feats].values, np.ones((~te).sum())]); b = np.linalg.lstsq(X, (y - base)[~te].values, rcond=None)[0][:-1]
            adj[te] = base[te] + G.loc[te, feats].values @ b
        e = (adj - G.dk_tot) if mk == "tot" else (adj + G.dk_sp); r = (G.pts - G.dk_tot) if mk == "tot" else (G.margin + G.dk_sp)
        k = te & (e.abs() >= 3)
        if live_filter: k &= G.early & ~((e > 0) & (G.dk_sp > 0))
        n, w, u = s_(np.sign(e[k]) * r[k]); out.append(f"{u:+.1f}"); tu += u; tn += n; tw += w
    return " ".join(out) + f" | {tn} bets {tw / max(tn, 1):.1%} {tu:+.1f}u  MAE {np.abs(adj - y).mean():.3f}"
print("NBA TOTALS at DK openers (2023-24 2024-25 2025-26)")
for lab, f in (("live model", []), ("+ altitude", ["f_alt"]), ("+ away b2b", ["f_ab2b"]), ("+ time-zone move (east/west)", ["f_east", "f_west"]),
               ("+ all three", ["f_alt", "f_ab2b", "f_east", "f_west"])):
    print(f"  {lab:32s}", run("tot", f))
print("NBA SPREADS at DK openers, all bets / live filter (Oct-Jan, no home dogs)")
for lab, f in (("live model", []), ("+ home b2b", ["f_hb2b"]), ("+ away moved west", ["f_west"]), ("+ home back from 5+ trip", ["f_back5"]),
               ("+ all three", ["f_hb2b", "f_west", "f_back5"])):
    print(f"  {lab:32s}", run("sp", f), "||", run("sp", f, True))
# ---------------- NHL moneyline
TN = pd.read_csv(os.path.join(W, "analysis", "travel_nhl_games.csv"))
H = pd.concat([pd.read_csv(os.path.join(N, "_tmp", f"dk_holdout_{s}.csv")) for s in (2022, 2023, 2024, 2025, 2026)])
H = H.merge(TN[["date", "home", "away", "h_rest", "a_rest", "a_tz_move"]], on=["date", "home", "away"]).dropna(subset=["open_home_ml", "open_away_ml", "p_home_win_open"])
dec = lambda o: np.where(o > 0, 1 + o / 100, 1 + 100 / np.abs(o))
H["f_ab2b"] = ((H.a_rest == 1) & (H.h_rest > 1)).astype(float); H["f_hb2b"] = ((H.h_rest == 1) & (H.a_rest > 1)).astype(float)
H["f_west"] = (-H.a_tz_move).clip(lower=0); H["hw"] = (H.home_goals > H.away_goals).astype(float)
print("NHL SHOT MODEL MONEYLINE at DK openers, EV 6%+ (2021-22 .. 2025-26)")
for lab, f in (("live model", []), ("+ away b2b", ["f_ab2b"]), ("+ home b2b", ["f_hb2b"]), ("+ away moved west", ["f_west"]), ("+ all three", ["f_ab2b", "f_hb2b", "f_west"])):
    out = []; tu = tn = 0; p = H.p_home_win_open.copy()
    for s in sorted(H.season.unique()):
        te = H.season == s
        if f:
            X = np.column_stack([H.loc[~te, f].values, np.ones((~te).sum())]); b = np.linalg.lstsq(X, (H.hw - H.p_home_win_open)[~te].values, rcond=None)[0][:-1]
            p[te] = (H.p_home_win_open[te] + H.loc[te, f].values @ b).clip(0.02, 0.98)
        h = H[te]; pp = p[te]; dh, da = dec(h.open_home_ml), dec(h.open_away_ml)
        evh, eva = pp * dh - 1, (1 - pp) * da - 1; home = evh >= eva; ev = np.maximum(evh, eva)
        won = np.where(home, h.home_goals > h.away_goals, h.away_goals > h.home_goals); u = np.where(won, np.where(home, dh, da) - 1, -1.0)
        k = ev >= 0.06; out.append(f"{u[k].sum():+.1f}"); tu += u[k].sum(); tn += k.sum()
    br = ((p - H.hw) ** 2).mean()
    print(f"  {lab:32s}", " ".join(out), f"| {tn} bets {tu:+.1f}u ({tu / tn:+.1%})  Brier {br:.4f}")
