"""EXPLORATORY (added after the pre-registered line-move results): WHEN during game day does DraftKings price the news that ends up on the
pretip injury report? Share of the full (build-fitted) move in the line at fixed ET clock times, games with |news| >= 1.5 pts, all seasons."""
import os, numpy as np, pandas as pd
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *p: os.path.join(W, *p)
G = pd.read_csv(J("analysis", "line_move_model_games.csv.gz"))
S = pd.read_csv(J("data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "t", "tip", "book", "sp", "tot", "date"])
S = S[S.book == "draftkings"]; S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True); S = S[S.t < S.tip].sort_values("t")
key = ["date", "home", "away"]; S = S.merge(G[key + ["N_sp", "N_tot", "sp_open", "tot_open", "sp_close", "tot_close"]], on=key)
S["et"] = S.t.dt.tz_convert("America/New_York"); S["gday"] = pd.to_datetime(S.date).dt.tz_localize("America/New_York")
out = []; say = lambda s: (print(s), out.append(s))
for mk, N, slope, sign in (("sp", "N_sp", 0.750, -1), ("tot", "N_tot", 0.881, 1)):
    say(f"{mk.upper()} (|news| >= 1.5; share = move from open / (build slope x news)); clock times ET")
    s = S.dropna(subset=[mk]); s = s[s[N].abs() >= 1.5]
    for lab, hrs in (("10 PM night before", -2), ("7 AM", 7), ("10 AM", 10), ("noon", 12), ("2 PM", 14), ("4 PM", 16), ("6 PM", 18)):
        cut = s.gday + pd.to_timedelta(hrs, unit="h")
        last = s[s.et <= cut].groupby(key).tail(1)
        sh = sign * (last[mk] - last[f"{mk}_open"]) / (slope * last[N])
        say(f"  {lab:>18}: median {sh.median():5.0%}  mean {sh.clip(-3,3).mean():5.0%}  games {len(last)}")
    g = s.groupby(key).tail(1); sh = sign * (g[f"{mk}_close"] - g[f"{mk}_open"]) / (slope * g[N]); say(f"  {'close':>18}: median {sh.median():5.0%}  mean {sh.clip(-3,3).mean():5.0%}")
open(J("analysis", "line_move_timing_explore_output.txt"), "w").write("\n".join(out) + "\n")
