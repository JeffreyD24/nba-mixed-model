"""
NBA shot quality: expected points per field-goal attempt from ESPN shot location and type (logistic regression fit on
earlier seasons only), then "shooting luck" per team-game = actual FG points - expected FG points.
Question: do teams that shot better (or allowed worse shooting) than their shot quality get overrated by the betting line?
If so, betting against season-to-date luck should beat the line.
  python analysis/shot_quality.py WORKDIR   -> analysis/shot_quality_games.csv, printed results
"""
import os, sys
import numpy as np, pandas as pd
from scipy.optimize import minimize
W = os.path.abspath(sys.argv[1])
S = pd.read_csv(os.path.join(W, "data", "nba_shots_hist.csv.gz"))
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))

S["value"] = np.where(S.value > 0, S.value, np.where(S.text.str.contains("three point", case=False), 3, 2))
xy = np.hypot(S.x - 25, S.y - 5.25)
S["d"] = S.dist.fillna(xy).clip(0, 60)
st = S.shot_type.fillna("").str.lower()
FLAGS = {"dunk": "dunk", "layup": "layup|finger roll", "hook": "hook", "pullup": "pullup", "stepback": "step back",
         "fade": "fade|turnaround", "float": "float", "driving": "driving", "cutting": "cutting", "running": "running",
         "putback": "putback|tip", "alleyoop": "alley oop", "heave": "heave", "bank": "bank"}


def design(D):
    d = D.d.values; is3 = (D.value == 3).values
    cols = dict(const=np.ones(len(D)), d=d / 10, d2=(d / 10) ** 2, ld=np.log1p(d), is3=is3.astype(float),
                corner3=(is3 & (D.y.fillna(99).values <= 14)).astype(float), deep3=(is3 & (d >= 28)).astype(float),
                q4=(D.period.values >= 4).astype(float), late=((D.sec_left.fillna(99).values <= 4) & True).astype(float))
    s_ = D.shot_type.fillna("").str.lower()
    for k, pat in FLAGS.items(): cols[k] = s_.str.contains(pat).values.astype(float)
    return np.column_stack(list(cols.values()))


def fit(X, y, l2=1e-3):
    def f(b):
        z = X @ b; p = 1 / (1 + np.exp(-z))
        return -(y * z - np.logaddexp(0, z)).sum() + l2 * b @ b, -(X.T @ (y - p)) + 2 * l2 * b
    return minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B").x


S["xmake"] = np.nan
for s in sorted(S.season.unique()):
    tr = S[S.season < s] if s > S.season.min() else S[S.season == s]       # first season: in-sample (only used as history)
    b = fit(design(tr), tr.made.values.astype(float))
    m = S.season == s
    S.loc[m, "xmake"] = 1 / (1 + np.exp(-(design(S[m]) @ b)))
te = S[S.season >= 2023]
ll = lambda p: -np.mean(te.made * np.log(p) + (1 - te.made) * np.log(1 - p))
print(f"make-probability log-loss 2023-26: model {ll(te.xmake):.4f} vs league average {ll(np.full(len(te), te.made.mean())):.4f}")

S["pts"] = S.made * S.value; S["xpts"] = S.xmake * S.value
S["m3"] = np.where(S.value == 3, S.made, 0); S["x3"] = np.where(S.value == 3, S.xmake, 0)
TG = S.groupby(["season", "espn_event_id", "date", "home", "away", "team"]).agg(
    fga=("made", "size"), pts=("pts", "sum"), xpts=("xpts", "sum"), m3=("m3", "sum"), x3=("x3", "sum")).reset_index()
TG["luck"] = TG.pts - TG.xpts; TG["luck3"] = 3 * (TG.m3 - TG.x3)
opp = TG[["espn_event_id", "team", "luck", "luck3", "xpts", "pts"]].rename(columns={"team": "opp", "luck": "opp_luck", "luck3": "opp_luck3",
                                                                                 "xpts": "opp_xpts", "pts": "opp_pts"})
TG = TG.merge(TG[["espn_event_id", "team"]].rename(columns={"team": "opp"}), on="espn_event_id")
TG = TG[TG.team != TG.opp].merge(opp, on=["espn_event_id", "opp"])
TG = TG.sort_values(["season", "team", "date"])
# season-to-date averages BEFORE each game (no lookahead), at least 5 games
for c in ("luck", "opp_luck", "luck3", "opp_luck3", "xpts", "opp_xpts"):
    g = TG.groupby(["season", "team"])[c]
    TG[f"pre_{c}"] = g.transform(lambda v: v.shift().expanding().mean())
TG["n_prev"] = TG.groupby(["season", "team"]).cumcount()
TG.loc[TG.n_prev < 5, [c for c in TG if c.startswith("pre_")]] = np.nan

# persistence: is shooting luck repeatable? (first half vs second half of each team-season)
TG["half"] = (TG.groupby(["season", "team"]).cumcount() >= 41).astype(int)
hh = TG.groupby(["season", "team", "half"])[["luck", "opp_luck", "xpts", "opp_xpts"]].mean().unstack("half")
print("\nFirst-half vs second-half correlation per team-season (1 = fully repeatable, 0 = pure luck):")
for c in ("luck", "opp_luck", "xpts", "opp_xpts"):
    print(f"  {c:9s} {hh[c][0].corr(hh[c][1]):+.2f}")

# join to games and lines
G = T.copy(); G["date"] = pd.to_datetime(G.date).dt.strftime("%Y-%m-%d")
TG["date"] = pd.to_datetime(TG.date).dt.strftime("%Y-%m-%d")
hcols = {c: f"h_{c}" for c in TG if c.startswith("pre_")}; acols = {c: f"a_{c}" for c in TG if c.startswith("pre_")}
Hh = TG[TG.team == TG.home][["date", "home", "away"] + list(hcols)].rename(columns=hcols)
Aa = TG[TG.team == TG.away][["date", "home", "away"] + list(acols)].rename(columns=acols)
G = G.merge(Hh, on=["date", "home", "away"], how="inner").merge(Aa, on=["date", "home", "away"], how="inner")
G["margin"] = G.home_pts - G.away_pts; G["pts_total"] = G.home_pts + G.away_pts
# luck that inflates the home side's results: home's own luck minus luck against home, minus the same for the away team
G["L_margin"] = (G.h_pre_luck - G.h_pre_opp_luck) - (G.a_pre_luck - G.a_pre_opp_luck)
G["L_total"] = G.h_pre_luck + G.h_pre_opp_luck + G.a_pre_luck + G.a_pre_opp_luck
G.to_csv(os.path.join(W, "analysis", "shot_quality_games.csv"), index=False)


def test(G, line_s, line_t, label):
    g = G.dropna(subset=["L_margin", line_s]).copy()
    cover = g.margin + g[line_s]; g = g[cover != 0]; cover = cover[cover != 0]
    b = np.polyfit(g.L_margin, cover, 1)[0]
    r = np.corrcoef(g.L_margin, cover)[0, 1]
    print(f"\n{label}: spreads, {len(g)} games. Home cover margin vs luck gap: slope {b:+.3f} pts per pt of luck, r = {r:+.3f} "
          f"(se of r ~ {1 / np.sqrt(len(g)):.3f})")
    for k in (2, 3, 4, 6):
        s = g[g.L_margin.abs() >= k]
        win = ((s.margin + s[line_s] > 0) == (s.L_margin < 0)).mean()      # bet the side whose results were LESS lucky
        print(f"   bet against the luckier team when the gap is {k}+ pts/game: {len(s):4d} bets, won {win:.1%}")
    t = G.dropna(subset=["L_total", line_t]).copy(); ov = t.pts_total - t[line_t]; t = t[ov != 0]; ov = ov[ov != 0]
    r = np.corrcoef(t.L_total, ov)[0, 1]
    print(f"{label}: totals, {len(t)} games. Over margin vs combined luck: r = {r:+.3f}")
    for k in (3, 5, 8):
        s = t[t.L_total.abs() >= k]
        win = ((s.pts_total > s[line_t]) == (s.L_total < 0)).mean()
        print(f"   bet under when shooting has been lucky (over when unlucky), {k}+ pts/game: {len(s):4d} bets, won {win:.1%}")


test(G[G.season >= 2023], "spread", "total", "Closing lines 2023-26")
test(G[G.season >= 2025], "open_spread", "open_total", "Opening lines 2025-26")
for s in range(2023, 2027):
    g = G[G.season == s].dropna(subset=["L_margin", "spread"])
    c = g.margin + g.spread
    print(f"  {s}: r(luck gap, home cover) = {np.corrcoef(g.L_margin, c)[0, 1]:+.3f} ({len(g)} games)")
