"""NBA tournament with injuries in Tier A (pre-registered: research/tournament/NBA_INJ_PREREG.md, commit 3241f3a).
  python research/tournament/nba_injury_tier_a.py WORKDIR choose    -> research/tournament/nba_inj_choose_output.txt
  python research/tournament/nba_injury_tier_a.py WORKDIR lockbox   -> research/tournament/nba_inj_lockbox_output.txt (only markets that pass)
Needs the _tmp Model 1 predictions (analysis/old_seasons_sbr.py predict; nba_tournament.py predict)."""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); MODE_INJ = sys.argv[2]
sys.argv = [sys.argv[0], W, "choose"]
sys.path.insert(0, os.path.join(W, "research", "tournament"))
import nba_tournament as nt

OUT = nt.OUT
INJ = {"spread": "inj_sp", "total": "inj_tot"}
_base_X = nt.stack_X
def stack_X_inj(D, mk, L):
    return np.column_stack([_base_X(D, mk, L), D[INJ[mk]].values])


def table():
    G = nt.table()
    M = pd.read_csv(os.path.join(W, "data", "external", "nba_box", "missed_value.csv"))
    M["date"] = pd.to_datetime(M.date)
    z = M.set_index(["date", "team"]).missed_value_z_prior
    z = z[~z.index.duplicated()]
    G["z_home"] = [z.get((d, t), np.nan) for d, t in zip(G.date, G.home)]
    G["z_away"] = [z.get((d, t), np.nan) for d, t in zip(G.date, G.away)]
    G["inj_sp"] = G.z_away - G.z_home; G["inj_tot"] = G.z_home + G.z_away
    return G


def fit(Dtr, mk, inj):
    L, _, y = nt.mk_xy(Dtr, mk)
    X = stack_X_inj(Dtr, mk, L) if inj else _base_X(Dtr, mk, L)
    ok = ~np.isnan(y) & ~np.isnan(X).any(1)
    b = np.linalg.lstsq(X[ok], y[ok], rcond=None)[0]
    return b, np.std(y[ok] - X[ok] @ b, ddof=1)


def edge(D, mk, inj, b):
    L, _, _ = nt.mk_xy(D, mk)
    return (stack_X_inj(D, mk, L) if inj else _base_X(D, mk, L)) @ b


def paired(D, mk, e6, e7, n=2000, seed=17):
    _, _, y = nt.mk_xy(D, mk)
    d = (y - e6) ** 2 - (y - e7) ** 2                    # positive = 7 closer to the result than 6
    s = pd.Series(d).groupby(D.date.values); sums, cnts = s.sum().values, s.size().values
    rng = np.random.default_rng(seed); k = len(sums)
    bs = np.array([(lambda i: sums[i].sum() / cnts[i].sum())(rng.integers(0, k, k)) for _ in range(n)])
    return float(d.mean()), float(np.percentile(bs, 5)), float(np.percentile(bs, 95))


def run(seasons_fit, seasons_test, label, out_name, markets=("spread", "total")):
    G = table(); lines = []
    def say(s): lines.append(s); print(s, flush=True)
    say(f"NBA tournament with injuries (missed last game, z_prior) - {label}. Pre-registered: NBA_INJ_PREREG.md")
    passed = []
    for mk in markets:
        base = G[(G[f"{mk}_trusted"] == 1) & G.z_home.notna() & G.z_away.notna()]
        tr, te = base[base.season.isin(seasons_fit)], base[base.season.isin(seasons_test)]
        dropped = int(((G[f"{mk}_trusted"] == 1) & G.season.isin(seasons_test) & (G.z_home.isna() | G.z_away.isna())).sum())
        say(f"\n== {mk.upper()}: fit {seasons_fit[0]}-{seasons_fit[-1]} ({len(tr)} games), test {seasons_test[0]}-{seasons_test[-1]} ({len(te)} games; "
            f"{dropped} test games dropped for a missing team row)")
        b6, sd6 = fit(tr, mk, False); b7, sd7 = fit(tr, mk, True)
        r = {}
        for name, inj, b, sd in (("6 stack", False, b6, sd6), ("7 stack + missed", True, b7, sd7)):
            sc = nt.score(te, mk, edge(te, mk, inj, b), sd); r[name] = sc
            ok = sc["lo"] > 0 and sc["clv"] > 0
            say(f"  {name:18s} dMSE {sc['dmse']:+.2f} [{sc['lo']:+.2f},{sc['hi']:+.2f}] P<0 {sc['p_neg']:.2f} | {sc['bets']} bets {sc['win']:.1%} "
                f"{sc['units']:+.1f}u CLV {sc['clv']:+.2f} | {'PASS' if ok else '-'}")
        say(f"  missed coefficient (fit seasons): {b7[-1]:+.3f} points per z  ({'home' if mk == 'spread' else 'total'}; "
            f"{'positive = healthier home side covers more' if mk == 'spread' else 'negative = fewer points when good players are out'})")
        d, lo, hi = paired(te, mk, edge(te, mk, False, b6), edge(te, mk, True, b7))
        say(f"  paired dMSE (7 - 6): {d:+.3f} [{lo:+.3f},{hi:+.3f}]")
        for s in seasons_test:
            x = te[te.season == s]
            if len(x):
                d_s = paired(x, mk, edge(x, mk, False, b6), edge(x, mk, True, b7), n=200)[0]
                s7 = nt.score(x, mk, edge(x, mk, True, b7), sd7, n_boot=100)
                say(f"     {s}: paired {d_s:+.3f}; 7: {s7['bets']} bets {s7['win']:.1%} {s7['units']:+.1f}u CLV {s7['clv']:+.2f}")
        verdict = lo > 0 and r["7 stack + missed"]["lo"] > 0 and r["7 stack + missed"]["clv"] > 0
        say(f"  VERDICT ({mk}): {'injury info ADDS to the stack' if verdict else 'not shown'}")
        if verdict: passed.append(mk)
    open(os.path.join(OUT, out_name), "w").write("\n".join(lines) + "\n")
    return passed


if __name__ == "__main__":
    if MODE_INJ == "choose":
        p = run(nt.BUILD, nt.CHOOSE, "CHOOSE 2019-2022 (verdict)", "nba_inj_choose_output.txt")
        open(os.path.join(OUT, "nba_inj_passed.txt"), "w").write(",".join(p))
    else:
        lf = os.path.join(OUT, "nba_inj_lockbox_output.txt"); assert not os.path.exists(lf), "already opened"
        p = [x for x in open(os.path.join(OUT, "nba_inj_passed.txt")).read().split(",") if x]
        if p: run(nt.BUILD + nt.CHOOSE, nt.LOCK, "LOCKBOX 2023-26, SECOND LOOK (see prereg rule 3)", "nba_inj_lockbox_output.txt", tuple(p))
        else: print("no market passed on CHOOSE: lockbox not run")
