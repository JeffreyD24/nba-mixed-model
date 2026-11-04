"""Shadow record of the bets the live rules PASSED because the line moved 0.5+ against the model since the open (Nov 4, 2026).
Not bets: nothing here is pushed or changes a rule. It answers, on 2026-27 data with 5-minute line checks, the questions the
historical test (analysis/line_move_threshold.py, analysis/LINE_MOVE_PREREG.md) could only partly answer:
  * how big a move against is too big (0.5 / 1 / 1.5 / 2-2.5 / 3+ pts),
  * does an early move (first 30 min, 30-90 min) differ from a later one,
  * did the line swing back by the close,
  * was there news (the model itself moved 1+ pt the same way between the morning lock and the pass).
Each passed game is graded at the line when it was passed and at the closing line.
  python shadow_passed.py WORKDIR  -> state/shadow_passed.csv, state/shadow_passed.md"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); STATE = os.path.join(W, "state")


def sgn(market, side):
    return 1.0 if side in ("over", "home") else -1.0


def tow(market, side, move):
    """points the line moved TOWARD our side (negative = against). move = line - opening line, spreads from the home view."""
    s = sgn(market, side)
    return s * move if market == "total" else -s * move


def res(market, side, line, hp, ap):
    if pd.isna(line) or pd.isna(hp) or pd.isna(ap): return np.nan
    s = sgn(market, side)
    return s * (hp + ap - line) if market == "total" else s * (hp - ap + line)


def build():
    A = pd.read_csv(os.path.join(STATE, "alerts.csv"))
    P = A[A.skipped.fillna("").str.contains("against", case=False)].copy()
    if not len(P): return pd.DataFrame()
    LH = pd.read_csv(os.path.join(STATE, "line_history.csv"))
    LH["seen_at_et"] = pd.to_datetime(LH.seen_at_et, errors="coerce")
    LH = LH.dropna(subset=["seen_at_et"]).sort_values("seen_at_et")
    PL = pd.read_csv(os.path.join(STATE, "picks_log.csv"))[["game_id", "pred_margin", "pred_total", "home_pts", "away_pts"]]
    PL = PL.drop_duplicates("game_id", keep="last").set_index("game_id")
    rows = []
    for r in P.itertuples(index=False):
        h = LH[(LH.game_id == r.game_id) & (LH.market == r.market)]
        passed_at = pd.to_datetime(r.alerted_at_et)
        opn = float(r.open_line) if pd.notna(r.open_line) else (h.open_line.iloc[0] if len(h) else np.nan)
        open_seen = h.seen_at_et.iloc[0] if len(h) else pd.NaT
        mv = h.line.astype(float) - opn if len(h) else pd.Series(dtype=float)
        t_ = np.array([tow(r.market, r.side, m) for m in mv]) if len(h) else np.array([])
        hit = np.where(t_ <= -0.5)[0]
        first_against = h.seen_at_et.iloc[hit[0]] if len(hit) else passed_at
        mins = (first_against - open_seen).total_seconds() / 60 if pd.notna(open_seen) else np.nan
        if len(hit) and hit[0] == 0: mins = np.nan          # already moved at the first check: timing unknown
        hp, ap = r.home_pts, r.away_pts
        if (pd.isna(hp) or pd.isna(ap)) and r.game_id in PL.index:
            hp, ap = PL.loc[r.game_id, "home_pts"], PL.loc[r.game_id, "away_pts"]
        close = r.closing_line
        if pd.isna(close) and len(h):
            pre = h[h.seen_at_et < pd.to_datetime(r.tip_et)]
            close = pre.line.iloc[-1] if len(pre) else np.nan
        lock = np.nan
        if r.game_id in PL.index:
            lock = PL.loc[r.game_id, "pred_total" if r.market == "total" else "pred_margin"]
        s = sgn(r.market, r.side)
        news = s * (float(r.model) - float(lock)) if pd.notna(lock) and pd.notna(r.model) else np.nan
        move_at_pass = tow(r.market, r.side, float(r.line) - opn) if pd.notna(opn) else np.nan
        close_tow = tow(r.market, r.side, float(close) - opn) if pd.notna(close) and pd.notna(opn) else np.nan
        rows.append(dict(game_id=r.game_id, date=r.date, home=r.home, away=r.away, market=r.market, side=r.side, open_line=opn,
                         passed_line=r.line, passed_at_et=r.alerted_at_et, edge_at_pass=r.edge, move_against=-move_at_pass,
                         mins_open_to_against=round(mins, 1) if pd.notna(mins) else np.nan, model_news_pts=round(news, 2) if pd.notna(news) else np.nan,
                         closing_line=close, close_vs_open=close_tow, swing_back=(close_tow >= 0) if pd.notna(close_tow) else np.nan,
                         clv_points=(close_tow - move_at_pass) if pd.notna(close_tow) else np.nan,
                         res_passed=res(r.market, r.side, float(r.line), hp, ap), res_close=res(r.market, r.side, close, hp, ap),
                         res_open=res(r.market, r.side, opn, hp, ap),
                         suspect=bool(pd.notna(move_at_pass) and -move_at_pass >= (8 if r.market == "total" else 6))))
    return pd.DataFrame(rows)


def line(g, col):
    x = g[col].dropna(); w, l = int((x > 0).sum()), int((x < 0).sum()); u = w * 100 / 110 - l
    return f"{w}-{l} ({w / max(w + l, 1):.0%}) {u:+.1f}u" if w + l else "-"


def main():
    D = build()
    D.to_csv(os.path.join(STATE, "shadow_passed.csv"), index=False)
    md = ["# Shadow record: bets passed because the line moved against the model",
          "",
          "Not bets and nothing is pushed. Every 3+ edge game the rules PASSED for a 0.5+ move against since the open, graded as if bet "
          "at the line when passed, at the close, and at the opener. Answers whether the 0.5 threshold is too strict "
          "(pre-registration: analysis/LINE_MOVE_PREREG.md; history: analysis/line_move_threshold_output.txt). "
          "Review with the monthly provisional review. Sample sizes stay small for months: do not act on fewer than ~100 per row.",
          ""]
    if not len(D):
        md.append(f"No passed games yet. Updated {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET."); open(os.path.join(STATE, "shadow_passed.md"), "w").write("\n".join(md) + "\n"); print("\n".join(md)); return
    n_sus = int(D.suspect.sum()); D = D[~D.suspect].copy()
    D["size"] = pd.cut(D.move_against, [0.49, 0.75, 1.25, 1.75, 2.75, 99], labels=["0.5", "1.0", "1.5", "2.0-2.5", "3+"])
    D["when"] = pd.cut(D.mins_open_to_against, [-1, 30, 90, 360, 1e9], labels=["first 30 min", "30-90 min", "90 min-6 h", "6 h+"])
    D["news"] = np.where(D.model_news_pts <= -1, "yes (model also moved against 1+)", np.where(D.model_news_pts.notna(), "no", "unknown"))
    graded = D.res_passed.notna().sum()
    md.append(f"Passed games: {len(D)} ({graded} graded); {n_sus} left out as a suspect opener (move of 8+ pts on a total / 6+ on a spread). Timing is 'unknown' when the line had already moved at the first 5-minute check.")
    md.append(f"Updated {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET.")
    md += ["", "| Group | n | At the passed line | At the close | At the opener | Avg CLV (pts) | Back to the opener by close |", "|---|---|---|---|---|---|---|"]
    def add(lab, g):
        md.append(f"| {lab} | {len(g)} | {line(g, 'res_passed')} | {line(g, 'res_close')} | {line(g, 'res_open')} | "
                  f"{g.clv_points.mean():+.2f} | {g.swing_back.astype(float).mean():.0%} |" if len(g) else f"| {lab} | 0 | | | | | |")
    for mk in ("total", "spread"):
        M = D[D.market == mk]
        add(f"**{mk}s, all**", M)
        for k, lab in (("size", "move"), ("when", "moved against"), ("news", "news")):
            for v, g in M.groupby(k, observed=True): add(f"{mk}s, {lab}: {v}" + (" pts" if k == "size" else ""), g)
            if k == "when" and M.when.isna().any(): add(f"{mk}s, moved against: unknown", M[M.when.isna()])
    md += ["", "Watch items from the historical test (in-sample only, not bets): totals where the line moved against with **no news**; "
           "totals whose against-move came **6 h+ after the open**. Both were positive at the 9 AM line in 2023-26 but fail at the 9 PM line."]
    open(os.path.join(STATE, "shadow_passed.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
