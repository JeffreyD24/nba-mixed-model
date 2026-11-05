"""Live sharp-money tracker, all five leagues (Nov 5, 2026; betting-goals SHARP_MONEY.md). About every minute (sharp/live_loop.sh inside workflow sharp-live.yml, Nov 5: was every 10 min):
1. Action Network: consensus betting splits (% of bets, % of money, number of bets) and lines at the Open book, Consensus, DraftKings, FanDuel
   (plus sharp books whenever Action Network returns them) for today's and tomorrow's games -> sharp/live/{sport}/{date}.csv, a row only when
   something changed (so the file is the timeline of WHEN money and lines moved).
2. Signals per game -> sharp/live/{sport}/signals_{date}.csv: money gap now and when it first reached 10, DraftKings' move since first seen,
   reverse line move (line moved toward the side with fewer bets), steam (DraftKings, FanDuel and Consensus all moved >= 1 pt the same way
   within 30 minutes). Recorded only; nothing here changes an alert (Q3 in sharp/signals_output.txt: archive splits near tip flag our losing
   NBA totals bets, so the question is whether that money shows up EARLY).
  python sharp/live_capture.py WORKDIR"""
import os, sys, json, time, urllib.request
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); OUT = os.path.join(W, "sharp", "live")
BOOKS = {15: "cons", 30: "open", 68: "dk", 69: "fd", 1: "betonline", 3: "pinnacle", 78: "circa", 34: "bookmaker", 14: "westgate", 21: "bovada"}
NOW = pd.Timestamp.now(tz="America/New_York").tz_localize(None).floor("min")
def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=30) as r: return json.loads(r.read())
        except Exception: time.sleep(2 + 2 * i)
    return {}
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return np.nan
def snap(sport):
    q = [f"date={d:%Y%m%d}" for d in (NOW, NOW + pd.Timedelta(days=1))] if sport in ("nba", "nhl", "ncaab") else [""]
    div = {"ncaab": "&division=D1", "ncaaf": "&division=FBS"}.get(sport, "")
    rows = []
    for qq in q:
        js = get(f"https://api.actionnetwork.com/web/v2/scoreboard/{sport}?bookIds={','.join(map(str, BOOKS))}{div}&{qq}")
        for g in js.get("games", []):
            if g.get("status") != "scheduled": continue
            t = {x["id"]: x for x in g.get("teams", [])}
            base = dict(seen_at=str(NOW), an_id=g["id"], start=g.get("start_time"), home=t.get(g["home_team_id"], {}).get("full_name"),
                        away=t.get(g["away_team_id"], {}).get("full_name"), num_bets=g.get("num_bets"))
            for bid, m in (g.get("markets") or {}).items():
                ev = (m or {}).get("event") or {}; b = BOOKS.get(int(bid), str(bid))
                pk = lambda mk, sd: next((o for o in ev.get(mk, []) if o.get("side") == sd and not o.get("is_alt_market")), {}) or {}
                hs, ov, hm, am = pk("spread", "home"), pk("total", "over"), pk("moneyline", "home"), pk("moneyline", "away")
                r = dict(base, book=b, spread=num(hs.get("value")), spread_px=num(hs.get("odds")), total=num(ov.get("value")), over_px=num(ov.get("odds")),
                         ml_home=num(hm.get("odds")), ml_away=num(am.get("odds")))
                bi = lambda o, k: num(((o.get("bet_info") or {}).get(k) or {}).get("percent"))
                if b == "cons":
                    r.update(sp_home_bets=bi(hs, "tickets"), sp_home_money=bi(hs, "money"), over_bets=bi(ov, "tickets"), over_money=bi(ov, "money"),
                             ml_home_bets=bi(hm, "tickets"), ml_home_money=bi(hm, "money"))
                rows.append(r)
    return pd.DataFrame(rows)
KEYS = ["spread", "spread_px", "total", "over_px", "ml_home", "ml_away", "sp_home_bets", "sp_home_money", "over_bets", "over_money"]
def signals(H):
    out = []
    for gid, g in H.groupby("an_id"):
        c = g[g.book == "cons"].sort_values("seen_at"); dk = g[g.book == "dk"].sort_values("seen_at")
        r = dict(an_id=gid, start=g.start.iloc[-1], home=g.home.iloc[-1], away=g.away.iloc[-1], snapshots=len(g))
        for mk, mcol, bcol, lcol in (("spread", "sp_home_money", "sp_home_bets", "spread"), ("total", "over_money", "over_bets", "total")):
            if len(c) and mcol in c:
                gap = c[mcol] - c[bcol]; r[f"{mk}_gap_now"] = gap.iloc[-1]; hit = c.seen_at[gap.abs() >= 10]
                r[f"{mk}_gap10_first_at"] = hit.iloc[0] if len(hit) else None; r[f"{mk}_gap10_side"] = (np.sign(gap[gap.abs() >= 10].iloc[0]) if len(hit) else 0)
                r[f"{mk}_bets_pct_now"] = c[bcol].iloc[-1]
            if len(dk) and dk[lcol].notna().any():
                d = dk[dk[lcol].notna()]; mv = d[lcol].iloc[-1] - d[lcol].iloc[0]; r[f"dk_{mk}_first"] = d[lcol].iloc[0]; r[f"dk_{mk}_now"] = d[lcol].iloc[-1]
                r[f"dk_{mk}_first_at"] = d.seen_at.iloc[0]; r[f"dk_{mk}_move"] = mv
                # reverse line move: spread moving toward home (mv < 0) while home has < 50% of bets, or toward away while home > 50%; totals: up with < 50% overs
                bp = r.get(f"{mk}_bets_pct_now", np.nan); thr = 1.0 if mk == "spread" else 1.5
                if mk == "spread": r["spread_rlm"] = int((mv <= -thr and bp < 50) or (mv >= thr and bp > 50))
                else: r["total_rlm"] = int((mv >= thr and bp < 50) or (mv <= -thr and bp > 50))
            # steam: DK, FD and Consensus each moved >= 1 pt the same way within 30 minutes
            st = 0; mvs = {}
            for b, gb in g[g.book.isin(["dk", "fd", "cons"])].sort_values("seen_at").groupby("book"):
                gb = gb[gb[lcol].notna()]; ts = pd.to_datetime(gb.seen_at)
                for i in range(1, len(gb)):
                    dlt = gb[lcol].iloc[i] - gb[lcol].iloc[i - 1]
                    if abs(dlt) >= 1: mvs.setdefault(b, []).append((ts.iloc[i], np.sign(dlt)))
            if len(mvs) == 3:
                for t0, s0 in mvs["dk"]:
                    if all(any(abs((t - t0).total_seconds()) <= 1800 and s == s0 for t, s in mvs[b]) for b in ("fd", "cons")): st = 1; r[f"{mk}_steam_at"] = str(t0)
            r[f"{mk}_steam"] = st
        out.append(r)
    return pd.DataFrame(out)
if __name__ == "__main__":
    for sport in ("nba", "nhl", "nfl", "ncaab", "ncaaf"):
        try:
            S = snap(sport)
        except Exception as ex:
            print(sport, "capture failed:", type(ex).__name__); continue
        if S.empty: print(sport, "no scheduled games"); continue
        d = os.path.join(OUT, sport); os.makedirs(d, exist_ok=True); f = os.path.join(d, f"{NOW.date()}.csv")
        old = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame(columns=S.columns)
        last = old.sort_values("seen_at").drop_duplicates(["an_id", "book"], keep="last").set_index(["an_id", "book"]) if len(old) else None
        def changed(r):
            key = (int(r["an_id"]), str(r["book"]))
            if last is None or key not in last.index: return True
            p = last.loc[key]
            return any(not (pd.isna(r.get(k)) and pd.isna(p.get(k))) and r.get(k) != p.get(k) for k in KEYS if k in S.columns)
        if last is not None: last.index = pd.MultiIndex.from_arrays([last.index.get_level_values(0).astype(int), last.index.get_level_values(1).astype(str)])
        new = S[[changed(r) for _, r in S.iterrows()]] if len(S) else S
        H = pd.concat([old, new], ignore_index=True); H.to_csv(f, index=False)
        # signals over the last 3 capture days (games can be seen days ahead)
        files = sorted(x for x in os.listdir(d) if x[:4].isdigit())[-3:]
        A = pd.concat([pd.read_csv(os.path.join(d, x)) for x in files], ignore_index=True)
        if "--no-signals" not in sys.argv: signals(A).to_csv(os.path.join(d, f"signals_{NOW.date()}.csv"), index=False)
        print(f"{sport}: {len(S)} book rows, {len(new)} changed, books seen {sorted(S.book.astype(str).unique())}")
