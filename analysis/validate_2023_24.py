import sys, glob, os, numpy as np, pandas as pd
sys.path.insert(0, "analysis")
W = "."
exec(open("analysis/odds_openers.py").read().split("rows = []")[0].replace("W = os.path.abspath(sys.argv[1])", ""))
P = pd.read_csv("_tmp/model1_open_preds_2024.csv"); P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
Q = pd.read_csv("analysis/shot_quality_games.csv")[["date", "home", "away", "h_pre_luck", "h_pre_opp_luck", "a_pre_luck", "a_pre_opp_luck", "L_total"]]
G = P.merge(Q, on=["date", "home", "away"], how="left").dropna(subset=["open_total"])
G["pts_total"] = G.home_pts + G.away_pts; G["margin"] = G.home_pts - G.away_pts
# team games played so far (min 5 for the luck correction), league-relative luck = that night's average team luck
G = G.sort_values("date"); cnt = {}
hg, ag = [], []
for r in G.itertuples():
    hg.append(cnt.get(r.home, 0)); ag.append(cnt.get(r.away, 0)); cnt[r.home] = cnt.get(r.home, 0) + 1; cnt[r.away] = cnt.get(r.away, 0) + 1
G["hg"], G["ag"] = hg, ag
lg = G.groupby("date")[["h_pre_luck", "a_pre_luck", "h_pre_opp_luck", "a_pre_opp_luck"]].transform("mean").mean(axis=1)
G["luck_adj"] = np.where((G.hg >= 5) & (G.ag >= 5), -0.5 * (G.L_total - 4 * lg), 0.0); G["luck_adj"] = G.luck_adj.fillna(0)
G["pt_adj"] = G.pred_total + G.luck_adj

# DraftKings prices and lines at open, +15/30/60 min, and close
snap = {}
for f in sorted(glob.glob("data/odds_history/nba/2023-1*.csv.gz") + glob.glob("data/odds_history/nba/2024-0*.csv.gz")):
    d = pd.read_csv(f); d = d[d.book == "draftkings"]
    d["t"] = pd.to_datetime(d.snapshot_utc); d["tip"] = pd.to_datetime(d.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    d = d[d.t < d.tip]
    for eid, g in d.groupby("event_id"):
        H, A = g.home.iloc[0], g.away.iloc[0]
        key = (str(g.tip.iloc[0].tz_convert("America/New_York").date()), NAME.get(H), NAME.get(A))
        sp = g[(g.market == "spreads")]; to = g[g.market == "totals"]
        out = {}
        for nm, gg, side in (("sp", sp, H), ("ov", to, "Over")):
            s = gg[gg.outcome == side].sort_values("t"); o = gg[gg.outcome != side].sort_values("t")
            if not len(s): continue
            t0 = s.t.iloc[0]
            for lab, tt in (("open", t0), ("m15", t0 + pd.Timedelta(minutes=15)), ("m30", t0 + pd.Timedelta(minutes=30)),
                            ("m60", t0 + pd.Timedelta(minutes=60)), ("close", s.t.iloc[-1])):
                a = s[s.t <= tt].iloc[-1]; b = o[o.t <= tt]
                out[f"{nm}_{lab}"] = a.point; out[f"{nm}_{lab}_px"] = a.price; out[f"{nm}_{lab}_opx"] = b.price.iloc[-1] if len(b) else np.nan
        snap[key] = out
S = pd.DataFrame.from_dict(snap, orient="index"); S.index = pd.MultiIndex.from_tuples(S.index, names=["date", "home", "away"])
G = G.merge(S.reset_index(), on=["date", "home", "away"], how="left")
print("games", len(G), "with DK snapshots", G.ov_open.notna().sum())

def grade(res): w, l = int((res > 0).sum()), int((res < 0).sum()); return w, l
def units(res, px):
    win = np.where(px < 0, 100 / -px, px / 100)
    return float(np.where(res > 0, win, np.where(res < 0, -1, 0)).sum())

print("\nTOTALS at the DK opener, edge 3+ (real DK prices):")
for lab, col in (("model as live before luck", "pred_total"), ("with luck correction", "pt_adj")):
    e = G[col] - G.ov_open; s = G[e.abs() >= 3].copy(); over = e[e.abs() >= 3] > 0
    res = np.where(over, s.pts_total - s.ov_open, s.ov_open - s.pts_total)
    px = np.where(over, s.ov_open_px, s.ov_open_opx)
    w, l = grade(res); u110 = float(np.where(res > 0, 100 / 110, np.where(res < 0, -1, 0)).sum())
    print(f"  {lab:28s}: {w + l} bets, won {w / (w + l):.1%}, {u110:+.1f}u at -110, {units(res, px):+.1f}u at DK's real prices")
    capped = px >= -120
    print(f"     with the -120 cap: {capped.sum()} bets (skipped {(~capped).sum()}), {units(res[capped], px[capped]):+.1f}u; "
          f"skipped ones made {units(res[~capped], px[~capped]):+.1f}u")
    for t in ("m15", "m30", "m60", "close"):
        ln = s[f"ov_{t}"]; pxt = np.where(over, s[f"ov_{t}_px"], s[f"ov_{t}_opx"])
        # bet only if the model still has 3+ against that later line
        still = np.where(over, s[col] - ln >= 3, ln - s[col] >= 3)
        r2 = np.where(over, s.pts_total - ln, ln - s.pts_total)
        w2, l2 = grade(r2[still])
        print(f"     waiting until {t:5s}: {w2 + l2} bets still qualify, won {w2 / max(w2 + l2, 1):.1%}, {units(r2[still], pxt[still]):+.1f}u")
    clv = np.where(over, s.ov_close - s.ov_open, s.ov_open - s.ov_close)
    print(f"     line moved our way {np.mean(clv > 0):.0%}, against {np.mean(clv < 0):.0%}")
e = G.pred_total - G.ov_open; mv = G.ov_close - G.ov_open; ok = e.notna() & mv.notna()
print(f"  model edge vs open->close move: r = {np.corrcoef(e[ok], mv[ok])[0, 1]:+.3f}")

print("\nSPREADS at the DK opener, edge 3+:")
e = G.pred_margin + G.sp_open; s = G[e.abs() >= 3].copy(); home = e[e.abs() >= 3] > 0
res = np.where(home, s.margin + s.sp_open, -(s.margin + s.sp_open)); px = np.where(home, s.sp_open_px, s.sp_open_opx)
w, l = grade(res); print(f"  {w + l} bets, won {w / (w + l):.1%}, {units(res, px):+.1f}u at DK prices")
clv = np.where(home, s.sp_open - s.sp_close, s.sp_close - s.sp_open)
print(f"  line moved our way {np.mean(clv > 0):.0%}, against {np.mean(clv < 0):.0%}")
mv = -(G.sp_close - G.sp_open); ok = e.notna() & mv.notna()
print(f"  model edge vs open->close move: r = {np.corrcoef(e[ok], mv[ok])[0, 1]:+.3f}")
for k in (3, 4, 5, 6):
    s = G[e.abs() >= k]; h = (e[e.abs() >= k] > 0); r_ = np.where(h, s.margin + s.sp_open, -(s.margin + s.sp_open)); w, l = grade(r_)
    print(f"   edge {k}+: {w + l} bets, {w / (w + l):.1%}")
G.to_csv("_tmp/test_2024_games.csv", index=False)
