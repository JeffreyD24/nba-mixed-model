"""Why did the live totals model lose -52.8u at the CLOSE in 2024-25 (vs +6.5u and +8.3u in the other seasons) while winning
at the opener every season?  Splits the close-line bets by side, month, line move, model bias; checks the close data itself.
  python analysis/close_2025.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
src = open(os.path.join(W, "analysis", "validate_dk_2024_26.py")).read().split('print("games at DK lines:"')[0].split("W = os.path.abspath(sys.argv[1]); sys.argv = [\"x\", W]")[1]
exec(src)
G["month"] = pd.to_datetime(G.date).dt.month
def g_(e, r, mask):
    m = (e.abs() >= 3) & mask; rr = np.sign(e[m]) * r[m]; w, l = (rr > 0).sum(), (rr < 0).sum(); return f"{w + l:4d} {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+6.1f}u"
for s in SEAS:
    d = G[G.season == s]
    eo, ro = d.tot_model - d.open_tot, d.pts - d.open_tot
    ec, rc = d.tot_model - d.close_tot, d.pts - d.close_tot
    print(f"\n===== {s}  ({len(d)} games)")
    print(f"  league: actual total {d.pts.mean():.1f}, DK open {d.open_tot.mean():.1f}, DK close {d.close_tot.mean():.1f}, model {d.tot_model.mean():.1f}; "
          f"overs vs close {(d.pts > d.close_tot).mean():.1%}; avg move open->close {(d.close_tot - d.open_tot).mean():+.2f}, |move| {(d.close_tot - d.open_tot).abs().mean():.2f}")
    print(f"  model error: mean (model - actual) {(d.tot_model - d.pts).mean():+.2f}; close error {(d.close_tot - d.pts).mean():+.2f}; MAE model {np.abs(d.tot_model - d.pts).mean():.2f}, open {np.abs(d.open_tot - d.pts).mean():.2f}, close {np.abs(d.close_tot - d.pts).mean():.2f}")
    print(f"  at OPEN : all {g_(eo, ro, True)} | overs {g_(eo, ro, eo > 0)} | unders {g_(eo, ro, eo < 0)}")
    print(f"  at CLOSE: all {g_(ec, rc, True)} | overs {g_(ec, rc, ec > 0)} | unders {g_(ec, rc, ec < 0)}")
    mv = np.sign(ec) * (d.close_tot - d.open_tot)       # + = line moved toward our side after the open
    print(f"  close bets where the line had moved TOWARD us since open {g_(ec, rc, mv > 0)} | moved AWAY {g_(ec, rc, mv < 0)} | no move {g_(ec, rc, mv == 0)}")
    print("  close bets by month: " + " | ".join(f"{m}: {g_(ec, rc, d.month == m)}" for m in (10, 11, 12, 1, 2, 3, 4)))
    both = (eo.abs() >= 3) & (ec.abs() >= 3) & (np.sign(eo) == np.sign(ec))
    only_c = (eo.abs() < 3) & (ec.abs() >= 3)
    print(f"  close bets that were ALSO bets at the open {g_(ec, rc, both)} | close-only bets (no edge at open) {g_(ec, rc, only_c)}")
    print(f"  close bets by edge: 3-4 {g_(ec, rc, ec.abs() < 4)} | 4-6 {g_(ec, rc, (ec.abs() >= 4) & (ec.abs() < 6))} | 6+ {g_(ec, rc, ec.abs() >= 6)}")
