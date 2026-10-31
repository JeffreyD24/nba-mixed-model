"""
Bet timing: how the model does if you bet at different times after the line opens.

For every finished game, rebuild DraftKings' line path (research/timeline, with the book's own change times; before that
existed, state/line_history), then grade the model's bet at fixed times:
  after the open: 0 (the opening line), 15 min, 30 min, 1 h, 2 h, 4 h, 8 h
  before tip:     3 h, 1 h, 30 min, and the close (last line before tip)
Two ways to read each time point:
  kept  - the side the model liked at the opening line (opening edge 3+), bet at this later line and price
          ("I got the alert but couldn't bet right away")
  fresh - a bet only if the model is still 3+ points off at this line (the decision you'd make seeing it then)
Writes state/bet_timing.csv, one row per game, market and time point.
"""
import os, glob
import numpy as np, pandas as pd

EDGE = 3.0
AFTER_OPEN = [("open", 0), ("open+15m", 15), ("open+30m", 30), ("open+1h", 60), ("open+2h", 120), ("open+4h", 240), ("open+8h", 480)]
BEFORE_TIP = [("tip-3h", 180), ("tip-1h", 60), ("tip-30m", 30), ("close", 0)]


def _profit(odds, result):
    if result == "W": return 100 / abs(odds) if odds < 0 else odds / 100
    if result == "L": return -1.0
    return 0.0


def _odds(x):
    return -110.0 if pd.isna(x) else float(x)


def _path(W, game, date, home, away):
    """DraftKings line path for one game: DataFrame t (ET, naive), home_spread, total, prices; plus whether the opening time is exact"""
    tl = os.path.join(W, "research", "timeline", f"{date}.csv")
    rows = pd.DataFrame()
    if os.path.exists(tl):
        d = pd.read_csv(tl)
        d = d[(d.book == "DraftKings") & (d.home == home) & (d.away == away)].copy()
        if len(d):
            ch = pd.to_datetime(d.book_changed_utc, utc=True, errors="coerce").dt.tz_convert("America/New_York").dt.tz_localize(None)
            seen = pd.to_datetime(d.seen_at_et)
            d["t"] = ch.where(ch.notna() & (ch <= seen + pd.Timedelta(minutes=1)), seen)
            rows = d[["t", "home_spread", "home_spread_odds", "away_spread_odds", "total", "over_odds", "under_odds"]]
    if not len(rows):
        hp = os.path.join(W, "state", "line_history.csv")
        if os.path.exists(hp):
            h = pd.read_csv(hp); h = h[h.game_id == game]
            if len(h):
                h["t"] = pd.to_datetime(h.seen_at_et)
                sp = h[h.market == "spread"][["t", "line"]].rename(columns={"line": "home_spread"})
                to = h[h.market == "total"][["t", "line"]].rename(columns={"line": "total"})
                rows = pd.concat([sp, to]).sort_values("t")
                rows[["home_spread", "total"]] = rows[["home_spread", "total"]].ffill()
                for c in ("home_spread_odds", "away_spread_odds", "over_odds", "under_odds"): rows[c] = np.nan
    return rows.sort_values("t").reset_index(drop=True) if len(rows) else rows


def grade(W, logdf):
    done = logdf[logdf.home_pts.notna() & (logdf.pick_type == "live")]
    out = []
    for g in done.itertuples():
        date = str(pd.Timestamp(g.date).date()); tip = pd.Timestamp(g.tip_et)
        P = _path(W, g.game_id, date, g.home, g.away)
        if not len(P): continue
        P = P[P.t < tip]
        if not len(P): continue
        margin = g.home_pts - g.away_pts; pts = g.home_pts + g.away_pts
        for market in ("spread", "total"):
            col = "home_spread" if market == "spread" else "total"
            Q = P[P[col].notna()]
            if not len(Q): continue
            dk_open = g.open_spread if market == "spread" else g.open_total
            open_exact = (not pd.isna(dk_open)) and float(Q[col].iloc[0]) == float(dk_open)
            t_open = Q.t.iloc[0]
            o_line = float(Q[col].iloc[0])
            o_edge = (g.pred_margin + o_line) if market == "spread" else (g.pred_total - o_line)
            o_side = (("home" if o_edge > 0 else "away") if market == "spread" else ("over" if o_edge > 0 else "under"))
            pts_list = [(n, t_open + pd.Timedelta(minutes=m)) for n, m in AFTER_OPEN] + \
                       [(n, tip - pd.Timedelta(minutes=m) - (pd.Timedelta(minutes=1) if m == 0 else pd.Timedelta(0))) for n, m in BEFORE_TIP]
            for name, T in pts_list:
                if T >= tip or T < t_open: continue
                r = Q[Q.t <= T].iloc[-1]
                line = float(r[col])
                if market == "spread":
                    edge = g.pred_margin + line; side = "home" if edge > 0 else "away"
                    res = lambda s: "P" if margin + line == 0 else ("W" if ((margin + line > 0) == (s == "home")) else "L")
                    price = lambda s: _odds(r.home_spread_odds if s == "home" else r.away_spread_odds)
                else:
                    edge = g.pred_total - line; side = "over" if edge > 0 else "under"
                    res = lambda s: "P" if pts == line else ("W" if ((pts > line) == (s == "over")) else "L")
                    price = lambda s: _odds(r.over_odds if s == "over" else r.under_odds)
                fresh = abs(edge) >= EDGE; kept = abs(o_edge) >= EDGE
                kept_edge = edge if o_side in ("home", "over") else -edge     # points of edge left on the opening side (negative = gone past)
                rf = res(side) if fresh else None; rk = res(o_side) if kept else None
                out.append(dict(game_id=g.game_id, date=date, away=g.away, home=g.home, market=market, time_point=name,
                                at_et=str(T)[:16], minutes_after_open=round((T - t_open).total_seconds() / 60),
                                minutes_before_tip=round((tip - T).total_seconds() / 60), open_time_exact=open_exact,
                                open_line=o_line, line=line, shift_from_open=line - o_line,
                                model=round(g.pred_margin if market == "spread" else g.pred_total, 2),
                                open_edge=round(o_edge, 2), open_side=o_side, edge=round(edge, 2), side=side,
                                kept_edge=round(kept_edge, 2),
                                kept_bet=kept, kept_odds=price(o_side) if kept else np.nan, kept_result=rk,
                                kept_profit=_profit(price(o_side), rk) if kept else np.nan,
                                fresh_bet=fresh, fresh_odds=price(side) if fresh else np.nan, fresh_result=rf,
                                fresh_profit=_profit(price(side), rf) if fresh else np.nan))
    T = pd.DataFrame(out)
    T.to_csv(os.path.join(W, "state", "bet_timing.csv"), index=False)
    return T


def summary(T):
    """per time point: how far the line has moved, and the record and profit for kept and fresh bets"""
    order = [n for n, _ in AFTER_OPEN] + [n for n, _ in BEFORE_TIP]
    rows = []
    for name in order:
        x = T[T.time_point == name] if len(T) else T
        k = x[x.kept_bet] if len(x) else x; f = x[x.fresh_bet] if len(x) else x
        wl = lambda d, c: (int((d[c] == "W").sum()), int((d[c] == "L").sum()))
        kw, kl = wl(k, "kept_result") if len(k) else (0, 0); fw, fl = wl(f, "fresh_result") if len(f) else (0, 0)
        rows.append(dict(time_point=name, games=len(x), avg_move_from_open=round(x.shift_from_open.abs().mean(), 2) if len(x) else np.nan,
                         kept_bets=len(k), kept_W=kw, kept_L=kl, kept_win_pct=round(kw / (kw + kl), 3) if kw + kl else np.nan,
                         kept_units=round(k.kept_profit.sum(), 2) if len(k) else 0.0,
                         kept_avg_edge_left=round(k.kept_edge.mean(), 2) if len(k) else np.nan,
                         fresh_bets=len(f), fresh_W=fw, fresh_L=fl, fresh_win_pct=round(fw / (fw + fl), 3) if fw + fl else np.nan,
                         fresh_units=round(f.fresh_profit.sum(), 2) if len(f) else 0.0))
    return pd.DataFrame(rows)
