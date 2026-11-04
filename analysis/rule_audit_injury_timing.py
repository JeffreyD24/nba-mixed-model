"""Rule audit (Nov 4, 2026): what does the "current injury report" gate cost the NBA totals bets?

Live, an alert needs the 8 PM night-before injury report. DraftKings' openers mostly post 3-7 PM, so by the time the report
is out the opener is 1+ hours old and the rule turns an unmoved line into OPTIONAL (not pushed). The backtests graded the bet
at the opener WITH the 8 PM report, which the bettor never has together for ~74% of games.

This replays the live totals number (Model 1 + luck 0.5 + last-10 form 0.20, morning-lock lag 1, both teams 10+ games, edge 3+)
at DraftKings 2023-24..2025-26 under bettable timings:
  S0  opener + 8 PM report                (the backtest as documented; not achievable when the opener is before 8 PM)
  S1  opener + each team's report from its PREVIOUS game  (what you know when the opener posts; conservative: ignores
      the 5-7 PM reports that sometimes already list tomorrow)
  S2  DraftKings line at ~9 PM (20:55 snapshot) + 8 PM report  (wait for the report, bet the line then)
  S3  DraftKings line at ~9 AM game day + 8 PM report          (bet in the morning)
For S2/S3 also: drop lines that moved 0.5+ against the model since the open (the PASS rule), and "current live" = only
lines that moved 0.5+ toward the model (unmoved stale openers are OPTIONAL and not pushed).
  python analysis/rule_audit_injury_timing.py WORKDIR  -> analysis/rule_audit_injury_timing_output.txt
"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)

src = open(os.path.join(W, "nba_mixed_model.py")).read()
assert "past = L_all[L_all.date < d]" in src
lagged = src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]")
ns = {"__name__": "nm_lag"}; exec(compile(lagged, "nba_mixed_model_lag", "exec"), ns); ns["LAG_DAYS"] = 1

T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total", "open_total_t", "close_total"]].drop_duplicates(["date", "home", "away"])
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")

# ---- S1 features: each team's PREVIOUS game's pre-tip report in place of the 8 PM report
INJ = ["miss_off", "miss_def", "n_out"]
long = pd.concat([T[["date", "season", "home"] + [f"home_{c}" for c in INJ]].rename(columns=lambda c: c.replace("home_", "") if c != "home" else "team"),
                  T[["date", "season", "away"] + [f"away_{c}" for c in INJ]].rename(columns=lambda c: c.replace("away_", "") if c != "away" else "team")])
long = long.sort_values(["team", "date"])
for c in INJ: long[f"prev_{c}"] = long.groupby("team")[c].shift(1)
prev = long.set_index(["date", "team"])[[f"prev_{c}" for c in INJ]]
TS = T.copy()
for side in ("home", "away"):
    p = prev.reindex(pd.MultiIndex.from_arrays([TS.date, TS[side]])).values
    for j, c in enumerate(INJ):
        TS[f"{side}_{c}_open"] = np.where(pd.isna(p[:, j]), TS[f"{side}_{c}_open"], p[:, j])
chg = (TS[[f"{s}_{c}_open" for s in ("home", "away") for c in INJ]].values != T[[f"{s}_{c}_open" for s in ("home", "away") for c in INJ]].values).any(1)

# ---- DraftKings line at 20:55 the night before and 08:55 game day
S = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "t", "book", "tot", "sp", "date"])
S = S[(S.book == "draftkings") & S.tot.notna()].copy()
TIP = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "tip", "date"]).drop_duplicates(["date", "home", "away"])
S["t"] = pd.to_datetime(S.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
S["gd"] = pd.to_datetime(S.date)
def line_at(hours_from_gameday_midnight, col="tot"):
    x = S[S[col].notna() & (S.t <= S.gd + pd.Timedelta(hours=hours_from_gameday_midnight))].sort_values("t").groupby(["date", "home", "away"]).tail(1)
    return x.set_index(["date", "home", "away"])[col]
L9pm, L9am = line_at(-3.0), line_at(9.0)
LATER = {f"l{h}": line_at(h) for h in (-2.0, 0.0, 12.0, 15.0, 18.0)}
LATER.update({f"sp{h}": line_at(h, "sp") for h in (-3.0, 0.0, 9.0, 12.0, 15.0)})       # 21:00 night before (20:55 snapshot); 09:00 game day (08:55 snapshot)

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

TG = pd.read_csv(os.path.join(W, "analysis", "shot_quality_team_games.csv.gz")); TG["date"] = pd.to_datetime(TG.date)
TT = T.copy(); TT["date"] = pd.to_datetime(TT.date)
pts = pd.concat([TT[["season", "date", "home"]].rename(columns={"home": "team"}).assign(tp=TT.home_pts + TT.away_pts),
                 TT[["season", "date", "away"]].rename(columns={"away": "team"}).assign(tp=TT.home_pts + TT.away_pts)])
TG = TG.merge(pts, on=["season", "date", "team"], how="left")
hist = {k: g.sort_values("date") for k, g in TG.groupby(["season", "team"])}
def feats(season, team, d):
    g = hist.get((season, team))
    if g is None: return (np.nan,) * 3
    g = g[g.date < d - pd.Timedelta(days=1)]; n = len(g)
    if n < 5: return (n, np.nan, np.nan)
    return (n, g.luck.mean() + g.opp_luck.mean(), g.tp.tail(10).mean() - g.tp.mean() if n >= 6 else np.nan)

def live_totals(TT_):
    rows = []
    for test in (2024, 2025, 2026):
        train = list(range(2022, test))
        with contextlib.redirect_stdout(io.StringIO()):
            _, P = ns["run"](TT_[TT_.season.isin(train + [test])], train, test, today_suffix="_open")
        P = P.dropna(subset=["open_total"]).copy(); P["d"] = pd.to_datetime(P.date)
        for side in ("home", "away"):
            F = [feats(test, t, d) for t, d in zip(P[side], P.d)]
            P[f"{side}_n"] = [f[0] for f in F]; P[f"{side}_luck"] = [f[1] for f in F]; P[f"{side}_f10"] = [f[2] for f in F]
        P["L"] = P.home_luck + P.away_luck; lg = P.groupby("date").L.transform("mean")
        P["pt_live"] = P.pred_total + np.where((P.home_n >= 5) & (P.away_n >= 5), (-0.5 * (P.L - lg)).fillna(0), 0)
        P["tot_model"] = P.pt_live + 0.20 * (P.home_f10 + P.away_f10).fillna(0)
        rows.append(P[(P.home_n >= 10) & (P.away_n >= 10)].assign(season=test))
    return pd.concat(rows)

R8 = live_totals(T)            # 8 PM report
RS = live_totals(TS)           # previous game's report
key = ["date", "home", "away"]
for X in (R8, RS): X["date"] = pd.to_datetime(X.date).dt.strftime("%Y-%m-%d")
R8 = R8.drop(columns=[c for c in ("open_total_t", "close_total") if c in R8]).merge(
    T[key + ["open_total_t", "close_total"]].drop_duplicates(key), on=key, how="left")
ot = pd.to_datetime(R8.open_total_t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
R8["open_before_8pm"] = (ot < pd.to_datetime(R8.date) - pd.Timedelta(hours=4)).values
idx = pd.MultiIndex.from_frame(R8[key])
R8["l9pm"] = L9pm.reindex(idx).values; R8["l9am"] = L9am.reindex(idx).values
for k_, v_ in LATER.items(): R8[k_] = v_.reindex(idx).values
R8 = R8.merge(RS[key + ["tot_model", "pred_margin"]].rename(columns={"tot_model": "tot_stale", "pred_margin": "pm_stale"}), on=key, how="left")

def grade(model, line, actual, mask=None):
    e = model - line; m = (e.abs() >= 3) & line.notna() & model.notna()
    if mask is not None: m &= mask
    r = np.sign(e[m]) * (actual[m] - line[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
    return w + l, (w / max(w + l, 1)), w * 100 / 110 - l
def row(name, model, line, mask=None):
    parts, tot = [], [0, 0.0, 0.0]
    for s in (2024, 2025, 2026):
        k = R8.season == s
        n, wp, u = grade(model[k], line[k], R8.act[k], None if mask is None else mask[k])
        parts.append(f"{s}: {n} {wp:.1%} {u:+.1f}u"); tot[0] += n; tot[1] += wp * n; tot[2] += u
    say(f"  {name:<58} " + " | ".join(parts) + f" | ALL: {tot[0]} {tot[1] / max(tot[0], 1):.1%} {tot[2]:+.1f}u  ({tot[2] / max(tot[0], 1) * 100:+.1f}u/100)")

R8["act"] = R8.home_pts + R8.away_pts
say("NBA live totals number at DraftKings 2023-26, edge 3+, both teams 10+ games, morning-lock lag 1 (units at -110)")
say(f"games: {len(R8)}; opener posted before 8 PM night before: {R8.open_before_8pm.mean():.0%}; "
    f"9 PM line found: {R8.l9pm.notna().mean():.0%}; 9 AM line found: {R8.l9am.notna().mean():.0%}")
say(f"S1 swap changed the injury inputs in {chg.mean():.0%} of all games (rest identical: no earlier report)")
say("\nS0 opener + 8 PM report (backtest)")
row("all openers", R8.tot_model, R8.open_total)
row("openers posted BEFORE 8 PM (report not out yet: not bettable)", R8.tot_model, R8.open_total, R8.open_before_8pm)
row("openers posted after 8 PM (bettable as tested)", R8.tot_model, R8.open_total, ~R8.open_before_8pm)
say("\nS1 opener + previous game's report (bettable the moment the opener posts)")
row("all openers", R8.tot_stale, R8.open_total)
row("openers posted before 8 PM", R8.tot_stale, R8.open_total, R8.open_before_8pm)
mv9 = R8.l9pm - R8.open_total; e9 = R8.tot_model - R8.l9pm
against9 = (mv9.abs() >= 0.5) & (np.sign(mv9) != np.sign(e9))     # over bet and line fell (or under and line rose) = against
toward9 = (mv9.abs() >= 0.5) & ~against9
say("\nS2 line at ~9 PM night before + 8 PM report (wait for the report)")
row("every 3+ edge", R8.tot_model, R8.l9pm)
row("minus lines moved 0.5+ against since open (PASS rule)", R8.tot_model, R8.l9pm, ~against9)
row("unmoved since open only (rule calls these OPTIONAL, no push)", R8.tot_model, R8.l9pm, mv9.abs() < 0.5)
row("moved 0.5+ toward the model only (= what live pushes now)", R8.tot_model, R8.l9pm, toward9)
mva = R8.l9am - R8.open_total; ea = R8.tot_model - R8.l9am
againsta = (mva.abs() >= 0.5) & (np.sign(mva) != np.sign(ea))
say("\nS3 line at ~9 AM game day + 8 PM report")
row("every 3+ edge", R8.tot_model, R8.l9am)
row("minus lines moved 0.5+ against since open", R8.tot_model, R8.l9am, ~againsta)
row("unmoved since open only", R8.tot_model, R8.l9am, mva.abs() < 0.5)
say("\nS1+S2 combined: bet the opener on the previous report; skip it if the 8 PM report then puts the edge on the OTHER side")
row("opener bets the 8 PM report keeps on the same side (edge any size)", R8.tot_stale, R8.open_total,
    np.sign(R8.tot_stale - R8.open_total) == np.sign(R8.tot_model - R8.open_total))
row("opener bets the 8 PM report keeps at 3+ edge", R8.tot_stale, R8.open_total, (R8.tot_model - R8.open_total).abs() >= 3)
row("opener bets the 8 PM report drops below 3 / flips", R8.tot_stale, R8.open_total, (R8.tot_model - R8.open_total).abs() < 3)
say("\nCLV check, S1 openers: average close move toward the bet (pts)")
e1 = R8.tot_stale - R8.open_total; m1 = e1.abs() >= 3
say(f"  {(np.sign(e1[m1]) * (R8.close_total[m1] - R8.open_total[m1])).mean():+.2f} pts over {int(m1.sum())} bets")
open(os.path.join(W, "analysis", "rule_audit_injury_timing_output.txt"), "w").write("\n".join(out) + "\n")
R8 = R8.merge(TIP, on=key, how="left")
R8.to_csv(os.path.join(W, "_tmp", "rule_audit_R8.csv"), index=False)
