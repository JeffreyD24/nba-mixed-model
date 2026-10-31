"""
Models 2 and 3 for the NBA mixed-model project, built to sit beside Model 1 (nba_mixed_model.py).

Model 2 - player-based team strength
  pts_ij = mu + home + b2b_i + b2b_j
           + b_off * S_off_i + b_def * S_def_j                  (projected lineups x last season's EPM)
           + sum_p w_ip * po_p + sum_q w_jq * pd_q               (player-season deviations, random)
           + O_i + D_j + e                                       (team residuals, random, carried over)
  w = projected minutes / 48 from the official injury report and recent minutes (build_lineups.py).

Model 3 - pace x efficiency
  pace_g  = mu_p + b2b_h + b2b_a + P_home + P_away + sum refs R_r + e          (possessions per 48 min)
  eff_ij  = mu_e + home + b2b_i + b2b_j + miss_off_i + miss_def_j + O_i + D_j + sum refs F_r + e   (pts/100)
  pts_ij  = pace * eff_ij / 100 * (average game length / 48)
  Referee crews are announced the morning of the game, so they are used for closing-line bets only.

Both: variance components by REML on the training seasons (Henderson's equations), then a walk-forward
through the test season re-solving the random effects each game day from earlier games only, with recent
games weighted more (half-life chosen on the last training season, same grid as Model 1).
"""
import os, sys, pickle, json
import numpy as np, pandas as pd
import scipy.sparse as sp
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nba_mixed_model import add_rest, evaluate, run as run_model1

W = os.environ.get("NBA_V2_WORK", "work/")          # backtest data folder (load() only)
HALFLIVES = (None, 60, 30, 15)


# ============================================================ generic mixed-model machinery
def blocks_to_Z(n, blocks):
    """blocks: list of (row_idx, col_idx, val) for one random group with q columns -> dense n x q"""
    out = []
    for (r, c, v, q) in blocks:
        Z = np.zeros((n, q)); np.add.at(Z, (r, c), v); out.append(Z)
    return out


def spz(Z):
    return Z if sp.issparse(Z) else sp.csr_matrix(Z)


def solve(X, Zs, y, ratios, w=None, prior=None, b_fixed=None):
    """Henderson MME with several random groups. ratios[k] = s2_e / s2_k. prior: list of prior means per group.
    If b_fixed is given, fixed effects are held at those values and only random effects are solved.
    Z blocks may be dense or scipy.sparse."""
    n = len(y); w = np.ones(n) if w is None else w
    Z = sp.hstack([spz(Zk) for Zk in Zs]).tocsr()
    A = np.concatenate([np.full(Zk.shape[1], r) for Zk, r in zip(Zs, ratios)])
    pr = np.concatenate(prior) if prior is not None else np.zeros(Z.shape[1])
    yy = y - Z @ pr
    Wd = sp.diags(w)
    if b_fixed is not None:
        r = yy - X @ b_fixed
        C = (Z.T @ Wd @ Z).toarray() + np.diag(A)
        u = np.linalg.solve(C, Z.T @ (w * r))
        return b_fixed, u + pr
    Wm = sp.hstack([sp.csr_matrix(X), Z]).tocsr(); p = X.shape[1]
    C = (Wm.T @ Wd @ Wm).toarray(); C[p:, p:] += np.diag(A)
    sol = np.linalg.solve(C, Wm.T @ (w * yy))
    return sol[:p], sol[p:] + pr


def split_u(u, Zs):
    out, i = [], 0
    for Zk in Zs:
        out.append(u[i:i + Zk.shape[1]]); i += Zk.shape[1]
    return out


def fit_reml(X, Zs, y, x0=None, maxfev=300, reml_rows=None):
    """REML variance ratios (optionally from a subset of rows, to save time), then fixed and random
    effects solved on all rows with those ratios."""
    X_all, Zs_all, y_all = X, Zs, y
    if reml_rows is not None:
        X, y = X[reml_rows], y[reml_rows]
        Zs = [spz(Zk)[reml_rows] for Zk in Zs]
        keep = [np.asarray(abs(Zk).sum(axis=0)).ravel() > 0 for Zk in Zs]     # drop columns with no data
        Zs = [Zk[:, k] for Zk, k in zip(Zs, keep)]
    n, p = X.shape
    Wm = sp.hstack([sp.csr_matrix(X)] + [spz(Zk) for Zk in Zs]).tocsr()
    WtW = (Wm.T @ Wm).toarray(); Wty = Wm.T @ y; yty = y @ y
    qs = [Zk.shape[1] for Zk in Zs]

    def f(log_a):
        a = np.exp(log_a)
        C = WtW.copy()
        C[p:, p:] += np.diag(np.concatenate([np.full(q, ak) for q, ak in zip(qs, a)]))
        try:
            L = np.linalg.cholesky(C)
        except np.linalg.LinAlgError:
            return 1e12
        sol = np.linalg.solve(L.T, np.linalg.solve(L, Wty))
        s2e = (yty - sol @ Wty) / (n - p)
        return (n - p) * np.log(s2e) - sum(q * la for q, la in zip(qs, log_a)) + 2 * np.log(np.diag(L)).sum()

    x0 = np.log(np.full(len(Zs), 5.0)) if x0 is None else np.asarray(x0, float)
    res = minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-3, "maxfev": maxfev})
    ratios = np.exp(res.x)
    X, Zs, y = X_all, Zs_all, y_all
    n, p = X.shape
    b, u = solve(X, Zs, y, ratios)
    resid = y - X @ b - sp.hstack([spz(Zk) for Zk in Zs]).tocsr() @ u
    s2e = resid @ resid / (n - p)
    return dict(ratios=ratios, b=b, u=split_u(u, Zs), s2e=s2e, s2=[s2e / r for r in ratios], reml=res.fun,
                converged=bool(res.success))


def carryover(eff_by_key, seasons):
    """slope of season s effect on season s-1 effect for the same team, consecutive seasons only"""
    pairs = []
    for s0, s1 in zip(seasons, seasons[1:]):
        if s1 - s0 != 1: continue
        for (s, t), v in eff_by_key.items():
            if s == s1 and (s0, t) in eff_by_key: pairs.append((eff_by_key[(s0, t)], v))
    p = np.array(pairs)
    return float(p[:, 0] @ p[:, 1] / (p[:, 0] @ p[:, 0])) if len(p) else 0.0


# ============================================================ data
def load():
    g = pd.read_csv(W + "games_v2.csv", parse_dates=["date"])
    off = pd.read_csv(W + "officials.csv", parse_dates=["date"])[["date", "home", "away", "officials"]]
    g = g.merge(off, on=["date", "home", "away"], how="left")
    g["officials"] = g.officials.fillna("")
    g = pd.concat([add_rest(g[g.season == s]) for s in sorted(g.season.unique())], ignore_index=True)
    lu = pickle.load(open(W + "lineups.pkl", "rb"))
    # lineups were keyed by the row index of games_v2.csv; re-key by (date, home, away)
    g0 = pd.read_csv(W + "games_v2.csv", parse_dates=["date"])
    pos = {(r.date, r.home, r.away): i for i, r in zip(g0.index, g0.itertuples())}
    g["lu_key"] = [pos[(r.date, r.home, r.away)] for r in g.itertuples()]
    return g, lu


def long_rows(G, kind_today=None):
    """two rows per game (scoring team vs defending team) with Model 1's injury features"""
    rows = []
    for r in G.itertuples():
        for side, opp in (("home", "away"), ("away", "home")):
            rows.append(dict(gid=r.Index, date=r.date, season=r.season, off=getattr(r, side), dfn=getattr(r, opp),
                             home=int(side == "home"), b2b_off=getattr(r, f"b2b_{side}"), b2b_def=getattr(r, f"b2b_{opp}"),
                             pts=getattr(r, f"{side}_pts"), lu_key=r.lu_key, side=side, opp=opp))
    return pd.DataFrame(rows)


# ============================================================ MODEL 2: player-based
class PlayerModel:
    name = "Model 2 (player-based)"

    def __init__(self, G, lu):
        self.G, self.lu = G, lu

    def rows(self, G, kind):
        L = long_rows(G)
        L["s_off"] = [self.lu[(k, s, kind)]["s_off"] for k, s in zip(L.lu_key, L.side)]
        L["s_def"] = [self.lu[(k, o, kind)]["s_def"] for k, o in zip(L.lu_key, L.opp)]
        return L

    @staticmethod
    def X(L):
        return np.column_stack([np.ones(len(L)), L.home, L.b2b_off, L.b2b_def, L.s_off, L.s_def]).astype(float)

    def player_Z(self, L, kind, pidx, q):
        r_o, c_o, v_o, r_d, c_d, v_d = [], [], [], [], [], []
        for i, (k, s, o, ss) in enumerate(zip(L.lu_key, L.side, L.opp, L.season)):
            a = self.lu[(k, s, kind)]; b = self.lu[(k, o, kind)]
            for p, w in zip(a["pids"], a["w"]):
                j = pidx.get((ss, p))
                if j is not None: r_o.append(i); c_o.append(j); v_o.append(w)
            for p, w in zip(b["pids"], b["w"]):
                j = pidx.get((ss, p))
                if j is not None: r_d.append(i); c_d.append(j); v_d.append(w)
        n = len(L)
        Zo = sp.csr_matrix((v_o, (r_o, c_o)), shape=(n, q))
        Zd = sp.csr_matrix((v_d, (r_d, c_d)), shape=(n, q))
        return Zo, Zd

    @staticmethod
    def team_Z(L, tidx, q):
        n = len(L); r = np.arange(n); one = np.ones(n)
        Zo = sp.csr_matrix((one, (r, [tidx[(s, t)] for s, t in zip(L.season, L.off)])), shape=(n, q))
        Zd = sp.csr_matrix((one, (r, [tidx[(s, t)] for s, t in zip(L.season, L.dfn)])), shape=(n, q))
        return Zo, Zd

    def fit(self, train):
        G = self.G[self.G.season.isin(train)].reset_index(drop=True)
        L = self.rows(G, "pretip")
        pkeys = sorted({(s, p) for k, s0, ss in zip(L.lu_key, L.side, L.season) for p in self.lu[(k, s0, "pretip")]["pids"]
                        for s in [ss]})
        pidx = {k: i for i, k in enumerate(pkeys)}
        tkeys = sorted(set(zip(L.season, L.off)))
        tidx = {k: i for i, k in enumerate(tkeys)}
        Zpo, Zpd = self.player_Z(L, "pretip", pidx, len(pkeys))
        Zto, Ztd = self.team_Z(L, tidx, len(tkeys))
        X = self.X(L); y = L.pts.values.astype(float)
        print(f"  {self.name}: REML on {len(L)} rows, {len(pkeys)} player-seasons, {len(tkeys)} team-seasons", flush=True)
        recent = L.season.isin(sorted(train)[-2:]).values         # variance components from the last 2 seasons
        f = fit_reml(X, [Zpo, Zpd, Zto, Ztd], y, x0=np.log([40.0, 40.0, 10.0, 10.0]), maxfev=200, reml_rows=recent)
        uO = dict(zip(tkeys, f["u"][2])); uD = dict(zip(tkeys, f["u"][3]))
        ss = sorted(train)
        self.f, self.train = f, train
        self.rho_O, self.rho_D = carryover(uO, ss), carryover(uD, ss)
        self.uO, self.uD = uO, uD
        names = ["intercept", "home", "b2b_offense", "b2b_defense", "lineup_offense_epm", "opp_lineup_defense_epm"]
        self.summary = dict(fixed_effects=dict(zip(names, np.round(f["b"], 3).tolist())),
                            sd_player_off=f["s2"][0] ** .5, sd_player_def=f["s2"][1] ** .5,
                            sd_team_off=f["s2"][2] ** .5, sd_team_def=f["s2"][3] ** .5, sd_residual=f["s2e"] ** .5,
                            rho_team_off=self.rho_O, rho_team_def=self.rho_D, reml_converged=f["converged"])
        print("  ", json.dumps(self.summary, default=float), flush=True)
        return self

    def walk(self, season, half_life, kind_today="pretip", use_refs=True):
        G = self.G[self.G.season == season].sort_values("date").reset_index(drop=True)
        Lp = self.rows(G, "pretip")                         # past games: best pre-game info
        Lt = self.rows(G, kind_today)                       # today's games: snapshot being bet against
        pkeys = sorted({(season, p) for k in G.lu_key for s in ("home", "away") for kind in ("pretip", kind_today)
                        for p in self.lu[(k, s, kind)]["pids"]})
        pidx = {k: i for i, k in enumerate(pkeys)}; qp = len(pkeys)
        teams = sorted(set(G.home) | set(G.away)); tidx = {(season, t): i for i, t in enumerate(teams)}; qt = len(teams)
        Zpo_p, Zpd_p = self.player_Z(Lp, "pretip", pidx, qp); Zto_p, Ztd_p = self.team_Z(Lp, tidx, qt)
        Zpo_t, Zpd_t = self.player_Z(Lt, kind_today, pidx, qp); Zto_t, Ztd_t = self.team_Z(Lt, tidx, qt)
        prior = [np.zeros(qp), np.zeros(qp),
                 np.array([self.rho_O * self.uO.get((season - 1, t), 0.0) for t in teams]),
                 np.array([self.rho_D * self.uD.get((season - 1, t), 0.0) for t in teams])]
        b = self.f["b"]; Xp = self.X(Lp); Xt = self.X(Lt); yp = Lp.pts.values.astype(float)
        out = np.zeros(len(Lt))
        for d in sorted(G.date.unique()):
            m = (Lp.date < d).values
            if m.any():
                age = (d - Lp.date[m]).dt.days.values
                w = 0.5 ** (age / half_life) if half_life else None
                _, u = solve(Xp[m], [Zpo_p[m], Zpd_p[m], Zto_p[m], Ztd_p[m]], yp[m], self.f["ratios"], w=w, prior=prior, b_fixed=b)
                po, pd_, O, D = split_u(u, [Zpo_p, Zpd_p, Zto_p, Ztd_p])
            else:
                po, pd_, O, D = prior
            t = (Lt.date == d).values
            out[t] = Xt[t] @ b + Zpo_t[t] @ po + Zpd_t[t] @ pd_ + Zto_t[t] @ O + Ztd_t[t] @ D
        Lt["pred"] = out
        return to_games(G, Lt)


def to_games(G, L):
    h = L[L.side == "home"].set_index("gid").pred; a = L[L.side == "away"].set_index("gid").pred
    G = G.copy()
    G["pred_home_pts"] = h.reindex(G.index).values; G["pred_away_pts"] = a.reindex(G.index).values
    G["pred_margin"] = G.pred_home_pts - G.pred_away_pts; G["pred_total"] = G.pred_home_pts + G.pred_away_pts
    return G


# ============================================================ MODEL 3: pace x efficiency
class PaceModel:
    name = "Model 3 (pace x efficiency)"

    def __init__(self, G, lu=None):
        self.G = G

    @staticmethod
    def refs(G):
        return [[x for x in s.split("|") if x] for s in G.officials]

    def fit(self, train):
        G = self.G[self.G.season.isin(train)].reset_index(drop=True)
        self.otf = float((G.game_min / 240).mean())          # overtime factor
        tkeys = sorted(set(zip(G.season, G.home)) | set(zip(G.season, G.away))); tidx = {k: i for i, k in enumerate(tkeys)}
        rkeys = sorted({r for rs in self.refs(self.G) for r in rs}); ridx = {k: i for i, k in enumerate(rkeys)}
        self.tkeys, self.rkeys, self.ridx = tkeys, rkeys, ridx
        # ---- pace (one row per game)
        n = len(G); Zt = np.zeros((n, len(tkeys))); r = np.arange(n)
        np.add.at(Zt, (r, [tidx[(s, t)] for s, t in zip(G.season, G.home)]), 1)
        np.add.at(Zt, (r, [tidx[(s, t)] for s, t in zip(G.season, G.away)]), 1)
        Zr = self.ref_Z(G, ridx)
        Xp = np.column_stack([np.ones(n), G.b2b_home, G.b2b_away]).astype(float)
        print(f"  {self.name}: pace REML on {n} games, {len(rkeys)} referees", flush=True)
        fp = fit_reml(Xp, [Zt, Zr], G.pace48.values.astype(float), x0=np.log([5.0, 20.0]))
        # ---- efficiency (two rows per game), points per 100 possessions
        L = self.eff_rows(G, "")
        Zo = np.zeros((len(L), len(tkeys))); Zd = np.zeros((len(L), len(tkeys))); rr = np.arange(len(L))
        Zo[rr, [tidx[(s, t)] for s, t in zip(L.season, L.off)]] = 1
        Zd[rr, [tidx[(s, t)] for s, t in zip(L.season, L.dfn)]] = 1
        Zr2 = self.ref_Z(G, ridx)[L.gid.values]
        fe = fit_reml(self.eff_X(L), [Zo, Zd, Zr2], L.eff.values.astype(float), x0=np.log([5.0, 5.0, 20.0]))
        self.fp, self.fe = fp, fe
        ss = sorted(train)
        self.uP = dict(zip(tkeys, fp["u"][0])); self.uO = dict(zip(tkeys, fe["u"][0])); self.uD = dict(zip(tkeys, fe["u"][1]))
        self.rP = dict(zip(rkeys, fp["u"][1])); self.rE = dict(zip(rkeys, fe["u"][2]))
        self.rho_P, self.rho_O, self.rho_D = carryover(self.uP, ss), carryover(self.uO, ss), carryover(self.uD, ss)
        top = sorted(rkeys, key=lambda k: -abs(self.ref_total_effect(k)))[:5]
        self.summary = dict(
            pace_fixed=dict(zip(["intercept", "b2b_home", "b2b_away"], np.round(fp["b"], 3).tolist())),
            sd_team_pace=fp["s2"][0] ** .5, sd_ref_pace=fp["s2"][1] ** .5, sd_pace_residual=fp["s2e"] ** .5,
            eff_fixed=dict(zip(["intercept", "home", "b2b_offense", "b2b_defense", "missing_offense", "missing_opp_defense"],
                               np.round(fe["b"], 3).tolist())),
            sd_team_off_eff=fe["s2"][0] ** .5, sd_team_def_eff=fe["s2"][1] ** .5, sd_ref_eff=fe["s2"][2] ** .5,
            sd_eff_residual=fe["s2e"] ** .5, rho_pace=self.rho_P, rho_off=self.rho_O, rho_def=self.rho_D,
            overtime_factor=self.otf, reml_converged=[fp["converged"], fe["converged"]],
            biggest_referee_effects_on_total=[(k, round(self.ref_total_effect(k), 2)) for k in top])
        print("  ", json.dumps(self.summary, default=float), flush=True)
        return self

    def ref_total_effect(self, k):
        """approximate effect of one referee on the game total, in points"""
        pace = self.fp["b"][0]; eff = self.fe["b"][0] + self.fe["b"][1] / 2
        return (self.rP.get(k, 0) * 2 * eff / 100 + pace * 2 * self.rE.get(k, 0) / 100) * self.otf

    def ref_Z(self, G, ridx):
        Z = np.zeros((len(G), len(ridx)))
        for i, rs in enumerate(self.refs(G)):
            for k in rs:
                if k in ridx: Z[i, ridx[k]] += 1
        return Z

    @staticmethod
    def eff_rows(G, suffix):
        rows = []
        for r in G.itertuples():
            poss = r.pace48 * r.game_min / 240
            for side, opp in (("home", "away"), ("away", "home")):
                rows.append(dict(gid=r.Index, date=r.date, season=r.season, off=getattr(r, side), dfn=getattr(r, opp),
                                 home=int(side == "home"), b2b_off=getattr(r, f"b2b_{side}"), b2b_def=getattr(r, f"b2b_{opp}"),
                                 miss_off=getattr(r, f"{side}_miss_off{suffix}"), miss_def=getattr(r, f"{opp}_miss_def{suffix}"),
                                 eff=100 * getattr(r, f"{side}_pts") / poss, side=side))
        return pd.DataFrame(rows)

    @staticmethod
    def eff_X(L):
        return np.column_stack([np.ones(len(L)), L.home, L.b2b_off, L.b2b_def, L.miss_off, L.miss_def]).astype(float)

    def walk(self, season, half_life, kind_today="pretip", use_refs=True):
        G = self.G[self.G.season == season].sort_values("date").reset_index(drop=True)
        suf = "_open" if kind_today == "open" else ""
        teams = sorted(set(G.home) | set(G.away)); tidx = {t: i for i, t in enumerate(teams)}; q = len(teams)
        n = len(G); r = np.arange(n)
        Zt = np.zeros((n, q)); np.add.at(Zt, (r, G.home.map(tidx).values), 1); np.add.at(Zt, (r, G.away.map(tidx).values), 1)
        Zr = self.ref_Z(G, self.ridx)
        Xp = np.column_stack([np.ones(n), G.b2b_home, G.b2b_away]).astype(float)
        Lp = self.eff_rows(G, ""); Lt = self.eff_rows(G, suf)
        Zo = np.zeros((len(Lp), q)); Zd = np.zeros((len(Lp), q)); rr = np.arange(len(Lp))
        Zo[rr, Lp.off.map(tidx).values] = 1; Zd[rr, Lp.dfn.map(tidx).values] = 1
        Zr2 = Zr[Lp.gid.values]
        Xe_p, Xe_t = self.eff_X(Lp), self.eff_X(Lt)
        prP = np.array([self.rho_P * self.uP.get((season - 1, t), 0.0) for t in teams])
        prO = np.array([self.rho_O * self.uO.get((season - 1, t), 0.0) for t in teams])
        prD = np.array([self.rho_D * self.uD.get((season - 1, t), 0.0) for t in teams])
        prRP = np.array([self.rP.get(k, 0.0) for k in self.rkeys]); prRE = np.array([self.rE.get(k, 0.0) for k in self.rkeys])
        bp, be = self.fp["b"], self.fe["b"]
        pace = np.zeros(n); eff = np.zeros(len(Lt))
        for d in sorted(G.date.unique()):
            # earlier games with usable box-score totals only (a missing stat line is skipped, not zero)
            m = ((G.date < d) & np.isfinite(G.pace48)).values
            me = ((Lp.date < d) & np.isfinite(Lp.eff) & np.isfinite(Lp.miss_off) & np.isfinite(Lp.miss_def)).values
            if m.any() and me.any():
                age = (d - G.date[m]).dt.days.values; w = 0.5 ** (age / half_life) if half_life else None
                _, u = solve(Xp[m], [Zt[m], Zr[m]], G.pace48.values[m], self.fp["ratios"], w=w, prior=[prP, prRP], b_fixed=bp)
                P_, RP = split_u(u, [Zt, Zr])
                age = (d - Lp.date[me]).dt.days.values; w = 0.5 ** (age / half_life) if half_life else None
                _, u = solve(Xe_p[me], [Zo[me], Zd[me], Zr2[me]], Lp.eff.values[me], self.fe["ratios"], w=w,
                             prior=[prO, prD, prRE], b_fixed=be)
                O, D, RE = split_u(u, [Zo, Zd, Zr2])
            else:
                P_, RP, O, D, RE = prP, prRP, prO, prD, prRE
            t = (G.date == d).values; te = (Lt.date == d).values
            refP = Zr[t] @ RP if use_refs else 0.0
            pace[t] = Xp[t] @ bp + Zt[t] @ P_ + refP
            refE = Zr2[(Lp.date == d).values] @ RE if use_refs else 0.0
            Zo_t = np.zeros((te.sum(), q)); Zd_t = np.zeros((te.sum(), q)); k = np.arange(te.sum())
            Zo_t[k, Lt.off[te].map(tidx).values] = 1; Zd_t[k, Lt.dfn[te].map(tidx).values] = 1
            eff[te] = Xe_t[te] @ be + Zo_t @ O + Zd_t @ D + refE
        Lt["eff_pred"] = eff
        Lt["pred"] = pace[Lt.gid.values] * eff / 100 * self.otf
        out = to_games(G, Lt)
        out["pred_pace"] = pace
        return out


# ============================================================ shared driver
def tune_and_test(M, train, test, kinds=("pretip", "open")):
    ss = sorted(train)
    val = ss[-1]
    tune = {}
    for hl in HALFLIVES:
        P = M.walk(val, hl)
        mse_m = ((P.pred_margin - (P.home_pts - P.away_pts)) ** 2).mean()
        mse_t = ((P.pred_total - (P.home_pts + P.away_pts)) ** 2).mean()
        tune[str(hl)] = float(mse_m + mse_t)
    best = min(HALFLIVES, key=lambda h: tune[str(h)])
    print(f"  half-life tuning on {val} (MSE margin + total): {tune} -> {best}", flush=True)
    P_close = M.walk(test, best, "pretip", use_refs=True)
    P_open = M.walk(test, best, "open", use_refs=False)
    return best, tune, P_close, P_open


def score(P_close, P_open):
    rc, Pc = evaluate(P_close)
    Po = P_open.drop(columns=["spread", "total"]).rename(columns={"open_spread": "spread", "open_total": "total"})
    Po = Po[Po.spread.notna() & Po.total.notna()]
    ro, Po = evaluate(Po)
    return {"close": rc, "open": ro}, Pc, Po


# ============================================================ saving fitted models for the live tracker
def _k(d):  return {f"{s}|{t}": float(v) for (s, t), v in d.items()}
def _uk(d): return {(int(k.split("|")[0]), k.split("|")[1]): v for k, v in d.items()}


def export_params(M, half_life):
    if isinstance(M, PlayerModel):
        return dict(model="player", half_life=half_life, ratios=M.f["ratios"].tolist(), b=M.f["b"].tolist(),
                    rho_O=M.rho_O, rho_D=M.rho_D, uO=_k(M.uO), uD=_k(M.uD), summary=M.summary, train=list(M.train))
    return dict(model="pace", half_life=half_life, otf=M.otf,
                fp=dict(ratios=M.fp["ratios"].tolist(), b=M.fp["b"].tolist()),
                fe=dict(ratios=M.fe["ratios"].tolist(), b=M.fe["b"].tolist()),
                rkeys=M.rkeys, rP=M.rP, rE=M.rE, uP=_k(M.uP), uO=_k(M.uO), uD=_k(M.uD),
                rho_P=M.rho_P, rho_O=M.rho_O, rho_D=M.rho_D, summary=M.summary)


def import_params(d, G, lu=None):
    if d["model"] == "player":
        M = PlayerModel(G, lu)
        M.f = dict(ratios=np.array(d["ratios"]), b=np.array(d["b"]))
        M.rho_O, M.rho_D, M.uO, M.uD = d["rho_O"], d["rho_D"], _uk(d["uO"]), _uk(d["uD"])
    else:
        M = PaceModel(G)
        M.otf = d["otf"]
        M.fp = dict(ratios=np.array(d["fp"]["ratios"]), b=np.array(d["fp"]["b"]))
        M.fe = dict(ratios=np.array(d["fe"]["ratios"]), b=np.array(d["fe"]["b"]))
        M.rkeys = d["rkeys"]; M.ridx = {k: i for i, k in enumerate(M.rkeys)}
        M.rP, M.rE = d["rP"], d["rE"]
        M.uP, M.uO, M.uD = _uk(d["uP"]), _uk(d["uO"]), _uk(d["uD"])
        M.rho_P, M.rho_O, M.rho_D = d["rho_P"], d["rho_O"], d["rho_D"]
    return M
