"""Exploratory follow-ups to step 2 (NOT pre-registered; for ideas only).
1) DK-specific deviation: DK residual minus Pinnacle residual (Pinnacle seen later, so this is partly timing)
2) Results by how early DK's first line was seen
3) Over vs under side of the pre-registered rule
"""
import numpy as np, pandas as pd
R = pd.read_csv("research/market_models/opener_residuals.csv")
def grade(S, under):
    line, close = S.dk_open_point, S.dk_close_point
    clv = np.where(under, line - close, close - line)
    win = np.where(under, S.final_total < line, S.final_total > line); push = S.final_total == line
    px = np.where(under, S.dk_open_under_px, S.dk_open_over_px); px = np.where(np.isnan(px), -110, px)
    u = np.where(push, 0, np.where(win, np.where(px > 0, px / 100, 100 / -px), -1.0))
    return dict(n=len(S), clv=round(clv.mean(), 2), units=round(u.sum(), 1), win=round(win[~push].mean(), 3))
for s in (2025, 2026):
    S = R[R.season == s].dropna(subset=["dk_resid", "pin_resid"])
    print(f"== {s}")
    rule = S[S.dk_resid.abs() >= 3]
    print(" prereg rule, unders:", grade(rule[rule.dk_resid > 0], True), " overs:", grade(rule[rule.dk_resid < 0], False))
    d = S.dk_resid - S.pin_resid
    for lab, m in [("DK off but Pinnacle agrees w/ model (|pin|<1.5)", (S.dk_resid.abs() >= 3) & (S.pin_resid.abs() < 1.5)),
                   ("both books off same way", (S.dk_resid.abs() >= 3) & (np.sign(S.pin_resid) == np.sign(S.dk_resid)) & (S.pin_resid.abs() >= 1.5)),
                   ("DK minus Pinnacle residual >=2", d.abs() >= 2)]:
        T = S[m]; ref = T.dk_resid if "minus" not in lab else d[m]
        print(f" {lab}:", grade(T, (ref > 0).to_numpy()))
    for lo, hi in [(0, 18), (18, 30), (30, 999)]:
        T = rule[(rule.dk_open_lead_h >= lo) & (rule.dk_open_lead_h < hi)]
        print(f" first seen {lo}-{hi}h before tip:", grade(T, (T.dk_resid > 0).to_numpy()))
