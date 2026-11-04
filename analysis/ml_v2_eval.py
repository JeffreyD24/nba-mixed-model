"""NBA moneyline v2, step 3: fit the final win-probability layer, the market blend gate, the EV bar, and (only with --lockbox) the lockbox.
Rules: research/MONEYLINE_V2_PREREG_2026-11-04.md.   python3 analysis/ml_v2_eval.py [--lockbox]"""
import os, sys, numpy as np, pandas as pd, statsmodels.api as sm
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *p: os.path.join(W, *p)
LOCK = "--lockbox" in sys.argv
G = pd.read_csv(J("analysis", "ml_v2_features.csv.gz"), parse_dates=["date"])
dec = lambda o: np.where(o > 0, 1 + o / 100, 1 + 100 / np.abs(o))
def nv(a, b): ia, ib = 1 / dec(a), 1 / dec(b); return ia / (ia + ib)
logit = lambda p: np.log(p / (1 - p)); sig = lambda x: 1 / (1 + np.exp(-x))
ll = lambda p, y: -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

# market probabilities: build = SBR close (sanity: book margin 0-10%, no price inside +-100); later seasons = DK opener and close
ok_sbr = (G.sbr_ml_h.abs() >= 100) & (G.sbr_ml_a.abs() >= 100)
over = 1 / dec(G.sbr_ml_h.fillna(-110)) + 1 / dec(G.sbr_ml_a.fillna(-110)); ok_sbr &= over.between(1.0, 1.10)
G["mkt_build"] = np.where(ok_sbr, nv(G.sbr_ml_h.fillna(-110), G.sbr_ml_a.fillna(-110)), np.nan)
G["mkt_open"] = nv(G.dk_o_h, G.dk_o_a); G["mkt_close"] = nv(G.dk_c_h, G.dk_c_a); G["mkt_pin"] = nv(G.pn_o_h, G.pn_o_a)
G["rest_d"] = G.rest_h - G.rest_a
SCHED = ["b2b_h", "b2b_a", "travel_h", "travel_a", "alt_home", "rest_d"]
G = G.dropna(subset=["rd_30", "rd_60", "rd_120"]).reset_index(drop=True)
build = G.split == "build"; choose = G.split == "choose"; lock = G.split == "lockbox"
L = []; say = lambda s="": (print(s), L.append(s))

def fit_predict(cols, train, test):
    X = sm.add_constant(G.loc[train, cols].astype(float)); m = sm.Logit(G.loc[train, "hw"], X).fit(disp=0)
    return m.predict(sm.add_constant(G.loc[test, cols].astype(float), has_constant="add")), m

def loso(cols):
    """build seasons: leave-one-season-out predictions; other seasons: fit on all build seasons."""
    p = pd.Series(np.nan, index=G.index)
    for s in G.loc[build, "season"].unique():
        te = build & (G.season == s); p[te] = fit_predict(cols, build & (G.season != s), te)[0]
    rest = ~build; p[rest], m = fit_predict(cols, build, rest); return p, m

say("# NBA moneyline v2 results"); say()
say("## Step A: choose tau for M1 on build seasons (leave-one-season-out log loss)")
best = None
for tau in (30, 60, 120):
    p, _ = loso([f"rd_{tau}"] + SCHED); l = ll(p[build], G.hw[build]); say(f"  tau {tau:>3}: log loss {l:.4f}")
    if best is None or l < best[1]: best = (tau, l)
TAU = best[0]; say(f"  -> tau = {TAU} days"); say()

MODELS = {"M1 win-prob mixed model": [f"rd_{TAU}"] + SCHED,
          "M2 M1 + availability": [f"rd_{TAU}"] + SCHED + ["mv_h", "mv_a"],
          "M3 Elo (MOV)": ["elo_diff"]}
for name, cols in MODELS.items():
    G[name], m = loso(cols)
    if name.startswith("M2"): say("M2 coefficients (all build seasons): " + ", ".join(f"{k} {v:+.3f}" for k, v in m.params.items()))
# M4 stack: logistic on the logits of M1-M3, fit on the build seasons' out-of-season predictions
for n in list(MODELS): G["lg_" + n[:2]] = logit(G[n])
G["M4 stack"], m4 = loso(["lg_M1", "lg_M2", "lg_M3"])
say("M4 stack weights: " + ", ".join(f"{k} {v:+.2f}" for k, v in m4.params.items())); say()
NAMES = list(MODELS) + ["M4 stack"]

def fit_w(p_model, p_mkt, y):
    off = logit(p_mkt); x = (logit(p_model) - off).to_frame("d")
    r = sm.GLM(y, x, family=sm.families.Binomial(), offset=off).fit(); return r.params["d"], r.bse["d"]

say("## Step B: market blend. w fit on build vs SBR close; gate on choose seasons vs the DraftKings opener")
say("| Model | log loss build (model / close) | w build | w choose (95% CI) vs DK open | log loss choose: blend / DK open / model | Gate |")
say("|---|---|---|---|---|---|")
GATE = {}
bm = build & G.mkt_build.notna(); cm = choose & G.mkt_open.notna()
for n in NAMES:
    wb, _ = fit_w(G.loc[bm, n], G.loc[bm, "mkt_build"], G.hw[bm])
    wc, se = fit_w(G.loc[cm, n], G.loc[cm, "mkt_open"], G.hw[cm])
    G["b_" + n] = sig(logit(G.mkt_open) + wb * (logit(G[n]) - logit(G.mkt_open)))
    lb, lo, lm = ll(G.loc[cm, "b_" + n], G.hw[cm]), ll(G.loc[cm, "mkt_open"], G.hw[cm]), ll(G.loc[cm, n], G.hw[cm])
    passed = (wc - 1.96 * se > 0) and (lb < lo); GATE[n] = (passed, wb, wc, se)
    say(f"| {n} | {ll(G.loc[bm, n], G.hw[bm]):.4f} / {ll(G.loc[bm, 'mkt_build'], G.hw[bm]):.4f} | {wb:.2f} | {wc:.2f} ({wc-1.96*se:.2f} to {wc+1.96*se:.2f}) "
        f"| {lb:.4f} / {lo:.4f} / {lm:.4f} | {'PASS' if passed else 'fail'} |")
say()

def bets(n, mask, bar):
    p = G.loc[mask, "b_" + n]; g = G[mask]
    dh, da = dec(g.dk_o_h), dec(g.dk_o_a); evh, eva = p * dh - 1, (1 - p) * da - 1; home = evh >= eva; ev = np.maximum(evh, eva)
    sel = ev >= bar; g = g[sel]; home = home[sel]
    win = np.where(home, g.hw == 1, g.hw == 0); price = np.where(home, g.dk_o_h, g.dk_o_a)
    u = np.where(win, dec(price) - 1, -1.0)
    clv = np.where(home, g.mkt_close - g.mkt_open, g.mkt_open - g.mkt_close) * 100
    pin = np.where(home, g.mkt_pin - g.mkt_open, g.mkt_open - g.mkt_pin)
    return pd.DataFrame(dict(season=g.season, u=u, clv=clv, win=win, home=home, price=price, pin_ok=pin >= 0))
def row(B, label):
    if B.empty: return f"| {label} | 0 | | | | |"
    per = B.groupby("season").agg(u=("u", "sum"), c=("clv", "mean"))
    seas = " ".join(f"{s % 100:02d}:{r.u:+.1f}u/{r.c:+.2f}" for s, r in per.iterrows())
    return f"| {label} | {len(B)} | {B.clv.mean():+.2f} | {B.u.sum():+.1f}u ({B.u.mean()*100:+.1f}%) | {B.win.mean()*100:.1f}% | {seas} |"

say("## Step C: bets at the DraftKings opener on the choose seasons (2021-22, 2022-23); CLV = no-vig win-% points, close minus open")
say("| Model, EV bar | Bets | CLV | Units | Win % | By season (units / CLV) |"); say("|---|---|---|---|---|---|")
CH = {}
for n in NAMES:
    for bar in (0.02, 0.03, 0.04, 0.06):
        B = bets(n, cm, bar); CH[(n, bar)] = B; say(row(B, f"{n}, EV {bar:.0%}+"))
say()
passing = [n for n in NAMES if GATE[n][0]]
if passing:
    # pre-registered choice: among passing models, the (model, bar) with the best mean CLV on the choose seasons, needing 100+ bets
    cand = [(CH[(n, b)].clv.mean(), n, b) for n in passing for b in (0.02, 0.03, 0.04, 0.06) if len(CH[(n, b)]) >= 100]
    _, CHOSEN, BAR = max(cand); say(f"**Chosen:** {CHOSEN} at EV {BAR:.0%}+ (best choose-season CLV among models passing the gate).")
else:
    CHOSEN = BAR = None; say("**No model passed the gate. Per the pre-registration the lockbox is not used to pick anything.**")
say()
say("## Secondary rows on the choose seasons (information only; filters were found on 2023-26)")
for n in NAMES:
    B = CH[(n, 0.04)]
    if B.empty: continue
    say(f"{n}, EV 4%+:"); say("| Filter | Bets | CLV | Units | Win % | By season |"); say("|---|---|---|---|---|---|")
    for lab, f in [("all", B.u == B.u), ("price +150 or shorter", B.price <= 150), ("away only", ~B.home), ("no home underdogs", ~(B.home & (B.price > 0))),
                   ("Pinnacle first price agrees", B.pin_ok), ("away, +150 or shorter", (~B.home) & (B.price <= 150))]:
        say(row(B[f], lab))
    say()

if LOCK:
    say("## Step D: LOCKBOX 2023-24..2025-26 (opened once)")
    lm_ = lock & G.mkt_open.notna()
    say("| Model, EV bar | Bets | CLV | Units | Win % | By season (units / CLV) |"); say("|---|---|---|---|---|---|")
    for n in NAMES:
        say(row(bets(n, lm_, BAR or 0.04), f"{n}, EV {(BAR or 0.04):.0%}+" + (" (CHOSEN)" if n == CHOSEN else "")))
    say(); say("Log loss on the lockbox: " + ", ".join(f"{n[:2]} model {ll(G.loc[lm_, n], G.hw[lm_]):.4f} / blend {ll(G.loc[lm_, 'b_'+n], G.hw[lm_]):.4f}" for n in NAMES)
            + f"; DK open {ll(G.loc[lm_, 'mkt_open'], G.hw[lm_]):.4f}, DK close {ll(G.loc[lm_, 'mkt_close'], G.hw[lm_]):.4f}")
    if CHOSEN:
        B = bets(CHOSEN, lm_, BAR); say(); say(f"{CHOSEN} lockbox filters (information only):")
        say("| Filter | Bets | CLV | Units | Win % | By season |"); say("|---|---|---|---|---|---|")
        for lab, f in [("all", B.u == B.u), ("price +150 or shorter", B.price <= 150), ("away only", ~B.home), ("Pinnacle first price agrees", B.pin_ok)]:
            say(row(B[f], lab))
open(J("analysis", "ml_v2_output" + ("_lockbox" if LOCK else "") + ".md"), "w").write("\n".join(L) + "\n")
