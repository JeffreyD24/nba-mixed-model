"""Check (Nov 5, 2026): ncaab/layer_features.py reproduces the research features exactly, (1) for whole seasons, and (2) in LIVE mode:
for sample dates, drop that day's games (and everything after) from the data, re-add them as 'scheduled' games with only their venue, and
compare the features the live path gives them with the research values.
  python ncaab/layer_features_check.py WORKDIR RESEARCH_DERIVED_DIR -> ncaab/research/layer_features_check_output.txt"""
import os, sys, importlib.util, shutil, tempfile
import numpy as np, pandas as pd
W, RD = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
spec = importlib.util.spec_from_file_location("lf", os.path.join(W, "ncaab", "layer_features.py")); lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
REF = pd.read_csv(os.path.join(RD, "lineup_travel_features.csv.gz")).merge(pd.read_csv(os.path.join(RD, "roster_features.csv.gz")).drop(columns=["season"]), on="espn_id")
COLS = [f"{s}_{c}" for s in "ha" for c in lf.LF + lf.RF]
def compare(F, tag):
    m = F.merge(REF, on="espn_id", suffixes=("", "_ref")); worst = 0.0; bad = 0
    for c in COLS:
        a, b = m[c].values.astype(float), m[c + "_ref"].values.astype(float)
        both_nan = np.isnan(a) & np.isnan(b); d = np.where(both_nan, 0.0, np.abs(a - b)); d[np.isnan(d)] = np.inf
        worst = max(worst, d.max()); bad += int((d > 1e-6).sum())
    print(f"[{tag}] games {len(m)} | columns {len(COLS)} | max abs difference {worst:.2e} | cells differing {bad}")
    return bad
bad = compare(lf.build(W, [2026]), "full season 2025-26")
# live-mode replay: data as it stood before each date; that date's games given as scheduled games (venue only)
G = pd.read_csv(os.path.join(W, "ncaab", "data", "all_games.csv"), low_memory=False)
for day in ("2025-11-21", "2026-01-14", "2026-02-21"):
    tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "ncaab", "data", "box"))
    g = G.copy(); today = g[g.date == day]; g = g[g.date < day]
    g.to_csv(os.path.join(tmp, "ncaab", "data", "all_games.csv"), index=False)
    for f in os.listdir(os.path.join(W, "ncaab", "data", "box")):
        s = int(f.split("_")[1][:4])
        if s not in (2025, 2026): continue
        b = pd.read_csv(os.path.join(W, "ncaab", "data", "box", f)); b = b[b.espn_id.isin(g.espn_id) | (s == 2025)]
        b.to_csv(os.path.join(tmp, "ncaab", "data", "box", f), index=False, compression="gzip")
    for s in range(2008, 2025):  # earlier seasons' team files only feed home-base fallbacks; copy them unchanged
        for k in ("teams",):
            src = os.path.join(W, "ncaab", "data", "box", f"{k}_{s}.csv.gz")
            if os.path.exists(src): shutil.copy(src, os.path.join(tmp, "ncaab", "data", "box"))
    T = pd.read_csv(os.path.join(W, "ncaab", "data", "box", "teams_2026.csv.gz")).drop_duplicates("espn_id").set_index("espn_id")
    X = today[["espn_id", "season", "date", "hk", "ak", "neutral"]].copy()
    X["city"] = X.espn_id.map(T.city); X["state"] = X.espn_id.map(T.state)
    X["neutral"] = X.neutral.astype(str).str.lower().isin(["true", "1", "1.0"])
    F = lf.build(tmp, [2026], extra=X); F = F[F.espn_id.isin(X.espn_id)]
    bad += compare(F, f"live replay {day} (scheduled games, data before that day)"); shutil.rmtree(tmp)
print("RESULT:", "IDENTICAL" if bad == 0 else f"{bad} differing cells")
