"""Rule audit part 2 (Nov 4, 2026): the line-movement and threshold rules for NBA totals, on the replay table saved by
analysis/rule_audit_injury_timing.py (_tmp/rule_audit_R8.csv; live totals number, morning-lock lag 1, DK 2023-26).
  (a) PASS when the line moved 0.5+ against since open / BET when it moved toward with 3+ left / OPTIONAL when unmoved,
      checked at several bet times (edge 3+ at the line at that time, 8 PM report)
  (b) size of the move against
  (c) edge threshold buckets at the opener (8 PM report and previous-game report)
  python analysis/rule_audit_line_rules.py WORKDIR -> analysis/rule_audit_line_rules_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
R = pd.read_csv(os.path.join(W, "_tmp", "rule_audit_R8.csv"))
R["tip_et"] = pd.to_datetime(R.tip, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
R["gd"] = pd.to_datetime(R.date)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def g(model, line, mask):
    e = model - line; m = mask & (e.abs() >= 3) & line.notna() & model.notna()
    r = np.sign(e[m]) * (R.act[m] - line[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
    by = []
    for s in (2024, 2025, 2026):
        rs = r[R.season[m] == s]; ws, ls = int((rs > 0).sum()), int((rs < 0).sum()); by.append(f"{ws * 100 / 110 - ls:+.1f}")
    return f"{w + l:5d} bets {w / max(w + l, 1):6.1%} {w * 100 / 110 - l:+7.1f}u ({(w * 100 / 110 - l) / max(w + l, 1) * 100:+5.1f}/100; by season {', '.join(by)})"

say("(a) Line moved since DraftKings' open, checked at each bet time; edge 3+ at the line then; 8 PM report")
for col, lab, hrs in [("l-2.0", "10 PM night before", -2.0), ("l9pm", "9 PM night before", -3.0), ("l0.0", "midnight", 0.0),
                      ("l9am", "9 AM game day", 9.0), ("l12.0", "noon", 12.0), ("l15.0", "3 PM", 15.0), ("l18.0", "6 PM (tips 7+ only)", 18.0)]:
    pre = R.tip_et > R.gd + pd.Timedelta(hours=hrs + 0.5)
    mv = R[col] - R.open_total; e = R.tot_model - R[col]
    ag = (mv.abs() >= 0.5) & (np.sign(mv) != np.sign(e)); tw = (mv.abs() >= 0.5) & ~ag; un = mv.abs() < 0.5
    say(f"  {lab}")
    say(f"    moved AGAINST 0.5+ : {g(R.tot_model, R[col], pre & ag)}")
    say(f"    unmoved            : {g(R.tot_model, R[col], pre & un)}")
    say(f"    moved TOWARD 0.5+  : {g(R.tot_model, R[col], pre & tw)}")

say("\n(b) size of the move against (9 AM game day line)")
mv = R.l9am - R.open_total; e = R.tot_model - R.l9am; ag = np.sign(mv) != np.sign(e)
for lo, hi in [(0.5, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 99)]:
    say(f"  {lo}-{hi if hi < 99 else '+'} pts: {g(R.tot_model, R.l9am, ag & (mv.abs() >= lo) & (mv.abs() < hi))}")

say("\n(c) edge size at the opener")
for name, col in [("8 PM report (backtest)", "tot_model"), ("previous game's report (bettable at the open)", "tot_stale")]:
    say(f"  {name}")
    e = R[col] - R.open_total
    for lo, hi in [(2.0, 2.5), (2.5, 3.0), (3.0, 4.0), (4.0, 5.0), (5.0, 6.0), (6.0, 99)]:
        m = (e.abs() >= lo) & (e.abs() < hi)
        r = np.sign(e[m]) * (R.act[m] - R.open_total[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
        say(f"    edge {lo}-{hi if hi < 99 else '+'}: {w + l:5d} bets {w / max(w + l, 1):6.1%} {w * 100 / 110 - l:+7.1f}u")

d = (R.tot_stale - R.tot_model)
say(f"\n(d) previous-game report vs 8 PM report: model totals differ by {d.abs().mean():.2f} pts on average "
    f"(median {d.abs().median():.2f}, 90th pct {d.abs().quantile(.9):.2f}); corr {np.corrcoef(R.tot_stale.dropna(), R.tot_model[R.tot_stale.notna()])[0, 1]:.4f}")
open(os.path.join(W, "analysis", "rule_audit_line_rules_output.txt"), "w").write("\n".join(out) + "\n")
