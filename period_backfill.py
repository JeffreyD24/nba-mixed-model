"""
Backfill past NBA quarter / half / team-total lines and quarter scores from Action Network (free; no key).
For every NBA game date in data/odds_history/schedule.csv (2021-22 on) and every period (game, 1st half, 1st quarter, 2nd half):
  - the opener (Action Network's 'Open' book), consensus, DraftKings and FanDuel, as Action Network last saw them before the
    period started (for 'game', '1st half' and '1st quarter' that is the closing line; for '2nd half' it is the halftime line)
  - spread + both prices, total + both prices, moneyline, team totals (when listed)
  - quarter-by-quarter scores (and OT) from the box score
Probe (Nov 4, 2026): DK and FanDuel period lines exist from 2022-23 on (TBC per season in the output); 2021-22 has consensus only.

  python period_backfill.py WORKDIR [--from 2021-10-19] [--to 2026-04-12] [--max-dates 60]
Writes data/period_history/nba_period_lines.csv.gz and data/period_history/nba_linescores.csv; dates already saved are skipped
(data/period_history/nba_dates_done.txt).
"""
import os, sys, json, time, urllib.request
import numpy as np, pandas as pd
import espn

W = os.path.abspath(sys.argv[1])
ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = os.path.join(W, "data", "period_history"); os.makedirs(OUT, exist_ok=True)
LINES, SCORES, DONE = (os.path.join(OUT, f) for f in ("nba_period_lines.csv.gz", "nba_linescores.csv", "nba_dates_done.txt"))
BOOKS = {15: "Consensus", 30: "Open", 68: "DraftKings", 69: "FanDuel"}
PERIODS = ["game", "firsthalf", "firstquarter", "secondhalf"]
HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1: raise
            time.sleep(4 * (i + 1))


def num(x):
    try: return float(x)
    except Exception: return np.nan


def one_date(day):
    lines, scores = [], []
    for per in PERIODS:
        d = get(f"https://api.actionnetwork.com/web/v1/scoreboard/nba?period={per}&bookIds={','.join(map(str, BOOKS))}&date={day:%Y%m%d}")
        for g in d.get("games", []):
            if g.get("status") not in ("complete", "closed", "final"): continue
            t = {x["id"]: espn.ESPN2.get(x.get("abbr")) for x in g.get("teams", [])}
            home, away = t.get(g["home_team_id"]), t.get(g["away_team_id"])
            if not home or not away: continue
            for o in g.get("odds") or []:
                b = BOOKS.get(o.get("book_id"))
                if not b: continue
                lines.append(dict(date=str(day.date()), home=home, away=away, period=per, book=b,
                                  home_spread=num(o.get("spread_home")), home_spread_odds=num(o.get("spread_home_line")),
                                  away_spread_odds=num(o.get("spread_away_line")), total=num(o.get("total")),
                                  over_odds=num(o.get("over")), under_odds=num(o.get("under")),
                                  home_ml=num(o.get("ml_home")), away_ml=num(o.get("ml_away")),
                                  home_team_total=num(o.get("home_total")), home_tt_over=num(o.get("home_over")),
                                  home_tt_under=num(o.get("home_under")), away_team_total=num(o.get("away_total")),
                                  away_tt_over=num(o.get("away_over")), away_tt_under=num(o.get("away_under")),
                                  inserted=o.get("inserted")))
            if per == "game":
                ls = (g.get("boxscore") or {}).get("linescore") or []
                if ls:
                    r = dict(date=str(day.date()), home=home, away=away)
                    for q in ls:
                        k = str(q.get("abbr") or q.get("id")); r[f"away_q{k}"] = q.get("away_points"); r[f"home_q{k}"] = q.get("home_points")
                    r["away_final"] = sum(q.get("away_points") or 0 for q in ls); r["home_final"] = sum(q.get("home_points") or 0 for q in ls)
                    scores.append(r)
        time.sleep(0.6)
    return lines, scores


def main():
    S = pd.read_csv(os.path.join(W, "data", "odds_history", "schedule.csv"))
    dates = sorted(pd.to_datetime(S[S.sport == "nba"].date).unique())
    lo, hi = pd.Timestamp(ARG("--from", "2021-10-19")), pd.Timestamp(ARG("--to", "2026-04-12"))
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()
    todo = [d for d in dates if lo <= d <= hi and str(d.date()) not in done][: int(ARG("--max-dates", "60"))]
    if not todo:
        print("all dates already saved"); return
    L, Q = [], []
    for d in todo:
        try:
            l, q = one_date(pd.Timestamp(d))
        except Exception as e:
            print(f"{d.date()}: failed ({e}); will retry next run"); continue
        L += l; Q += q; done.add(str(pd.Timestamp(d).date()))
        print(f"{pd.Timestamp(d).date()}: {len(q)} games, {len(l)} line rows")
    if L:
        old = pd.read_csv(LINES) if os.path.exists(LINES) else pd.DataFrame()
        pd.concat([old, pd.DataFrame(L)], ignore_index=True).drop_duplicates(["date", "home", "away", "period", "book"], keep="last").to_csv(LINES, index=False)
    if Q:
        old = pd.read_csv(SCORES) if os.path.exists(SCORES) else pd.DataFrame()
        pd.concat([old, pd.DataFrame(Q)], ignore_index=True).drop_duplicates(["date", "home", "away"], keep="last").to_csv(SCORES, index=False)
    open(DONE, "w").write("\n".join(sorted(done)) + "\n")
    print(f"saved through {pd.Timestamp(todo[-1]).date()}")


if __name__ == "__main__":
    main()
