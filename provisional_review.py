"""Provisional bets review (research/PROVISIONAL_BETS.md). Scoreboard for every provisional rule and which stop / promote line it has
crossed. Graded on every BET alert the rule made (first BET per game and market) and on the bets actually logged.
  python provisional_review.py WORKDIR  -> prints, and writes state/provisional_review.md"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); STATE = os.path.join(W, "state")
BREAK_EVEN = {"spread": 0.77,          # CLV in points needed to pay -110 (research/spreads/STEP1_NBA_RESULTS.md)
              "total": 1.07}           # full-game totals. Corrected Nov 5, 2026 from 0.33 (an "at the act line" number from
                                       #   research/spreads/LINE_MOVE_MODEL_RESULTS.md): 1 pt of CLV = +2.2% wins in NBA totals,
                                       #   every season 2021-26 (research/market_models/STEP3_MOVEMENT_RESULTS.md), so -110 needs ~1.07
STOP_ANY, STOP_25, PROMOTE_N, GIVE_UP_N = -10.0, -5.0, 100, 150


def score(R):
    g = R[R.result.astype(str).isin(["W", "L", "P"])]
    w, l, p = (g.result == "W").sum(), (g.result == "L").sum(), (g.result == "P").sum()
    u = w * 100 / 110 - l
    clv = pd.to_numeric(g.clv_points, errors="coerce")
    return dict(alerts=len(R), graded=int(w + l + p), w=int(w), l=int(l), p=int(p), units=round(float(u), 2),
                clv=round(float(clv.mean()), 2) if clv.notna().any() else np.nan, pending=int(len(R) - len(g)))


def decision(s, be):
    n, u, c = s["graded"], s["units"], s["clv"]
    if u <= STOP_ANY: return f"STOP: {u:+.1f}u is at or past the {STOP_ANY:+.0f}u line"
    if n >= 25 and u <= STOP_25: return f"STOP: {u:+.1f}u after {n} bets (25-bet line {STOP_25:+.0f}u)"
    if n >= 50 and (not (c > 0) or u < 0): return f"STOP: after {n} bets CLV {c:+.2f} / units {u:+.1f} (50-bet line: both must be positive)"
    if n >= PROMOTE_N and c >= be and u > 0: return f"PROMOTE (ask Jeffrey): {n} bets, CLV {c:+.2f} >= break-even {be:+.2f}, {u:+.1f}u"
    if n >= GIVE_UP_N: return f"STOP: {n} bets without meeting the promote bar (150-bet limit)"
    nxt = 25 if n < 25 else 50 if n < 50 else PROMOTE_N if n < PROMOTE_N else GIVE_UP_N
    return f"continue ({nxt - n} bets to the next checkpoint)"


def main():
    out = []
    A = pd.read_csv(os.path.join(STATE, "alerts.csv"))
    for c in ("tier", "news_bet", "verdict", "clv_points", "result"):
        if c not in A: A[c] = np.nan
    bet = A[(A.verdict.astype(str) == "BET") & A.sent.astype(str).isin(["True", "1", "1.0"])]
    first = bet.sort_values("alerted_at_et").groupby(["game_id", "market"]).head(1)
    rules = {"NBA spread injury-news bets (PROVISIONAL)": first[first.tier.astype(str) == "provisional"],
             "  all NBA spread news bets (tracking: provisional + v3 bets on unmoved/toward lines)":
                 first[(first.market == "spread") & first.news_bet.astype(str).isin(["True", "1", "1.0"])],
             "NBA totals 2.5-3 pt edges (PROVISIONAL)": first[first.tier.astype(str) == "provisional_totals"]}
    # market models line-movement bets (Nov 5, 2026): own file; graded on every BET the rule made, and on the ones pushed
    try:
        M = pd.read_csv(os.path.join(STATE, "market_models", "movement_alerts.csv"))
        M = M.assign(clv_points=M.clv_points)
        rules["NBA totals line-movement bets, market models v1-an (PROVISIONAL; every trigger)"] = M
        rules["  pushed to the phone (not same-side/conflict with the main totals model, price OK)"] = M[M.pushed.astype(str).isin(["True", "1", "1.0"])]
    except FileNotFoundError:
        pass
    try:
        Bl = pd.read_csv(os.path.join(STATE, "market_models", "blend_alerts.csv"))
        Bl = Bl[Bl.tier.astype(str) == "provisional_blend"]
        rules["NBA totals blend v4 + market, market models blend v1 (PROVISIONAL; every BET decision)"] = Bl
        rules["  blend totals pushed to the phone"] = Bl[Bl.pushed.astype(str).isin(["True", "1", "1.0"])]
        rules["  blend totals, overs only"] = Bl[Bl.side.astype(str) == "over"]
        rules["  blend totals, unders only"] = Bl[Bl.side.astype(str) == "under"]
    except FileNotFoundError:
        pass
    out.append(f"# Provisional bets review, {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET\n")
    out.append("Rules and stop lines: research/PROVISIONAL_BETS.md. Units at -110, 1 unit per alert; CLV in points vs the DraftKings close.\n")
    for name, R in rules.items():
        s = score(R)
        be = BREAK_EVEN["total" if "totals" in name else "spread"]
        line = (f"- **{name.strip()}**: {s['alerts']} BET alerts, graded {s['w']}-{s['l']}-{s['p']}, {s['units']:+.2f}u, "
                f"CLV {s['clv']:+.2f} (break-even {be:+.2f}), {s['pending']} pending")
        if not name.startswith("  "): line += f". Decision: **{decision(s, be)}**"
        out.append(line)
    try:
        BR = pd.read_csv(os.path.join(STATE, "bet_record.csv"))
        P = BR[BR.version.astype(str).str.startswith("PROVISIONAL")]
        g = P[P.status.isin(["W", "L", "P"])]
        out.append(f"- Logged provisional bets: {len(P)} ({(g.status == 'W').sum()}-{(g.status == 'L').sum()}-{(g.status == 'P').sum()}, "
                   f"{g.units.sum():+.2f}u at your prices)")
    except Exception as ex:
        out.append(f"- Logged provisional bets: unavailable ({type(ex).__name__})")
    txt = "\n".join(out) + "\n"
    open(os.path.join(STATE, "provisional_review.md"), "w").write(txt); print(txt)


if __name__ == "__main__":
    main()
