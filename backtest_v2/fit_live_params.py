"""
Fit Models 2 and 3 on all five training seasons (2021-22..2025-26), the same seasons Model 1 uses live,
choose the half-life on 2025-26, and save everything the live tracker needs to walk forward through 2026-27.
Also saves last season's minutes per player (for projected minutes) and the team-id -> code map.
"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/work")
from models_v2 import load, PlayerModel, PaceModel, export_params, HALFLIVES
from lineups import prepare_box, LineupBuilder

W = "/home/claude/work/"
OUT = "/home/claude/nba-mixed-model/data/"
TRAIN = [2022, 2023, 2024, 2025, 2026]
G, lu = load()
params = {}
for mid, cls in (("2", PlayerModel), ("3", PaceModel)):
    M = cls(G, lu).fit(TRAIN)
    tune = {}
    for hl in HALFLIVES:
        P = M.walk(2026, hl)
        tune[str(hl)] = float(((P.pred_margin - (P.home_pts - P.away_pts)) ** 2).mean() + ((P.pred_total - (P.home_pts + P.away_pts)) ** 2).mean())
    best = min(HALFLIVES, key=lambda h: tune[str(h)])
    print(f"model {mid} half-life tuning on 2025-26: {tune} -> {best}", flush=True)
    params[mid] = export_params(M, best)
    params[mid]["tuning"] = tune
json.dump(params, open(OUT + "models_v2_params.json", "w"), indent=1, default=float)

# last season's average minutes (games he was available for) and team codes
codes = pd.read_csv(W + "team_codes.csv", index_col=0).code.to_dict(); code2tid = {c: t for t, c in codes.items()}
P = pd.read_parquet(W + "players_min.parquet"); P["date"] = P.d.dt.normalize()
rep = pd.read_csv(W + "injury_reports_parsed.csv")
box = prepare_box(P, rep, code2tid)
reg = box[box.reg & ~box.absent & (box.season == 2026)]
m = reg.groupby("personId").agg(mpg=("MIN", "mean"), games=("MIN", "size"),
                                name=("k", lambda s: s.mode()[0])).reset_index()
m.to_csv(OUT + "last_season_minutes_2025_26.csv", index=False)
pd.Series(codes, name="code").rename_axis("team_id").to_csv(OUT + "team_codes.csv")
print("saved", len(m), "players' minutes and", len(codes), "team codes")
