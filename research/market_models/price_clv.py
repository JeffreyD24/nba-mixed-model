"""Price-terms CLV (pre-registration: PRICE_CLV_PREREG.md). Run after price_clv_build.py.
python research/market_models/price_clv.py -> price_clv_results.json, prints tables"""
import glob, json, numpy as np, pandas as pd
R = "research/market_models/"
L = pd.read_csv(R + "price_lines.csv.gz")
O = pd.read_csv(R + "opener_data.csv.gz", usecols=["event_id", "date", "home", "away", "home_pts", "away_pts"])
L = L.drop(columns=["home", "away"]).merge(O, on="event_id", how="inner")
L["date"] = pd.to_datetime(L.date)
L["season"] = np.where(L.date.dt.month >= 8, L.date.dt.year + 1, L.date.dt.year)      # END year
L["res"] = np.where(L.market == "totals", L.home_pts + L.away_pts, L.home_pts - L.away_pts)
# outcome margin of side "a" (over / home) at a line: totals res - point; spreads res + home point
def margin_a(df, pt): return np.where(df.market == "totals", df.res - df[pt], df.res + df[pt])
out = {}

# ---- step 2: points per unit of probability, k, from 2021-24 only, at DK close (empirical density near the line)
k = {}
for m in ["totals", "spreads"]:
    t = L[(L.book == "draftkings") & (L.market == m) & (L.season <= 2024)]
    mg = margin_a(t, "point_a_close")
    dens = np.mean(np.abs(mg) <= 4.0) / 8.0                      # 8 points wide window around the line
    k[m] = 1 / dens
    out[f"k_{m}"] = {"k_points_per_prob": round(k[m], 1), "win_pct_per_point": round(100 * dens, 2), "n": int(len(t))}
L["k"] = L.market.map(k)

# ---- T1: does the closing price carry information beyond the point? Brier of side-a result at the close point.
t1 = []
for (b, m, s), t in L[L.season >= 2025].groupby(["book", "market", "season"]):
    mg = margin_a(t, "point_a_close"); y = (mg > 0).astype(float); ok = mg != 0
    y, p = y[ok], t.p_a_close.values[ok]
    t1.append({"book": b, "market": m, "season": int(s), "n": int(ok.sum()),
               "brier_point_only": round(float(np.mean((y - 0.5) ** 2)), 5),
               "brier_with_price": round(float(np.mean((y - p) ** 2)), 5),
               "gain_x1000": round(1000 * float(np.mean((y - 0.5) ** 2) - np.mean((y - p) ** 2)), 3),
               "mean_abs_skew_pts": round(float(np.mean(np.abs(t.p_a_close - 0.5) * t.k)), 3)})
out["T1"] = t1

# ---- T2: DK first-seen skew vs DK move in effective points (2025-26, descriptive)
t2 = []
for m in ["totals", "spreads"]:
    t = L[(L.book == "draftkings") & (L.market == m) & (L.season == 2026)]
    skew = (t.p_a_open - 0.5) * t.k
    eff_close = t.point_a_close + (t.p_a_close - 0.5) * t.k * np.where(m == "totals", 1, -1)
    # totals: over favoured -> book expects higher total. spreads: home favoured at same point -> home spread should be more negative
    move = eff_close - t.point_a_open
    sk = skew * np.where(m == "totals", 1, -1)
    b = np.polyfit(sk, move, 1)[0]
    t2.append({"market": m, "n": int(len(t)), "slope_move_on_skew": round(float(b), 3),
               "sd_skew_pts": round(float(sk.std()), 3), "corr": round(float(np.corrcoef(sk, move)[0, 1]), 3)})
out["T2"] = t2

# ---- price CLV helper: EV of a bet on side s ("a"/"b") at (line, american price) vs a book's no-vig close
def dec(a): a = np.asarray(a, float); return np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))
def price_ev(row_close, side, line, price, market, k_):
    """line = the bet side's own line in side-a terms (total point, or home spread point)"""
    pa, lc = row_close["p_a_close"], row_close["point_a_close"]
    if market == "totals":
        d = (lc - line) if side == "a" else (line - lc)              # over: lower bet line is better
    else:
        d = (line - lc) if side == "a" else (lc - line)              # home: higher home point is better
    p = (pa if side == "a" else 1 - pa) + d / k_
    return p * dec(price) - 1, d

# ---- T3 (i): step 3 movement bets 2025-26 at DK, priced from the snapshot they fired on
M = pd.read_csv(R + "movement_bets_2025_26.csv"); M["date"] = pd.to_datetime(M.date)
ids = O.assign(date=pd.to_datetime(O.date))[["event_id", "date", "home", "away"]]
M = M.merge(ids, on=["date", "home", "away"], how="left")
fs = sorted(glob.glob("data/odds_history/nba/2025-*.csv.gz") + glob.glob("data/odds_history/nba/2026-0*.csv.gz"))
S = pd.concat([pd.read_csv(f, usecols=["snapshot_utc", "event_id", "book", "market", "outcome", "price", "point"]) for f in fs])
S = S[(S.book == "draftkings") & (S.market == "totals")]
S["snap"] = pd.to_datetime(S.snapshot_utc).dt.tz_convert("America/New_York").dt.tz_localize(None)
S = S.pivot_table(index=["event_id", "snap"], columns="outcome", values=["price", "point"], aggfunc="first")
S.columns = [f"{a}_{b}" for a, b in S.columns]; S = S.reset_index()
M["snap"] = pd.to_datetime(M.snap)
M = pd.merge_asof(M.sort_values("snap"), S.sort_values("snap"), on="snap", by="event_id", direction="nearest",
                  tolerance=pd.Timedelta("2min"))
rows = []
CL = L.set_index(["event_id", "book", "market"])
for _, r in M.iterrows():
    side = "a" if r.side == "Over" else "b"
    px = r.price_Over if side == "a" else r.price_Under
    rec = {"date": r.date, "home": r.home, "side": r.side, "line": r.dk_now, "price": px, "point_clv": r.clv, "units": r.units}
    for bk in ["draftkings", "pinnacle"]:
        key = (r.event_id, bk, "totals")
        if pd.isna(px) or key not in CL.index: rec[f"ev_{bk}"] = np.nan; continue
        c = CL.loc[key]; ev, _ = price_ev(c, side, r.dk_now, px, "totals", k["totals"]); rec[f"ev_{bk}"] = float(ev)
        # same EV if the close were treated as -110/-110 (point-only view)
        if bk == "draftkings":
            c0 = c.copy(); c0["p_a_close"] = 0.5
            rec["ev_point_only"] = float(price_ev(c0, side, r.dk_now, -110, "totals", k["totals"])[0])
    rows.append(rec)
T3 = pd.DataFrame(rows); T3.to_csv(R + "price_clv_movement_bets.csv", index=False)
def summ(T):
    n = T.ev_draftkings.notna().sum(); se = lambda c: T[c].std() / np.sqrt(T[c].notna().sum())
    return {"bets": int(len(T)), "priced": int(n), "avg_price": round(float(T.price.mean()), 1),
            "point_clv": round(float(T.point_clv.mean()), 3),
            "ev_point_only_pct": round(100 * float(T.ev_point_only.mean()), 2),
            "ev_vs_dk_close_pct": round(100 * float(T.ev_draftkings.mean()), 2), "se_dk": round(100 * float(se("ev_draftkings")), 2),
            "ev_vs_pin_close_pct": round(100 * float(T.ev_pinnacle.mean()), 2), "se_pin": round(100 * float(se("ev_pinnacle")), 2),
            "units": round(float(T.units.sum()), 1)}
out["T3_movement_bets_2025_26"] = summ(T3)
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(R + "price_clv_results.json", "w"), indent=1, default=str)

# ---- T1 uncertainty: paired bootstrap of the Brier gain (1,000 draws)
rng = np.random.default_rng(7)
for row in out["T1"]:
    t = L[(L.book == row["book"]) & (L.market == row["market"]) & (L.season == row["season"])]
    mg = margin_a(t, "point_a_close"); ok = mg != 0
    y = (mg[ok] > 0).astype(float); p = t.p_a_close.values[ok]; g = (y - 0.5) ** 2 - (y - p) ** 2
    bs = [g[rng.integers(0, len(g), len(g))].mean() for _ in range(1000)]
    row["gain_x1000_90ci"] = [round(1000 * float(np.percentile(bs, 5)), 3), round(1000 * float(np.percentile(bs, 95)), 3)]

# ---- T3 (ii): step 2 pre-registered residual bets, 2025-26, DK first-seen line and price (|resid| >= 3, bet against)
Rz = pd.read_csv(R + "opener_residuals.csv"); Rz = Rz[(Rz.season == 2026) & (Rz.dk_resid.abs() >= 3)].copy()
Rz["date"] = pd.to_datetime(Rz.date)
Rz = Rz.merge(ids, on=["date", "home", "away"], how="left")
rows = []
for _, r in Rz.iterrows():
    side = "b" if r.dk_resid > 0 else "a"                       # opened too high -> under
    px = r.dk_open_under_px if side == "b" else r.dk_open_over_px
    pclv = (r.dk_open_point - r.dk_close_point) if side == "b" else (r.dk_close_point - r.dk_open_point)
    won = (r.final_total < r.dk_open_point) if side == "b" else (r.final_total > r.dk_open_point)
    push = r.final_total == r.dk_open_point
    rec = {"point_clv": pclv, "price": px, "units": 0.0 if push else (dec(px) - 1 if won else -1.0)}
    for bk in ["draftkings", "pinnacle"]:
        key = (r.event_id, bk, "totals")
        rec[f"ev_{bk}"] = float(price_ev(CL.loc[key], side, r.dk_open_point, px, "totals", k["totals"])[0]) if key in CL.index else np.nan
    c0 = CL.loc[(r.event_id, "draftkings", "totals")].copy() if (r.event_id, "draftkings", "totals") in CL.index else None
    if c0 is not None: c0["p_a_close"] = 0.5; rec["ev_point_only"] = float(price_ev(c0, side, r.dk_open_point, -110, "totals", k["totals"])[0])
    rows.append(rec)
T3b = pd.DataFrame(rows); out["T3_step2_residual_bets_2025_26"] = summ(T3b)

# ---- T3 (iii): live 2026-27 picks, priced from research/live_odds at lock time (DK snapshot within 10 min)
H = pd.read_csv(sorted(glob.glob("data/odds_history/nba/2026-0[3-4]*.csv.gz"))[0], usecols=["event_id", "home", "away"]).drop_duplicates()
nm = H.merge(O[["event_id", "home", "away"]], on="event_id", suffixes=("_full", ""))
name = dict(zip(nm.home_full, nm.home)) | dict(zip(nm.away_full, nm.away))
LV = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("research/live_odds/nba/*.csv.gz"))])
LV = LV[LV.book.isin(["draftkings", "pinnacle"]) & LV.market.isin(["totals", "spreads"])].copy()
LV["home"] = LV.home.map(name); LV["away"] = LV.away.map(name)
LV["snap"] = pd.to_datetime(LV.snapshot_utc).dt.tz_convert("America/New_York").dt.tz_localize(None)
LV["tip"] = pd.to_datetime(LV.commence_et); LV = LV[LV.snap <= LV.tip]
LV["s"] = np.where(LV.market == "totals", np.where(LV.outcome == "Over", "a", "b"), np.where(LV.outcome.map(name) == LV.home, "a", "b"))
LW = LV.pivot_table(index=["home", "away", "tip", "book", "market", "snap"], columns="s", values=["price", "point"], aggfunc="first")
LW.columns = [f"{a}_{b}" for a, b in LW.columns]; LW = LW.reset_index().dropna(subset=["price_a", "price_b", "point_a"])
qa, qb = 1 / dec(LW.price_a), 1 / dec(LW.price_b); LW["p_a"] = qa / (qa + qb)
P = pd.read_csv("state/picks_log.csv"); P = P.dropna(subset=["home_pts"]); P["lock"] = pd.to_datetime(P.locked_at_et).dt.floor("s")
live = []
for _, r in P.iterrows():
    for m, col, sidef in [("totals", "open_total_bet", lambda v: "a" if v == "over" else "b"),
                          ("spreads", "open_spread_bet", lambda v: "a" if v == "home" else "b")]:
        if pd.isna(r[col]) or r[col] in ("", "none", "pass"): continue
        g = LW[(LW.home == r.home) & (LW.away == r.away) & (LW.market == m)]
        dk = g[g.book == "draftkings"].sort_values("snap")
        if dk.empty: continue
        at = dk.iloc[(dk.snap - r.lock).abs().argsort()[:1]]
        if abs((at.snap.iloc[0] - r.lock).total_seconds()) > 600: continue
        side = sidef(r[col]); a = at.iloc[0]
        line = a.point_a; px = a.price_a if side == "a" else a.price_b
        rec = {"date": r.date, "home": r.home, "market": m, "side": side, "line": line, "price": px}
        for bk in ["draftkings", "pinnacle"]:
            c = g[g.book == bk].sort_values("snap")
            if c.empty: rec[f"ev_{bk}"] = np.nan; continue
            cl = {"p_a_close": c.p_a.iloc[-1], "point_a_close": c.point_a.iloc[-1]}
            rec[f"ev_{bk}"] = float(price_ev(cl, side, line, px, m, k[m])[0])
            if bk == "draftkings":
                d = price_ev(cl, side, line, px, m, k[m])[1]; rec["point_clv"] = float(d)
                rec["ev_point_only"] = float(price_ev({"p_a_close": 0.5, "point_a_close": cl["point_a_close"]}, side, line, -110, m, k[m])[0])
        live.append(rec)
LI = pd.DataFrame(live)
out["T3_live_2026_27"] = {m: {"bets": int(len(t)), "point_clv": round(float(t.point_clv.mean()), 3),
                              "ev_point_only_pct": round(100 * float(t.ev_point_only.mean()), 2),
                              "ev_vs_dk_close_pct": round(100 * float(t.ev_draftkings.mean()), 2),
                              "ev_vs_pin_close_pct": round(100 * float(t.ev_pinnacle.mean()), 2)} for m, t in LI.groupby("market")} if len(LI) else "no picks inside live_odds coverage"
LI.to_csv(R + "price_clv_live_picks.csv", index=False)
print(json.dumps({k_: out[k_] for k_ in ["T3_step2_residual_bets_2025_26", "T3_live_2026_27"]}, indent=1, default=str))
print([(r["book"], r["market"], r["season"], r["gain_x1000"], r["gain_x1000_90ci"]) for r in out["T1"]])
json.dump(out, open(R + "price_clv_results.json", "w"), indent=1, default=str)
