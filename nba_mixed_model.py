"""
NBA spread / total mixed model with walk-forward backtest.

Model (one row per team-game, i.e. two rows per game):
    pts_ij = mu + b_home*home + b_b2b_off*b2b_i + b_b2b_def*b2b_j
             + O_i(season) + D_j(season) + e
  O = offensive team-season random effect, D = defensive team-season random effect,
  O ~ N(rho_O * O_prev_season, s2_O),  D ~ N(rho_D * D_prev_season, s2_D),  e ~ N(0, s2_e)

Variance components are estimated by REML on the training seasons (Henderson's mixed
model equations, same machinery as BLUP in animal breeding). In the test season the
variance components and fixed effects are frozen, and team effects are re-solved each
game day using ONLY games played before that day (no lookahead), with recent games
weighted more (half-life tuned on the last training season).

Predicted home margin = pred_home_pts - pred_away_pts ; predicted total = sum.
Bet the side of the closing line the model favors when |model - line| >= threshold.

Input CSV columns (one row per game):
    date, season, home, away, home_pts, away_pts, spread, total
  spread = closing line from the HOME team's perspective (home -5.5 -> -5.5)
  total  = closing over/under
  season = label for the season's END year (2025-26 -> 2026)
"""
import sys, json
import numpy as np, pandas as pd
from scipy.optimize import minimize

JUICE_WIN = 100 / 110  # profit per unit risked at -110


# ---------------------------------------------------------------- data prep
def add_rest(df):
    df = df.sort_values("date").reset_index(drop=True)
    last = {}
    b2b_h, b2b_a = [], []
    for d, h, a in zip(df.date, df.home, df.away):
        b2b_h.append(int(h in last and (d - last[h]).days == 1))
        b2b_a.append(int(a in last and (d - last[a]).days == 1))
        last[h] = d; last[a] = d
    df["b2b_home"], df["b2b_away"] = b2b_h, b2b_a
    return df


def long_rows(g):
    """two rows per game: scoring team's points vs the opponent"""
    h = pd.DataFrame({"gid": g.index, "pts": g.home_pts, "off": g.home, "def": g.away,
                      "home": 1, "b2b_off": g.b2b_home, "b2b_def": g.b2b_away,
                      "season": g.season, "date": g.date,
                      "miss_off": g.get("home_miss_off", 0.0), "miss_def": g.get("away_miss_def", 0.0)})
    a = pd.DataFrame({"gid": g.index, "pts": g.away_pts, "off": g.away, "def": g.home,
                      "home": 0, "b2b_off": g.b2b_away, "b2b_def": g.b2b_home,
                      "season": g.season, "date": g.date,
                      "miss_off": g.get("away_miss_off", 0.0), "miss_def": g.get("home_miss_def", 0.0)})
    L = pd.concat([h, a], ignore_index=True)
    if "home_miss_off" not in g:          # no injury columns -> original model
        L = L.drop(columns=["miss_off", "miss_def"])
    return L


def xmat(L):
    """fixed effects: intercept, home, b2b (scoring team), b2b (defending team),
    missing offense of scoring team, missing defense of defending team"""
    cols = [np.ones(len(L)), L.home, L.b2b_off, L.b2b_def]
    if "miss_off" in L:
        cols += [L.miss_off, L.miss_def]
    return np.column_stack(cols).astype(float)


def design(L, teams_by_season):
    """X (fixed) and Z (random: [offense team-seasons | defense team-seasons])"""
    X = xmat(L)
    keys = [(s, t) for s in sorted(teams_by_season) for t in teams_by_season[s]]
    idx = {k: i for i, k in enumerate(keys)}
    q = len(keys)
    Z = np.zeros((len(L), 2 * q))
    r = np.arange(len(L))
    Z[r, [idx[(s, t)] for s, t in zip(L.season, L.off)]] = 1
    Z[r, [q + idx[(s, t)] for s, t in zip(L.season, L["def"])]] = 1
    return X, Z, keys


# ---------------------------------------------------------------- MME / REML
def solve_mme(X, Z, y, a_off, a_def, w=None, z_prior=None, fixed=None):
    """Henderson MME. a_* = s2_e / s2_component. Optional weights, prior means for u,
    and fixed effects held constant (test season)."""
    n = len(y)
    w = np.ones(n) if w is None else w
    q2 = Z.shape[1]; q = q2 // 2
    A = np.r_[np.full(q, a_off), np.full(q, a_def)]
    yy = y.copy()
    if z_prior is not None:
        yy = yy - Z @ z_prior
    if fixed is not None:                      # fixed effects known -> solve u only
        r = yy - X @ fixed
        C = (Z.T * w) @ Z + np.diag(A)
        u = np.linalg.solve(C, (Z.T * w) @ r)
        return fixed, u + (0 if z_prior is None else z_prior)
    W = np.hstack([X, Z])
    C = (W.T * w) @ W
    p = X.shape[1]
    C[p:, p:] += np.diag(A)
    sol = np.linalg.solve(C, (W.T * w) @ yy)
    b, u = sol[:p], sol[p:]
    return b, u + (0 if z_prior is None else z_prior)


def neg2_reml(log_a, X, Z, y):
    a_off, a_def = np.exp(log_a)
    n, p = X.shape; q = Z.shape[1] // 2
    W = np.hstack([X, Z])
    C = W.T @ W
    C[p:, p:] += np.diag(np.r_[np.full(q, a_off), np.full(q, a_def)])
    rhs = W.T @ y
    sol = np.linalg.solve(C, rhs)
    ssr = y @ y - sol @ rhs
    s2e = ssr / (n - p)
    sign, logdetC = np.linalg.slogdet(C)
    return (n - p) * np.log(s2e) - q * np.log(a_off) - q * np.log(a_def) + logdetC


def fit_reml(X, Z, y):
    res = minimize(neg2_reml, x0=np.log([5.0, 5.0]), args=(X, Z, y), method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-4})
    a_off, a_def = np.exp(res.x)
    b, u = solve_mme(X, Z, y, a_off, a_def)
    W = np.hstack([X, Z]); sol = np.r_[b, u - 0]
    resid = y - X @ b - Z @ u
    s2e = resid @ resid / (len(y) - X.shape[1])
    return dict(a_off=a_off, a_def=a_def, s2e=s2e, s2_off=s2e / a_off, s2_def=s2e / a_def,
                b=b, u=u)


def solve_adaptive(X, Z, y, a_off, a_def, b, n0, w=None, z_prior=None):
    """Like solve_mme with fixed effects known, except the first two fixed effects
    (intercept = scoring baseline, home court) are re-estimated from these games, shrunk toward
    their training values b[:2] with the weight of n0 team-game rows. Other fixed effects
    (back-to-backs, injuries) stay at their training values."""
    n = len(y); w = np.ones(n) if w is None else w
    q = Z.shape[1] // 2
    A = np.r_[np.full(q, a_off), np.full(q, a_def)]
    yy = y - X[:, 2:] @ b[2:]
    if z_prior is not None: yy = yy - Z @ z_prior
    W = np.hstack([X[:, :2], Z])
    C = (W.T * w) @ W
    C[:2, :2] += np.eye(2) * n0
    C[2:, 2:] += np.diag(A)
    rhs = (W.T * w) @ yy
    rhs[:2] += n0 * b[:2]
    sol = np.linalg.solve(C, rhs)
    bb = b.copy(); bb[:2] = sol[:2]
    return bb, sol[2:] + (0 if z_prior is None else z_prior)


# ---------------------------------------------------------------- walk-forward season
def walk_forward(G, prev_O, prev_D, fit, rho_O, rho_D, half_life, adapt_n0=None, today_suffix=None):
    """Predict each game of one season using only earlier games of that season,
    shrinking toward rho * last season's effects. adapt_n0: if set, the scoring baseline and
    home-court effect are re-estimated each game day from this season's games so far."""
    G = G.sort_values("date").reset_index(drop=True)
    teams = sorted(set(G.home) | set(G.away))
    t_idx = {t: i for i, t in enumerate(teams)}; q = len(teams)
    prior = np.r_[[rho_O * prev_O.get(t, 0.0) for t in teams],
                  [rho_D * prev_D.get(t, 0.0) for t in teams]]
    b = fit["b"]
    L_all = long_rows(G)
    L_today = L_all
    if today_suffix:      # predict today's games with an alternate (earlier) injury snapshot
        G2 = G.copy()
        for c in ("home_miss_off", "home_miss_def", "away_miss_off", "away_miss_def"):
            G2[c] = G2[c + today_suffix]
        L_today = long_rows(G2)
    preds = []
    for d in sorted(G.date.unique()):
        past = L_all[L_all.date < d]
        if len(past):
            Z = np.zeros((len(past), 2 * q)); r = np.arange(len(past))
            Z[r, past.off.map(t_idx).values] = 1
            Z[r, q + past["def"].map(t_idx).values] = 1
            X = xmat(past)
            age = (d - past.date).dt.days.values
            w = 0.5 ** (age / half_life) if half_life else None
            if adapt_n0 is None:
                _, u = solve_mme(X, Z, past.pts.values.astype(float), fit["a_off"], fit["a_def"],
                                 w=w, z_prior=prior, fixed=b)
            else:
                b, u = solve_adaptive(X, Z, past.pts.values.astype(float), fit["a_off"], fit["a_def"],
                                      fit["b"], adapt_n0, w=w, z_prior=prior)
        else:
            u = prior
        O, D = u[:q], u[q:]
        today = L_today[L_today.date == d]
        xb = xmat(today) @ b
        pts = {(gid, ih): v for gid, ih, v in zip(today.gid, today.home, xb)}
        for _, g in G[G.date == d].iterrows():
            h, a = t_idx[g.home], t_idx[g.away]
            ph = pts[(g.name, 1)] + O[h] + D[a]
            pa = pts[(g.name, 0)] + O[a] + D[h]
            preds.append((g.name, ph - pa, ph + pa, b[0], b[1]))
    P = pd.DataFrame(preds, columns=["i", "pred_margin", "pred_total", "cur_intercept", "cur_home"]).set_index("i")
    return G.join(P)


# ---------------------------------------------------------------- betting evaluation
def evaluate(P, thresholds=(0, 1, 2, 3, 4, 5, 6)):
    P = P.copy()
    P["margin"] = P.home_pts - P.away_pts
    P["tot"] = P.home_pts + P.away_pts
    out = {}
    # spread: home covers if margin + spread > 0. Model edge = pred_margin + spread
    P["sp_edge"] = P.pred_margin + P.spread
    P["sp_res"] = np.sign(P.margin + P.spread) * np.sign(P.sp_edge)    # +1 win, -1 loss, 0 push
    P["ou_edge"] = P.pred_total - P.total
    P["ou_res"] = np.sign(P.tot - P.total) * np.sign(P.ou_edge)
    for mkt, e, r in [("spread", "sp_edge", "sp_res"), ("total", "ou_edge", "ou_res")]:
        rows = []
        for t in thresholds:
            s = P[P[e].abs() >= max(t, 1e-9)]
            wins, losses, pushes = (s[r] > 0).sum(), (s[r] < 0).sum(), (s[r] == 0).sum()
            n = wins + losses
            profit = wins * JUICE_WIN - losses
            rows.append(dict(threshold=t, bets=int(n), wins=int(wins), losses=int(losses),
                             pushes=int(pushes), win_pct=round(wins / n, 4) if n else None,
                             units=round(profit, 2), roi=round(profit / n, 4) if n else None))
        out[mkt] = rows
    out["accuracy"] = dict(
        model_margin_mae=float((P.pred_margin - P.margin).abs().mean()),
        line_margin_mae=float((-P.spread - P.margin).abs().mean()),
        model_total_mae=float((P.pred_total - P.tot).abs().mean()),
        line_total_mae=float((P.total - P.tot).abs().mean()))
    return out, P


# ---------------------------------------------------------------- driver
def run(df, train_seasons, test_season, halflives=(None, 60, 30, 15), adapt_grid=(None,), today_suffix=None):
    df = df.copy(); df["date"] = pd.to_datetime(df.date)
    df = pd.concat([add_rest(df[df.season == s]) for s in sorted(df.season.unique())],
                   ignore_index=True)
    tr = df[df.season.isin(train_seasons)].reset_index(drop=True)
    L = long_rows(tr)
    tbs = {s: sorted(set(tr[tr.season == s].home) | set(tr[tr.season == s].away)) for s in train_seasons}
    X, Z, keys = design(L, tbs)
    fit = fit_reml(X, Z, L.pts.values.astype(float))
    q = len(keys)
    O = {k: fit["u"][i] for i, k in enumerate(keys)}
    D = {k: fit["u"][q + i] for i, k in enumerate(keys)}
    # carryover rho: regress season s effects on season s-1 effects (consecutive seasons only)
    pairs_O, pairs_D = [], []
    ss = sorted(train_seasons)
    for s0, s1 in zip(ss, ss[1:]):
        if s1 - s0 != 1: continue
        for t in tbs[s1]:
            if (s0, t) in O:
                pairs_O.append((O[(s0, t)], O[(s1, t)])); pairs_D.append((D[(s0, t)], D[(s1, t)]))
    def slope(p):
        p = np.array(p); return float(p[:, 0] @ p[:, 1] / (p[:, 0] @ p[:, 0]))
    rho_O, rho_D = slope(pairs_O), slope(pairs_D)
    # tune half-life on the last training season (walk-forward, frozen components)
    val_s = ss[-1]; prev_s = ss[-2]
    eff = lambda dct, s: {t: v for (ss_, t), v in dct.items() if ss_ == s}
    tune = {}
    adaptive = adapt_grid != (None,)
    for hl in halflives:
        for n0 in adapt_grid:
            Pv = walk_forward(df[df.season == val_s], eff(O, prev_s), eff(D, prev_s), fit, rho_O, rho_D, hl, n0)
            mse_m = ((Pv.pred_margin - (Pv.home_pts - Pv.away_pts)) ** 2).mean()
            mse_t = ((Pv.pred_total - (Pv.home_pts + Pv.away_pts)) ** 2).mean()
            # original model: tuned on margins only; adaptive: on margins + totals
            tune[f"hl={hl}, n0={n0}"] = float((mse_m + mse_t) ** .5 if adaptive else mse_m ** .5)
    best_hl, best_n0 = min(((h, n) for h in halflives for n in adapt_grid), key=lambda k: tune[f"hl={k[0]}, n0={k[1]}"])
    # TEST: one pass on the held-out season
    Pt = walk_forward(df[df.season == test_season], eff(O, val_s), eff(D, val_s), fit, rho_O, rho_D, best_hl, best_n0,
                      today_suffix)
    res, Pt = evaluate(Pt)
    if "open_spread" in Pt:                    # also bet at the opening number
        Po = Pt.drop(columns=["spread", "total"]).rename(
            columns={"open_spread": "spread", "open_total": "total"})
        res_open, Po = evaluate(Po)
        res = {"close": res, "open": res_open}
        Pt["sp_res_open"], Pt["ou_res_open"] = Po.sp_res.values, Po.ou_res.values
    summary = dict(train_seasons=list(train_seasons), test_season=test_season,
                   fixed_effects=dict(zip(["intercept", "home", "b2b_offense", "b2b_defense", "missing_offense", "missing_opp_defense"],
                                          np.round(fit["b"], 3).tolist())),
                   sd_offense=fit["s2_off"] ** .5, sd_defense=fit["s2_def"] ** .5,
                   sd_residual=fit["s2e"] ** .5, rho_offense=rho_O, rho_defense=rho_D,
                   tuning_rmse_on_validation=tune, chosen_halflife=best_hl, chosen_adapt_n0=best_n0, test=res)
    return summary, Pt


if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1])
    train = [int(s) for s in sys.argv[2].split(",")]
    test = int(sys.argv[3])
    summary, P = run(df, train, test)
    print(json.dumps(summary, indent=2, default=float))
    P.to_csv(sys.argv[4] if len(sys.argv) > 4 else "test_predictions.csv", index=False)
