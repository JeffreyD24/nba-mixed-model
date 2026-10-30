"""Builds NBA_Live_Tracker.xlsx from state/picks_log.csv. Summary numbers are formulas on the Picks sheet."""
import math
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter as CL

F = "Arial"
f_norm = Font(name=F, size=10); f_bold = Font(name=F, size=10, bold=True)
f_title = Font(name=F, size=14, bold=True, color="1F3864"); f_h = Font(name=F, size=11, bold=True, color="1F3864")
f_white = Font(name=F, size=10, bold=True, color="FFFFFF"); f_note = Font(name=F, size=9, italic=True, color="595959")
fill_dark = PatternFill("solid", fgColor="1F3864"); fill_head = PatternFill("solid", fgColor="D9E2F3")
fill_green = PatternFill("solid", fgColor="E2EFDA"); fill_rule = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="BFBFBF"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
center = Alignment(horizontal="center", vertical="center")
COLS = [("Date", "date"), ("Tip (ET)", "tip_et"), ("Away", "away"), ("Home", "home"), ("Pick type", "pick_type"),
        ("Locked at (ET)", "locked_at_et"), ("Model margin (home)", "pred_margin"), ("Model total", "pred_total"),
        ("Open spread (home)", "open_spread"), ("Open total", "open_total"), ("Close spread (home)", "close_spread"),
        ("Close total", "close_total"), ("Away pts", "away_pts"), ("Home pts", "home_pts"),
        ("Open spread: bet", "open_spread_bet"), ("Open spread: edge", "open_spread_edge"), ("Open spread: result", "open_spread_result"),
        ("Open total: bet", "open_total_bet"), ("Open total: edge", "open_total_edge"), ("Open total: result", "open_total_result"),
        ("Close spread: bet", "close_spread_bet"), ("Close spread: edge", "close_spread_edge"), ("Close spread: result", "close_spread_result"),
        ("Close total: bet", "close_total_bet"), ("Close total: edge", "close_total_edge"), ("Close total: result", "close_total_result")]
RES_COL = {f"{l}_{m}": (CL(16 + 6 * (l == "close") + 3 * (m == "total")), CL(17 + 6 * (l == "close") + 3 * (m == "total")))
           for l in ("open", "close") for m in ("spread", "total")}      # (edge col, result col)


def hdr(ws, r, c, text, span=1, dark=True):
    if span > 1: ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + span - 1)
    x = ws.cell(r, c, text); x.font = f_white if dark else f_bold; x.fill = fill_dark if dark else fill_head
    x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for k in range(c, c + span): ws.cell(r, k).border = box


def record(df, line, market, edge, live_only):
    d = df if not live_only else df[df.pick_type == "live"]
    e, r = d[f"{line}_{market}_edge"], d[f"{line}_{market}_result"]
    s = d[(e >= edge) & r.isin(["W", "L"])]
    return int((s[f"{line}_{market}_result"] == "W").sum()), int((s[f"{line}_{market}_result"] == "L").sum())


def interpret(w, l):
    n = w + l
    if n == 0:
        return ("No graded live bets under the rule yet.", "Nothing to judge yet. Let the season run; the first meaningful read comes after about 150 bets.")
    p = w / n; units = w * 100 / 110 - l
    se = math.sqrt(0.25 / n); z = (p - 110 / 210) / se
    lo, hi = max(0, p - 1.96 * math.sqrt(p * (1 - p) / n)), min(1, p + 1.96 * math.sqrt(p * (1 - p) / n))
    status = f"Live record under the rule: {w}-{l} ({p:.1%}), {units:+.1f} units at -110. Plausible range for the true win rate: {lo:.0%} to {hi:.0%}."
    if n < 50:
        adv = (f"Only {n} bets so far: far too few to tell skill from luck (a coin-flip bettor lands anywhere from about "
               f"{0.5 - 1.96 * math.sqrt(0.25 / n):.0%} to {0.5 + 1.96 * math.sqrt(0.25 / n):.0%} over {n} bets). Do not change the rule or start betting. Keep tracking.")
    elif n < 150:
        adv = ("Still early. Results this size swing a lot by chance. "
               + ("It is running above break-even, which is consistent with the backtests, but not proof. " if p > 110 / 210 else
                  "It is running below break-even. That is not yet evidence the edge is gone, but watch it. ")
               + "Keep the rule fixed and keep tracking to at least 150 bets.")
    else:
        if z > 1.645:
            adv = (f"After {n} bets it is beating break-even by more than chance would usually allow (z = {z:.2f}). This is the result we were hoping to see. "
                   "Before risking money, compare the logged opening lines with prices you could actually have gotten, and start small.")
        elif p > 110 / 210:
            adv = (f"After {n} bets it is above break-even but not convincingly (z = {z:.2f}). Keep tracking through the end of the season before deciding anything.")
        else:
            adv = (f"After {n} bets it is not beating break-even (z = {z:.2f}). The backtested opening-line edge is not showing up live. "
                   "The honest conclusion so far is that the model does not beat the market; do not bet on it.")
    return status, adv


def clv_line(df, A, MB):
    parts = []
    for mk in ("spread", "total"):
        c = f"open_{mk}_clv"; e = f"open_{mk}_edge"
        if c in df:
            x = df[(df.pick_type == "live") & (df[e] >= 3)][c].dropna()
            if len(x): parts.append(f"scorecard {mk}s {x.mean():+.2f} pts avg, beat the close {(x > 0).mean():.0%} of the time (n={len(x)})")
    if len(A) and "clv_points" in A:
        x = A["clv_points"].dropna()
        if len(x): parts.append(f"alerts {x.mean():+.2f} pts avg (n={len(x)})")
    if len(MB) and "clv_points" in MB:
        x = MB["clv_points"].dropna()
        if len(x): parts.append(f"your bets {x.mean():+.2f} pts avg (n={len(x)})")
    if not parts:
        return "Closing line value (did a bet beat the final line?): nothing graded yet. Over time this is the best early sign of a real edge, far quicker than wins and losses."
    return ("Closing line value (did a bet beat the final line?): " + "; ".join(parts) +
            ". Consistently positive closing line value is the strongest early sign of a real edge, more reliable than a short win-loss record.")


def jump_line(J):
    if not len(J):
        return "Line jumps (moves of 1.5+ pts within an hour): none logged yet. This builds a database of how lines react to news."
    s = f"Line jumps logged: {len(J)} (moves of 1.5+ pts within an hour)."
    if "result_matched_move" in J:
        g = J[J.result_matched_move.isin(["yes", "no"])]
        if len(g):
            s += (f" Graded: {len(g)}; the final result went the way the line jumped {int((g.result_matched_move == 'yes').sum())} times"
                  f" ({(g.result_matched_move == 'yes').mean():.0%}).")
            k = J[J.kept_moving_to_close.notna()] if "kept_moving_to_close" in J else J.iloc[:0]
            if len(k): s += f" Kept moving the same way by the close: {(k.kept_moving_to_close == 'yes').mean():.0%}."
    return s + " Give it a few weeks of data before drawing conclusions."


def caution_line(A):
    if not len(A) or "skipped" not in A or "result" not in A:
        return "Caution alerts (sent with a warning because a safeguard was triggered): none graded yet."
    c = A[A.skipped.notna() & A.result.isin(["W", "L"])]
    if not len(c): return "Caution alerts (sent with a warning because a safeguard was triggered): none graded yet."
    w, l = int((c.result == "W").sum()), int((c.result == "L").sum())
    return (f"Caution alerts (sent with a warning because a safeguard was triggered): {w}-{l}, {w * 100 / 110 - l:+.1f} units. "
            "If these do clearly worse than clean alerts over time, the safeguards are doing their job.")


def build(log_csv, out_xlsx, rule, run_log):
    df = pd.read_csv(log_csv, parse_dates=["date", "tip_et", "locked_at_et"]).sort_values(["date", "tip_et"])
    wb = Workbook(); notes = wb.active; notes.title = "Notes"
    import os
    apath = os.path.join(os.path.dirname(log_csv), "alerts.csv")
    A = pd.read_csv(apath) if os.path.exists(apath) else pd.DataFrame()
    al = wb.create_sheet("Alerts")
    acols = [("Alerted at (ET)", "alerted_at_et"), ("Away", "away"), ("Home", "home"), ("Tip (ET)", "tip_et"), ("Market", "market"),
             ("Bet", "side"), ("Line when alerted", "line"), ("Opening line", "open_line"), ("Model", "model"), ("Edge", "edge"),
             ("Injury report used", "injury_report"), ("Caution (reason)", "skipped"), ("Result", "result")]
    for k, (t, _) in enumerate(acols): hdr(al, 1, k + 1, t)
    al.row_dimensions[1].height = 30
    for r in A.to_dict("records"):
        al.append([None if (isinstance(r.get(c), float) and np.isnan(r.get(c))) else r.get(c) for _, c in acols])
    for k in range(1, len(acols) + 1): al.column_dimensions[CL(k)].width = 13
    al.column_dimensions["K"].width = 20; al.column_dimensions["L"].width = 26; al.freeze_panes = "A2"
    sent = A[A.skipped.isna()] if len(A) and "skipped" in A else A
    graded = sent[sent.result.isin(["W", "L"])] if len(sent) and "result" in sent else sent.iloc[:0] if len(sent) else sent
    # ---- line jumps database
    jpath = os.path.join(os.path.dirname(log_csv), "line_jumps.csv")
    JJ = pd.read_csv(jpath) if os.path.exists(jpath) else pd.DataFrame()
    lj = wb.create_sheet("Line Jumps")
    jcols = [("Detected (ET)", "detected_at_et"), ("Game date", "date"), ("Away", "away"), ("Home", "home"), ("Market", "market"),
             ("From", "from_line"), ("To", "to_line"), ("Move", "move"), ("Steady since", "steady_since"), ("Move started", "move_started"),
             ("Minutes", "minutes"), ("Hours to tip", "hours_to_tip"), ("Model", "model"), ("Direction", "direction"),
             ("News items", "news_count"), ("Alerted", "alerted"), ("Closing line", "closing_line"),
             ("Kept moving to close?", "kept_moving_to_close"), ("Result matched move?", "result_matched_move"), ("News around the move", "news_in_window")]
    for k, (t, _) in enumerate(jcols): hdr(lj, 1, k + 1, t)
    lj.row_dimensions[1].height = 30
    for r in JJ.to_dict("records"):
        vals = []
        for _, c in jcols:
            v = r.get(c)
            if isinstance(v, float) and np.isnan(v): v = None
            if c in ("away", "home") and isinstance(v, str): v = v.upper()
            vals.append(v)
        lj.append(vals)
    for k in range(1, len(jcols) + 1): lj.column_dimensions[CL(k)].width = 12
    lj.column_dimensions["T"].width = 80; lj.freeze_panes = "A2"

    # ---- the user's own logged bets
    bpath = os.path.join(os.path.dirname(log_csv), "my_bets.csv")
    MB = pd.read_csv(bpath) if os.path.exists(bpath) else pd.DataFrame()
    mb = wb.create_sheet("My Bets", 1)
    mcols = [("Logged at (ET)", "logged_at_et"), ("Game date", "date"), ("Away", "away"), ("Home", "home"), ("Market", "market"),
             ("Pick", "pick"), ("Line", "line"), ("Odds", "odds"), ("Stake ($)", "stake"), ("Book", "book"),
             ("Model number (your side)", "model_number"), ("Model edge at your line", "model_edge_at_your_line"),
             ("Result", "result"), ("Profit ($)", "profit"), ("Notes", "notes")]
    for k, (t, _) in enumerate(mcols): hdr(mb, 1, k + 1, t)
    mb.row_dimensions[1].height = 30
    for r in MB.to_dict("records"):
        vals = []
        for _, c in mcols:
            v = r.get(c)
            if isinstance(v, float) and np.isnan(v): v = None
            if c in ("pick", "away", "home") and isinstance(v, str): v = v.upper()
            vals.append(v)
        mb.append(vals)
    n = max(mb.max_row, 2)
    for k in range(1, len(mcols) + 1): mb.column_dimensions[CL(k)].width = 12
    mb.column_dimensions["O"].width = 30; mb.freeze_panes = "A2"
    r0 = n + 2
    mb.cell(r0, 1, "Totals (formulas)").font = f_h
    labels = [("Bets graded", f'=COUNTIF(M2:M{n},"W")+COUNTIF(M2:M{n},"L")+COUNTIF(M2:M{n},"P")'),
              ("Wins", f'=COUNTIF(M2:M{n},"W")'), ("Losses", f'=COUNTIF(M2:M{n},"L")'), ("Pushes", f'=COUNTIF(M2:M{n},"P")'),
              ("Staked on graded bets ($)", f'=SUMIF(M2:M{n},"?*",I2:I{n})'), ("Profit ($)", f"=SUM(N2:N{n})"),
              ("Return on money staked", f'=IFERROR(B{r0 + 6}/B{r0 + 5},"")')]
    for k, (lab, fml) in enumerate(labels):
        mb.cell(r0 + 1 + k, 1, lab).font = f_bold
        x = mb.cell(r0 + 1 + k, 2, fml); x.font = f_norm
        if "($)" in lab: x.number_format = '$#,##0.00;-$#,##0.00'
        if lab.startswith("Return"): x.number_format = "0.0%"
    gb = MB[MB.result.isin(["W", "L", "P"])] if len(MB) and "result" in MB else MB.iloc[:0] if len(MB) else MB
    if len(gb):
        mbw, mbl = int((gb.result == "W").sum()), int((gb.result == "L").sum())
        my_line = (f"Your logged bets: {mbw}-{mbl}, ${gb.profit.sum():+.2f} on ${gb.stake.sum():.2f} staked "
                   f"({gb.profit.sum() / gb.stake.sum():+.1%}). Average model edge at the lines you got: {gb.model_edge_at_your_line.mean():.1f} pts. "
                   "If your edge is usually smaller than the scorecard's opening-line edge, betting earlier would help.")
    else:
        my_line = "Your logged bets: none graded yet. Log bets with the 'Log a bet' form (button on each alert, or the Issues tab)."
    ps = wb.create_sheet("Picks")
    for k, (t, _) in enumerate(COLS): hdr(ps, 1, k + 1, t)
    ps.row_dimensions[1].height = 42
    for r in df.itertuples(index=False):
        vals = []
        for _, c in COLS:
            v = getattr(r, c, None)
            if isinstance(v, float) and np.isnan(v): v = None
            if isinstance(v, pd.Timestamp): v = v.to_pydatetime() if c != "date" else v.date()
            if c in ("pred_margin", "pred_total") and v is not None: v = round(v, 1)
            if c.endswith("_edge") and v is not None: v = round(v, 2)
            vals.append(v)
        ps.append(vals)
    N = max(ps.max_row, 2)
    for row in ps.iter_rows(min_row=2, max_row=N):
        for x in row: x.font = f_norm
    for k in range(1, len(COLS) + 1): ps.column_dimensions[CL(k)].width = 11
    for c in (2, 6):
        for row in range(2, N + 1): ps.cell(row, c).number_format = "m/d h:mm"
    ps.freeze_panes = "E2"; ps.auto_filter.ref = f"A1:{CL(len(COLS))}{N}"

    sm = wb.create_sheet("Summary", 1)
    sm["A1"] = "2026-27 tracker results (formulas on the Picks sheet)"; sm["A1"].font = f_title
    sm["A2"] = (f"The tracked rule (highlighted): every spread and total where the opening line differs from the model by ≥ {rule['edge']:g} points, graded at the opening line. "
                "'Live' = locked before tip on game day. 'Backfilled' = games before tracking started, predicted with the same no-lookahead method."); sm["A2"].font = f_note
    sm["A3"] = "Break-even win % at -110:"; sm["A3"].font = f_bold
    sm["D3"] = "=110/210"; sm["D3"].number_format = "0.0%"; sm["D3"].font = f_norm
    r = 5
    for scope, crit in [("Live picks only", '"live"'), ("Live + backfilled", '"*"')]:
        sm.cell(r, 1, scope).font = f_h; r += 1
        for k, t in enumerate(["Line", "Market", "Edge ≥", "W", "L", "Win %", "Units"]): hdr(sm, r, k + 1, t)
        r += 1; start = r
        for line in ("open", "close"):
            for market in ("spread", "total"):
                ec, rc = RES_COL[f"{line}_{market}"]
                for th in (0, 3, 4, 5, 6):
                    is_rule = (line == rule["line"] and market in rule["markets"] and th == rule["edge"])
                    for k, v in enumerate([line, market, th]):
                        x = sm.cell(r, k + 1, v); x.font = f_bold if is_rule else f_norm; x.alignment = center; x.border = box
                    base = f"Picks!$E$2:$E${N},{crit},Picks!${ec}$2:${ec}${N},\">=\"&$C{r}"
                    cells = [sm.cell(r, 4, f'=COUNTIFS({base},Picks!${rc}$2:${rc}${N},"W")'),
                             sm.cell(r, 5, f'=COUNTIFS({base},Picks!${rc}$2:${rc}${N},"L")'),
                             sm.cell(r, 6, f'=IFERROR(D{r}/(D{r}+E{r}),"")'), sm.cell(r, 7, f"=D{r}*100/110-E{r}")]
                    cells[2].number_format = "0.0%"; cells[3].number_format = '+0.0;-0.0;0.0'
                    for x in cells:
                        x.font = f_bold if is_rule else f_norm; x.alignment = center; x.border = box
                        if is_rule: x.fill = fill_rule
                    r += 1
        sm.conditional_formatting.add(f"F{start}:F{r-1}", FormulaRule(formula=[f"AND(ISNUMBER(F{start}),F{start}>=$D$3)"], fill=fill_green))
        r += 1
    for c, w in zip(range(1, 8), [9, 9, 8, 8, 8, 9, 9]): sm.column_dimensions[CL(c)].width = w

    # ---- notes (regenerated every run)
    w = l = 0
    for mk in rule["markets"]:
        a, b = record(df, rule["line"], mk, rule["edge"], live_only=True); w += a; l += b
    status, adv = interpret(w, l)
    live = df[df.pick_type == "live"]
    lw, ll = record(df, "close", "spread", 0, True)
    notes["A1"] = "NBA Live Tracker, 2026-27"; notes["A1"].font = f_title
    lines = [
        ("h", "What this is"),
        ("t", "Every evening (about 9:30 PM ET) GitHub refits the official-injury-report mixed model (trained on 2021-22 through 2025-26) and locks its predictions for the next day's games using the 8 PM injury report, the same setup the backtests used. A morning run adds the latest results, grades finished games, and refreshes the data. Locked picks are never changed. Lines come from ESPN (DraftKings)."),
        ("t", f"The tracked rule, fixed before live tracking began: every spread and total whose opening line differs from the locked model number by at least {rule['edge']:g} points counts as a bet at the opening line, even if the line moved before a bet could be placed. That measures the model itself. Everything else on the Summary sheet is context only; do not pick a new rule from it mid-season."),
        ("t", f"Picks logged: {len(df)} games ({len(live)} live, {len(df) - len(live)} backfilled from before tracking started). Latest run: {run_log[0] if run_log else ''}"),
        ("h", "Where things stand"),
        ("t", status),
        ("t", (f"Phone alerts (edge 3+ against the line at the moment of the alert, spreads and totals): {int((graded.result == 'W').sum())}-{int((graded.result == 'L').sum())}"
               f" graded so far, {int((graded.result == 'W').sum()) * 100 / 110 - int((graded.result == 'L').sum()):+.1f} units at -110. These are judged against later, sharper lines than the scorecard, so expect them to do worse."
               if len(graded) else "Phone alerts: none graded yet.")),
        ("t", caution_line(A)),
        ("t", my_line),
        ("t", jump_line(JJ)),
        ("t", clv_line(df, A, MB)),
        ("h", "My note and advice"),
        ("t", adv),
        ("t", "Reminders: the opening line logged here is the sportsbook's first posted number, which usually has low limits and moves quickly, so real results would be somewhat worse. The model has never beaten closing lines in any backtest; the closing-line rows are there as a reality check."),
        ("h", "Last run log"),
    ] + [("t", s) for s in run_log]
    r = 3
    for kind, text in lines:
        x = notes.cell(r, 1, text)
        if kind == "h": x.font = f_h; r += 1
        else:
            x.font = f_norm; x.alignment = Alignment(wrap_text=True, vertical="top")
            notes.row_dimensions[r].height = 15 * (1 + len(text) // 110)
        r += 1
    notes.column_dimensions["A"].width = 120
    wb.save(out_xlsx)
