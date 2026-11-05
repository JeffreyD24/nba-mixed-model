"""NCAAM daily test-only run (Nov 5, 2026). The model FAILED its pre-registered backtest (ncaab/research/NCAAM_RESULTS_2026-11-05.md),
so 2026-27 is recorded, not bet: no alerts. Each morning:
  1. add the last few days' finished games, scores and lines (ncaab/backfill.py)
  2. walk-forward predictions for every season (ncaab/model.py; ridge 5, carryover 0.8, no decay; no lookahead)
  3. grade this season's TEST bets with the pre-registered rule (spreads 5+, totals 6+ vs the Open; CLV to the DK close)
     -> ncaab/state/test_record.md and ncaab/state/test_bets.csv
  python ncaab/daily.py WORKDIR"""
import os, sys, subprocess
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); PY = sys.executable
ST = os.path.join(W, "ncaab", "state"); os.makedirs(ST, exist_ok=True)
y = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None) - pd.Timedelta(days=1)
done = os.path.join(W, "ncaab", "data", "dates_done.txt")
if os.path.exists(done):              # re-fetch the last 3 days (late scores / late-posted results)
    keep = [d for d in open(done).read().split() if pd.Timestamp(d) < y - pd.Timedelta(days=2)]
    open(done, "w").write("".join(f"{d}\n" for d in keep))
subprocess.run([PY, os.path.join(W, "ncaab", "backfill.py"), W, "--from", str((y - pd.Timedelta(days=2)).date()), "--to", str(y.date())], check=True)
subprocess.run([PY, os.path.join(W, "ncaab", "model.py"), W, "--predict", "5", "0.8", "0"], check=True)
P = pd.read_csv(os.path.join(W, "ncaab", "data", "preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
S = P[P.season == P.season.max()].copy()
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})]).sort_values("date")
long["n"] = long.groupby(["season", "t"]).cumcount(); first = long.groupby(["season", "t", "date"]).n.min()
S["hn"] = [first.get((s, t, d), 0) for s, t, d in zip(S.season, S.hk, S.date)]; S["an"] = [first.get((s, t, d), 0) for s, t, d in zip(S.season, S.ak, S.date)]
ok = S.home_d1 & S.away_d1 & S.neutral_ok & (np.minimum(S.hn, S.an) >= 3)
rows = []
for mk, thr, line, close, model, res in (("spread", 5, -S.open_spread, -S.dk_spread, S.pred_margin, S.home_pts - S.away_pts),
                                         ("total", 6, S.open_total, S.dk_total, S.pred_total, S.home_pts + S.away_pts)):
    e = model - line; k = ok & line.notna() & (e.abs() >= thr)
    for i in S.index[k]:
        sg = np.sign(e[i]); r = sg * (res[i] - line[i])
        rows.append(dict(date=str(S.date[i].date()), home=S.home[i], away=S.away[i], market=mk,
                         side=("home" if sg > 0 else "away") if mk == "spread" else ("over" if sg > 0 else "under"),
                         open_line=S.open_spread[i] if mk == "spread" else line[i], model=round(model[i], 1), edge=round(abs(e[i]), 1),
                         dk_close=S.dk_spread[i] if mk == "spread" else close[i], clv=round(sg * (close[i] - line[i]), 2) if pd.notna(close[i]) else np.nan,
                         result="W" if r > 0 else "L" if r < 0 else "P", units=100 / 110 if r > 0 else -1.0 if r < 0 else 0.0))
# conference-game totals TEST (Nov 5, 2026; ncaab/research/CONF_TOTALS_RESULTS_2026-11-05.md): 6+ vs the DraftKings close, conference games
conf = S.conf_game.astype(str) == "True"; ec = S.pred_total - S.dk_total
for i in S.index[ok & conf & S.dk_total.notna() & (ec.abs() >= 6)]:
    sg = np.sign(ec[i]); r = sg * (S.home_pts[i] + S.away_pts[i] - S.dk_total[i])
    rows.append(dict(date=str(S.date[i].date()), home=S.home[i], away=S.away[i], market="conference total (vs DK close)",
                     side="over" if sg > 0 else "under", open_line=S.open_total[i], model=round(S.pred_total[i], 1), edge=round(abs(ec[i]), 1),
                     dk_close=S.dk_total[i], clv=np.nan, result="W" if r > 0 else "L" if r < 0 else "P", units=100 / 110 if r > 0 else -1.0 if r < 0 else 0.0))
B = pd.DataFrame(rows, columns=["date", "home", "away", "market", "side", "open_line", "model", "edge", "dk_close", "clv", "result", "units"])
B.to_csv(os.path.join(ST, "test_bets.csv"), index=False)
L = [f"# NCAAM 2026-27 TEST record (not bets), updated {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET", "",
     "Pre-registered rule (ncaab/research/NCAAM_PREREG_2026-11-05.md) failed the backtest, so this season is tracked only.",
     "Spreads 5+ / totals 6+ pts vs the Open; both teams 3+ games; CLV = Open to DraftKings close (break-even 0.67 spreads, 0.99 totals).", ""]
for mk, g in B.groupby("market"):
    L.append(f"- **{mk}**: {len(g)} test bets, {(g.result == 'W').sum()}-{(g.result == 'L').sum()}-{(g.result == 'P').sum()}, "
             f"{g.units.sum():+.2f}u at the Open, CLV {g.clv.mean():+.2f}")
if not len(B): L.append("- no test bets yet (both teams need 3+ games)")
L.append(f"\nGames this season so far: {len(S)}; eligible: {int(ok.sum())}.")
open(os.path.join(ST, "test_record.md"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
