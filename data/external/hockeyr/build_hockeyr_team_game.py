"""Team-game expected-goals table from hockeyR-data play-by-play (lite files). Derived, aggregated facts only; raw files are not redistributed.
Usage: python3 -I build_hockeyr_team_game.py DATA_DIR OUT_CSV_GZ
One row per team per game: goals, xG for/against (all strengths, 5v5, power play), shot attempts, shots on goal, plus the game's final score for checking.
xG is hockeyR's own model (unblocked shots only). Event types: SHOT (on goal, saved), GOAL, MISSED_SHOT, BLOCKED_SHOT."""
import glob, os, sys
import numpy as np, pandas as pd
SRC, OUT = sys.argv[1], sys.argv[2]
COLS = ["game_id", "season", "season_type", "game_date", "event_type", "event_team_type", "xg", "strength_state", "home_name", "away_name", "home_final", "away_final", "period"]
UNBLOCKED = {"SHOT", "GOAL", "MISSED_SHOT"}; ATT = UNBLOCKED | {"BLOCKED_SHOT"}
parts = []
for f in sorted([p for p in glob.glob(os.path.join(SRC, "play_by_play_20*_lite.csv.gz")) if not p.endswith("2023_24_lite.csv.gz")]):
    d = pd.read_csv(f, encoding="latin-1", usecols=lambda c: c in COLS, low_memory=False)
    d = d[d.event_type.isin(ATT) & d.event_team_type.isin(["home", "away"])].copy()
    d["xg"] = d.xg.fillna(0.0); d["is5v5"] = (d.strength_state == "5v5"); d["unb"] = d.event_type.isin(UNBLOCKED)
    d["pp"] = d.event_team_type.eq("home") & d.strength_state.str[0].gt(d.strength_state.str[-1]) | d.event_team_type.eq("away") & d.strength_state.str[0].lt(d.strength_state.str[-1])
    ginfo = d.drop_duplicates("game_id").set_index("game_id")[["season", "season_type", "game_date", "home_name", "away_name", "home_final", "away_final"]]
    for side in ("home", "away"):
        for who, tag in ((side, "f"), ("away" if side == "home" else "home", "a")):
            m = d[d.event_team_type == who]
            g = m.groupby("game_id")
            t = pd.DataFrame({f"xg_all_{tag}": g.xg.sum(), f"xg_5v5_{tag}": m[m.is5v5].groupby("game_id").xg.sum(), f"xg_pp_{tag}": m[m.pp].groupby("game_id").xg.sum(),
                              f"att_{tag}": g.size(), f"att_5v5_{tag}": m[m.is5v5].groupby("game_id").size(), f"sog_{tag}": m[m.event_type.isin(["SHOT", "GOAL"])].groupby("game_id").size(),
                              f"goals_{tag}": m[m.event_type == "GOAL"].groupby("game_id").size()})
            ginfo = ginfo.join(t.add_prefix(side + "_"), how="left")
    parts.append(ginfo.reset_index())
H = pd.concat(parts, ignore_index=True).drop_duplicates("game_id")
num = [c for c in H.columns if c.startswith(("home_", "away_")) and c not in ("home_name", "away_name", "home_final", "away_final")]
H[num] = H[num].fillna(0.0)
rows = []
for side, opp in (("home", "away"), ("away", "home")):
    r = pd.DataFrame({"game_id": H.game_id, "season": H.season, "season_type": H.season_type, "game_date": H.game_date, "team": H[f"{side}_name"], "opp": H[f"{opp}_name"], "is_home": int(side == "home"),
                      "final_for": H[f"{side}_final"], "final_against": H[f"{opp}_final"]})
    for k in ("xg_all", "xg_5v5", "xg_pp", "att", "att_5v5", "sog", "goals"):
        r[f"{k}_for"] = H[f"{side}_{k}_f"].round(4) if k.startswith("xg") else H[f"{side}_{k}_f"]
        r[f"{k}_against"] = H[f"{side}_{k}_a"].round(4) if k.startswith("xg") else H[f"{side}_{k}_a"]
    rows.append(r)
T = pd.concat(rows, ignore_index=True).sort_values(["game_date", "game_id", "is_home"], ascending=[True, True, False])
T["goals_match_final"] = (T.goals_for == T.final_for).astype(int)
T.to_csv(OUT, index=False)
print("rows", len(T), "games", T.game_id.nunique())
print("games per season type:", H.groupby(["season", "season_type"]).size().unstack(fill_value=0).to_string())
print("share of team rows where counted goals equal the final score: %.3f" % T.goals_match_final.mean())
print("mean xG per team per game (all / 5v5):", T.xg_all_for.mean().round(3), T.xg_5v5_for.mean().round(3), "| mean goals:", T.goals_for.mean().round(3))
print("by season mean xG vs goals:\n", T.groupby("season")[["xg_all_for", "goals_for"]].mean().round(3).to_string())
