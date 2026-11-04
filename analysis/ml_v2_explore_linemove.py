# EXPLORATORY (added after the pre-registered results): does the DK moneyline move from open to close toward the v2 models?
import sys, numpy as np, pandas as pd, statsmodels.api as sm
sys.argv=["x"]; src=open("analysis/ml_v2_eval.py").read().split('say("## Step B')[0]
__file__="/home/claude/nba-mixed-model/analysis/ml_v2_eval.py"; exec(src)
cm = choose & G.mkt_open.notna() & G.mkt_close.notna()
for n in NAMES:
    d = logit(G.loc[cm, n]) - logit(G.loc[cm, "mkt_open"]); mv = logit(G.loc[cm, "mkt_close"]) - logit(G.loc[cm, "mkt_open"])
    r = sm.OLS(mv, sm.add_constant(d)).fit(); print(f"{n}: line move toward model, slope {r.params.iloc[1]:+.3f} (t {r.tvalues.iloc[1]:+.1f}); corr model vs open {np.corrcoef(G.loc[cm,n],G.loc[cm,'mkt_open'])[0,1]:.3f}; sd of disagreement {d.std():.3f} logit")
# availability alone: does missing-value news move the line?
d = (G.loc[cm,"mv_h"]-G.loc[cm,"mv_a"]); mv = logit(G.loc[cm,"mkt_close"])-logit(G.loc[cm,"mkt_open"])
r = sm.OLS(mv, sm.add_constant(d)).fit(); print(f"availability diff vs line move: slope {r.params.iloc[1]:+.4f} (t {r.tvalues.iloc[1]:+.1f})")
