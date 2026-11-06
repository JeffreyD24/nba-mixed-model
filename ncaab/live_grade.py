"""Grade the NCAAM PROVISIONAL stale-line spread alerts (ncaab/state/live_bets.csv) and the v2 paper picks each morning: result from Action Network's final score
(ncaab/data/games.csv by an_id), close = our own last pre-tip DraftKings capture (ncaab/state/dk_lines.csv). Stop rules (fixed Nov 5, 2026):
stop at -15u any time; at 100 graded bets stop if CLV < +0.63 or units < 0; first-100 CLV near +0.6 = we are not getting the opener.
  python ncaab/live_grade.py WORKDIR [--version v1|v2paper]
Nov 6, 2026 (Jeffrey: keep v1 LIVE, v2 on PAPER; Fable review NCAAM ncaab/research/fable_review_stale_line_v2_2026-11-05/REVIEW.md):
  v1 (default): ncaab/state/live_bets.csv -> live_record.md, stop rules and stop file exactly as before.
  v2paper: ncaab/state/live_paper_v2.csv -> live_record_v2_paper.md, same grading, NEVER writes the stop file."""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); ST = os.path.join(W, "ncaab", "state")
VER = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "v1"
BP, REC, SENT, LIVE, TITLE, RULE, EMPTY = {
    "v1": ("live_bets.csv", "live_record.md", ["True", "1"], True, "NCAAM PROVISIONAL stale-line spreads",
           "Rule: ncaab/research/MODEL3_RESULTS_2026-11-05.md. 1 unit per alert at the alerted DraftKings number and price.", "no alerts yet"),
    "v2paper": ("live_paper_v2.csv", "live_record_v2_paper.md", ["paper"], False, "NCAAM stale-line spreads v2 (PAPER, nothing is bet)",
                "Rule: v1 + lineup/travel/rest/roster layers, |edge| >= 0.62 (ncaab/data/live_blendc_v2.json). Tested at 0.62 on DK 2023-24 + 2025-26: "
                "625 bets, 57.4%, +58.8u, CLV +1.42 (NCAAM ncaab/research/stale_line_v2_fixed_threshold_check_output.txt); SBR 2014-2021: 1,520 bets, "
                "+251.1u, CLV +0.64 vs v1 +0.56 (NCAAM ncaab/research/STALE_LINE_V2_SBR_RESULTS_2026-11-06.md, SBR openers not bettable). "
                "Paper picks logged beside v1 at the same DraftKings number and price; nothing is bet.", "no picks yet"),
}[VER]
BP = os.path.join(ST, BP)
out = [f"# {TITLE}, updated {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET", "", RULE]
B = pd.read_csv(BP) if os.path.exists(BP) else pd.DataFrame(columns=["sent", "an_id"])
B = B[B.sent.astype(str).isin(SENT)].drop_duplicates("an_id")
if not len(B):
    out.append("\n- " + EMPTY); open(os.path.join(ST, REC), "w").write("\n".join(out) + "\n"); print("\n".join(out)); sys.exit(0)
G = pd.read_csv(os.path.join(W, "ncaab", "data", "games.csv"), low_memory=False).drop_duplicates("an_id").set_index("an_id")
L = pd.read_csv(os.path.join(ST, "dk_lines.csv")).drop_duplicates("an_id").set_index("an_id")
rows = []
for r in B.itertuples():
    g = G.loc[r.an_id] if r.an_id in G.index else None; close_home = L.last_line.get(r.an_id)
    sgn = 1 if r.side == "home" else -1
    clv = (sgn * (-close_home) - sgn * (-(r.line if r.side == "home" else -r.line))) if pd.notna(close_home) else np.nan
    if g is None or pd.isna(g.home_pts): res, u = "pending", 0.0
    else:
        m = g.home_pts - g.away_pts; cover = sgn * m + r.line
        px = float(r.price); win = px / 100 if px > 0 else 100 / abs(px)
        res, u = ("W", win) if cover > 0 else ("L", -1.0) if cover < 0 else ("P", 0.0)
    rows.append(dict(date=r.date, bet=f"{r.team} {r.line:+g} ({float(r.price):+.0f})", result=res, units=round(u, 3), clv=round(clv, 2) if pd.notna(clv) else np.nan))
R = pd.DataFrame(rows); D = R[R.result != "pending"]
n, units, clv = len(D), D.units.sum(), D.clv.mean()
dec = "continue"
if units <= -15: dec = "STOP (-15u)"
elif n >= 100 and (clv < 0.63 or units < 0): dec = "STOP (100-bet check failed)"
elif n >= 100: dec = "100-bet check passed: Fable review to promote"
out += ["", f"- **{len(R)} alerts, graded {(D.result == 'W').sum()}-{(D.result == 'L').sum()}-{(D.result == 'P').sum()}, {units:+.2f}u, CLV {clv:+.2f} (break-even +0.63; expected ~+1.2 if we get the opener)**",
        f"- Decision: **{dec}**", "", "| Date | Bet | Result | Units | CLV |", "|---|---|---|---|---|"] + \
       [f"| {x.date} | {x.bet} | {x.result} | {x.units:+.2f} | {x.clv:+.2f} |" for x in R.sort_values("date", ascending=False).itertuples()]
open(os.path.join(ST, REC), "w").write("\n".join(out) + "\n"); print("\n".join(out[:6]))
if LIVE and dec.startswith("STOP"): open(os.path.join(ST, "live_stop.txt"), "w").write(f"{dec} on {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d}\n")   # live_alert.py stops alerting
