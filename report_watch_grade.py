"""
Grades the report watcher (TEST bucket, not bets). Morning run. Rules written before any live data: research/spreads/REPORT_WATCH_PLAN.md.

For every game a new official report changed (summed model news |N| >= 0.5 for the home margin or the total, compared with the
report just before it, nothing missed in between), DraftKings' spread and total from research/pregame (every minute) at: the report's
printed time, the minute we first saw the file, +5, +15, +30 min, and the close (last line before tip). Results from state/picks_log.csv.

  python report_watch_grade.py WORKDIR   -> state/report_watch_record.csv (one row per event x market), state/report_watch.md
"""
import os, sys, glob
import numpy as np, pandas as pd

W = os.path.abspath(sys.argv[1]); STATE = os.path.join(W, "state")
DELAYS = [("seen", 0), ("+5", 5), ("+15", 15), ("+30", 30)]
MIN_N = 0.5          # event threshold (points)
BET_N = 1.5          # hypothetical TEST bets: news of 1.5+ points


def dk_lines(date):
    p = os.path.join(W, "research", "pregame", f"{date}.csv")
    if not os.path.exists(p): return None
    d = pd.read_csv(p, parse_dates=["seen_at_et"])
    d = d[(d.book == "DraftKings") & (d.period == "event") & (((d.market == "spread") & (d.side == "home")) | ((d.market == "total") & (d.side == "over")))]
    return {k: g.sort_values("seen_at_et") for k, g in d.groupby(["away", "home", "market"])}


def at(g, t):
    """last DraftKings value at or before t (None if nothing yet)"""
    x = g[g.seen_at_et <= t]
    return None if x.empty else float(x.value.iloc[-1])


def main():
    files = sorted(glob.glob(os.path.join(W, "research", "report_watch", "*.csv")))
    if not files:
        open(os.path.join(STATE, "report_watch.md"), "w").write("# Report watcher (TEST bucket, not bets)\n\nNothing logged yet.\n")
        print("Report watch: nothing logged yet."); return
    E = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    E["first_seen_et"] = pd.to_datetime(E.first_seen_et); E["report_as_of"] = pd.to_datetime(E.report_as_of, errors="coerce")
    E["tip_et"] = pd.to_datetime(E.tip_et)
    # only changes against the report immediately before (15 min earlier for 15-minute names, 60 for the hourly name) so timing is clean
    import re
    def nt(n):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2})(?:_(\d{2}))?(AM|PM)$", str(n))
        return None if not m else pd.to_datetime(f"{m.group(1)} {m.group(2)}:{m.group(3) or '30'}{m.group(4)}", format="%Y-%m-%d %I:%M%p")
    def gap(r):
        a, b = nt(r.report), nt(r.prev_report)
        return np.nan if a is None or b is None else (a - b).total_seconds() / 60
    E["gap_min"] = E.apply(gap, axis=1)
    E = E[E.gap_min.notna()]                    # groupby would drop NaN keys silently; make the drop explicit
    G = (E[E.rated].groupby(["date", "game_id", "away", "home", "tip_et", "report", "prev_report", "gap_min"])
         .agg(first_seen=("first_seen_et", "min"), printed=("report_as_of", "min"), N_margin=("d_home_margin", "sum"),
              N_total=("d_total", "sum"), players=("player", lambda s: "; ".join(s))).reset_index())
    hourly = ~G.report.str[11:].str.contains("_")
    G = G[(G.gap_min > 0) & (G.gap_min <= np.where(hourly, 60, 15)) & (G.first_seen < G.tip_et)]
    PL = pd.read_csv(os.path.join(STATE, "picks_log.csv")) if os.path.exists(os.path.join(STATE, "picks_log.csv")) else pd.DataFrame()
    res = {(str(r.date)[:10], r.home): (r.home_pts, r.away_pts) for r in PL.itertuples() if pd.notna(r.home_pts)} if len(PL) else {}
    cache = {}; rows = []
    for r in G.itertuples():
        if r.date not in cache: cache[r.date] = dk_lines(r.date)
        L = cache[r.date]
        if not L: continue
        for mk, N in (("spread", r.N_margin), ("total", r.N_total)):
            if abs(N) < MIN_N or (r.away, r.home, mk) not in L: continue
            g = L[(r.away, r.home, mk)]; g = g[g.seen_at_et < r.tip_et]
            conv = (lambda v: None if v is None else -v) if mk == "spread" else (lambda v: v)     # spread -> home margin
            rec = dict(date=r.date, game_id=r.game_id, away=r.away, home=r.home, report=r.report, players=r.players, market=mk,
                       news=round(N, 2), printed=r.printed, first_seen=r.first_seen,
                       detect_lag_min=round((r.first_seen - r.printed).total_seconds() / 60, 1) if pd.notna(r.printed) else None,
                       line_printed=conv(at(g, r.printed)) if pd.notna(r.printed) else None)
            for lab, m in DELAYS:   # a time at or after tip is left empty (it would just repeat the close)
                tt = r.first_seen + pd.Timedelta(minutes=m)
                rec[f"line_{lab}"] = conv(at(g, tt)) if tt < r.tip_et else None
            rec["line_close"] = conv(float(g.value.iloc[-1])) if len(g) else None
            pts = res.get((r.date, r.home))
            rec["result"] = (pts[0] - pts[1] if mk == "spread" else pts[0] + pts[1]) if pts else None
            rows.append(rec)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(STATE, "report_watch_record.csv"), index=False)
    md = ["# Report watcher (TEST bucket, not bets)", "",
          f"Updated {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} ET. Plan: research/spreads/REPORT_WATCH_PLAN.md. "
          f"Events: {len(R)} (news 0.5+ pts vs the report just before)."]
    if len(R):
        md.append(f"Our detection lag (printed time -> first seen): median {R.detect_lag_min.median():.1f} min.")
        md += ["", "| Market | Events | Move per pt of news: printed->seen | seen->+5 | +5->+15 | +15->+30 | +30->close |", "|---|---|---|---|---|---|---|"]
        for mk, g in R.groupby("market"):
            g = g.dropna(subset=["line_printed", "line_seen", "line_+5", "line_+15", "line_+30", "line_close"])
            if g.empty: continue
            sl = lambda a, b: float(np.sum(g.news * (g[b] - g[a])) / np.sum(g.news ** 2))
            md.append(f"| {mk} | {len(g)} | {sl('line_printed','line_seen'):+.2f} | {sl('line_seen','line_+5'):+.2f} | {sl('line_+5','line_+15'):+.2f} | "
                      f"{sl('line_+15','line_+30'):+.2f} | {sl('line_+30','line_close'):+.2f} |")
        md += ["", f"Hypothetical TEST bets (news {BET_N}+ pts, side the news favors), CLV vs the DraftKings close and record so far:",
               "| Market | Bet at | Bets | CLV (pts) | W-L |", "|---|---|---|---|---|"]
        for mk, g in R[R.news.abs() >= BET_N].groupby("market"):
            for lab, _ in DELAYS:
                h = g.dropna(subset=[f"line_{lab}", "line_close"]); s = np.sign(h.news)
                clv = (s * (h.line_close - h[f"line_{lab}"])).mean() if len(h) else np.nan
                d = h.dropna(subset=["result"]); w = (np.sign(d.news) * (d.result - d[f"line_{lab}"]))
                md.append(f"| {mk} | {lab} | {len(h)} | {clv:+.2f} | {(w > 0).sum()}-{(w < 0).sum()} |")
    open(os.path.join(STATE, "report_watch.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
