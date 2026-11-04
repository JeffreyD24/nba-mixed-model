"""Spreads plan step 1 (NBA): re-grade the live spread rule v2 with only what was known when DraftKings' opener posted.
Pre-registration: research/spreads/STEP1_NBA_PREREG.md (pushed before this ran).
Rows: A lag 0 + 8 PM report (original record), B lag 1 + previous game's report (PRIMARY), C lag 1 + 8 PM, D lag 0 + previous.
  python analysis/spreads_step1_nba.py WORKDIR  -> analysis/spreads_step1_nba_output.txt, analysis/spreads_step1_nba_bets.csv"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
rng = np.random.default_rng(20261104)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

SEAS = (2024, 2025, 2026); FORM_W, ROSTER_W, EDGE, MAX_PRICE = 0.11, 0.57, 3.0, -120
EAST = {"atl", "bos", "bkn", "cha", "chi", "cle", "det", "ind", "mia", "mil", "ny", "orl", "phi", "tor", "wsh"}
key = ["date", "home", "away"]

# ---------------- Model 1 with a results lag (same exec trick as analysis/rule_audit_injury_timing.py)
src = open(os.path.join(W, "nba_mixed_model.py")).read()
assert "past = L_all[L_all.date < d]" in src
ns = {"__name__": "nm_lag"}
exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]"), "nm_lag", "exec"), ns)

T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][key + ["open_spread", "open_total"]].drop_duplicates(key)
pin = O[O.book == "pinnacle"][key + ["open_spread"]].drop_duplicates(key).rename(columns={"open_spread": "pin_open"})
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=key, how="left")

# previous game's final report in place of the 8 PM report (as in the totals timing audit)
INJ = ["miss_off", "miss_def", "n_out"]
lg_ = pd.concat([T[["date", "home"] + [f"home_{c}" for c in INJ]].rename(columns=lambda c: c.replace("home_", "") if c != "home" else "team"),
                 T[["date", "away"] + [f"away_{c}" for c in INJ]].rename(columns=lambda c: c.replace("away_", "") if c != "away" else "team")]).sort_values(["team", "date"])
for c in INJ: lg_[f"prev_{c}"] = lg_.groupby("team")[c].shift(1)
prev = lg_.set_index(["date", "team"])[[f"prev_{c}" for c in INJ]]
TS = T.copy()
for side in ("home", "away"):
    p = prev.reindex(pd.MultiIndex.from_arrays([TS.date, TS[side]])).values
    for j, c in enumerate(INJ):
        TS[f"{side}_{c}_open"] = np.where(pd.isna(p[:, j]), TS[f"{side}_{c}_open"], p[:, j])

def model1(TT, lag):
    ns["LAG_DAYS"] = lag; rows = []
    for test in SEAS:
        with contextlib.redirect_stdout(io.StringIO()):
            _, P = ns["run"](TT[TT.season.isin(list(range(2022, test)) + [test])], list(range(2022, test)), test, today_suffix="_open")
        P = P[key + ["pred_margin"]].copy(); P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d"); rows.append(P.assign(season=test))
    return pd.concat(rows)

# ---------------- form, roster, standings, each available at lag 0 (through d-1) and lag 1 (through d-2)
rows = []
for r in T.itertuples():
    rows += [dict(season=r.season, date=r.date, team=r.home, mg=r.home_pts - r.away_pts, w=int(r.home_pts > r.away_pts)),
             dict(season=r.season, date=r.date, team=r.away, mg=r.away_pts - r.home_pts, w=int(r.away_pts > r.home_pts))]
L = pd.DataFrame(rows).sort_values(["season", "team", "date"]); g = L.groupby(["season", "team"])
L["n"] = g.cumcount()
L["f10"] = g.mg.transform(lambda v: v.shift().rolling(10, min_periods=6).mean()) - g.mg.transform(lambda v: v.shift().expanding().mean())
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))[["date", "team", "delta"]]
L = L.merge(R, on=["date", "team"], how="left")
L["d"] = pd.to_datetime(L.date)
L["prev_d"] = L.groupby(["season", "team"]).d.shift(); L["b2b"] = (L.d - L.prev_d).dt.days == 1
for c in ("n", "f10", "delta"):
    L[f"{c}_lag1"] = np.where(L.b2b, L.groupby(["season", "team"])[c].shift(), L[c])   # played last night: value from before that game
# standings categories (late_season.py definitions) with cutoff date < d (lag 0) or < d-1 (lag 1)
def cats(lag):
    cat = {}
    for s, S in L.groupby("season"):
        for d in sorted(S.d.unique()):
            past = S[S.d < d - pd.Timedelta(days=lag)].groupby("team").w.agg(["sum", "size"])
            if len(past) < 30: continue
            past["l"] = past["size"] - past["sum"]; past["wp"] = past["sum"] / past["size"]
            for conf in (True, False):
                c = past[past.index.isin(EAST) == conf].sort_values("wp", ascending=False); c["rank"] = np.arange(1, len(c) + 1)
                w10, l10 = c.iloc[9]["sum"], c.iloc[9]["l"]; c["gb10"] = ((w10 - l10) - (c["sum"] - c.l)) / 2
                for t, x in c.iterrows():
                    cat[(pd.Timestamp(d).strftime("%Y-%m-%d"), t)] = ("top" if x["rank"] <= 4 else "middle" if x["rank"] <= 10 else
                                                                     "bubble" if (x["rank"] <= 12 and x.gb10 <= 4) else "tanking")
    return cat
CAT = {0: cats(0), 1: cats(1)}
ARR = pd.read_csv(os.path.join(W, "analysis", "late_season_games.csv"))[key + ["h_arr", "a_arr"]].drop_duplicates(key)
LI = L.set_index(["date", "team"])

# ---------------- DraftKings opener (first snapshot with spread and total, as in validate_dk_2024_26.py) and close
S = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "t", "book", "sp", "sp_px_h", "sp_px_a", "tot", "tip", "date"])
S = S[(S.book == "draftkings") & S.sp.notna()].copy(); S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True)
S = S[S.t <= S.tip].sort_values("t")
op = S[S.tot.notna()].groupby(key).head(1).set_index(key)[["sp", "sp_px_h", "sp_px_a", "t"]].rename(columns={"sp": "open_sp", "t": "open_t"})
cl = S.groupby(key).tail(1).set_index(key)[["sp"]].rename(columns={"sp": "close_sp"})
LINES = op.join(cl).reset_index()
LINES["open_et"] = LINES.open_t.dt.tz_convert("America/New_York").dt.tz_localize(None)

def build(lag, rep):
    P = model1(T if rep == "8pm" else TS, lag).merge(T[key + ["home_pts", "away_pts"]], on=key).merge(LINES, on=key).merge(pin, on=key, how="left").merge(ARR, on=key, how="left")
    sfx = "_lag1" if lag == 1 else ""
    for side, k in (("home", "h"), ("away", "a")):
        v = LI.reindex(pd.MultiIndex.from_arrays([P.date, P[side]]))
        P[f"{k}_n"] = v[f"n{sfx}"].values; P[f"{k}_f10"] = v[f"f10{sfx}"].values; P[f"{k}_rd"] = v[f"delta{sfx}"].values
        P[f"{k}_cat"] = [CAT[lag].get((d, t)) for d, t in zip(P.date, P[side])]
    P = P[(P.h_n >= 10) & (P.a_n >= 10)].copy()
    P["sp_model"] = P.pred_margin + FORM_W * (P.h_f10 - P.a_f10).fillna(0) + ROSTER_W * (P.h_rd - P.a_rd).fillna(0)
    P["margin"] = P.home_pts - P.away_pts
    P["e"] = P.sp_model + P.open_sp; P["bet_home"] = P.e > 0
    P["res"] = np.where(P.bet_home, P.margin + P.open_sp, -(P.margin + P.open_sp))           # >0 win, <0 loss, 0 push
    P["clv"] = np.where(P.bet_home, P.open_sp - P.close_sp, P.close_sp - P.open_sp)           # pts the close moved toward the bet
    P["px"] = np.where(P.bet_home, P.sp_px_h, P.sp_px_a)
    P["late"] = pd.to_datetime(P.date).dt.month.isin([2, 3, 4])
    P["home_dog"] = P.bet_home & (P.open_sp > 0)
    us_cat = np.where(P.bet_home, P.h_cat, P.a_cat); them_cat = np.where(P.bet_home, P.a_cat, P.h_cat)
    us_arr = np.where(P.bet_home, P.h_arr, P.a_arr)
    P["late_ok"] = pd.notna(us_cat) & pd.notna(them_cat) & (us_cat != "tanking") & (them_cat != "middle") & (pd.Series(us_arr).fillna(0).values == 0)
    P["pin_against"] = np.where(P.bet_home, (P.open_sp - P.pin_open) < 0, (P.open_sp - P.pin_open) > 0) & P.pin_open.notna()
    P["edge3"] = P.e.abs() >= EDGE
    P["price_ok"] = ~(P.px < MAX_PRICE)
    P["v2"] = P.edge3 & P.price_ok & ~P.home_dog & (~P.late | P.late_ok)
    return P

V = {"A": build(0, "8pm"), "B": build(1, "prev"), "C": build(1, "8pm"), "D": build(0, "prev")}

# ---------------- break-even CLV: cover rate at the opener vs (close - opener) movement, all games with both lines
G = V["B"].dropna(subset=["open_sp", "close_sp"])
hc = G[(G.margin + G.open_sp) != 0]; y = ((hc.margin + hc.open_sp) > 0).astype(float); x = (hc.open_sp - hc.close_sp)   # + = close moved toward home
slope = float(np.polyfit(x, y, 1)[0]); BE = 0.024 / slope

def summ(P, m):
    b = P[m]; w, l = int((b.res > 0).sum()), int((b.res < 0).sum()); n = w + l
    u = w * 100 / 110 - l
    r = np.where(b.res > 0, 100 / 110, np.where(b.res < 0, -1.0, 0.0))
    bs = [rng.choice(r, len(r)).mean() * 100 for _ in range(2000)] if len(r) else [np.nan]
    return dict(n=n, wp=w / max(n, 1), u=u, u100=u / max(n, 1) * 100, lo=np.percentile(bs, 5), hi=np.percentile(bs, 95),
                clv=b.clv.mean(), beat=(b.clv > 0).mean(), lose=(b.clv < 0).mean())
def line(lab, P, m):
    s = summ(P, m); per = " ".join(f"{yr}:{summ(P, m & (P.season == yr))['u']:+.1f}" for yr in SEAS)
    say(f"  {lab:<34} {s['n']:5d} {s['wp']:.1%} {s['u']:+7.1f}u  {s['u100']:+5.1f}/100 [{s['lo']:+5.1f},{s['hi']:+5.1f}]  CLV {s['clv']:+.2f} pts"
        f" (beat close {s['beat']:.0%}, worse {s['lose']:.0%})  | {per}")

say("NBA spreads v2 at DraftKings openers 2023-24..2025-26 with opener-time information (prereg research/spreads/STEP1_NBA_PREREG.md)")
say(f"games graded (B): {len(V['B'])}; opener posted before 8 PM night before: {(V['B'].open_et < pd.to_datetime(V['B'].date) - pd.Timedelta(hours=4)).mean():.0%}")
say(f"break-even CLV: cover rate rises {slope * 100:.2f} win-% pts per point the close moves toward the bet -> break-even = {BE:+.2f} pts")
say("columns: bets, win %, units at -110, units per 100 [90% bootstrap], CLV vs DK close, per-season units")
NAMES = {"A": "lag 0 + 8 PM report (original record)", "B": "lag 1 + previous report (PRIMARY)", "C": "lag 1 + 8 PM report", "D": "lag 0 + previous report"}
for k, P in V.items():
    say(f"\n{k}: {NAMES[k]}")
    line("v2 full rule", P, P.v2)
    line("  Oct-Jan part", P, P.v2 & ~P.late)
    line("  Feb-Apr part (outside traps)", P, P.v2 & P.late)
    line("home underdogs (excluded)", P, P.edge3 & P.home_dog)
    line("all 3+ edges, no filters", P, P.edge3)
    if k == "B":
        line("v2 + Pinnacle cancel (secondary)", P, P.v2 & ~P.pin_against)
        line("  bets Pinnacle would cancel", P, P.v2 & P.pin_against)
B = V["B"]
say(f"\nAccuracy (B games, both teams 10+): model margin MAE {(B.sp_model - B.margin).abs().mean():.2f} vs DK opener MAE {(-B.open_sp - B.margin).abs().mean():.2f}"
    f" vs DK close MAE {(-B.close_sp - B.margin).abs().mean():.2f}")
for k in ("A", "B"):
    P = V[k]; say(f"  {k}: model MAE {(P.sp_model - P.margin).abs().mean():.3f}")
# how often the honest inputs changed the bet
AB = V["A"][key + ["e", "v2"]].merge(V["B"][key + ["e", "v2"]], on=key, suffixes=("_A", "_B"))
say(f"\nA vs B: v2 bets A {int(AB.v2_A.sum())}, B {int(AB.v2_B.sum())}, both {int((AB.v2_A & AB.v2_B).sum())}; "
    f"same side when both 3+: {(np.sign(AB.e_A) == np.sign(AB.e_B))[AB.v2_A & AB.v2_B].mean():.0%}; mean |model change| {(AB.e_A - AB.e_B).abs().mean():.2f} pts")
open(os.path.join(W, "analysis", "spreads_step1_nba_output.txt"), "w").write("\n".join(out) + "\n")
pd.concat([P.assign(variant=k) for k, P in V.items()])[["variant", "season", "date", "home", "away", "open_et", "open_sp", "close_sp", "pin_open", "pred_margin", "sp_model", "e",
    "bet_home", "res", "clv", "late", "home_dog", "late_ok", "pin_against", "edge3", "price_ok", "v2"]].to_csv(os.path.join(W, "analysis", "spreads_step1_nba_bets.csv"), index=False)
