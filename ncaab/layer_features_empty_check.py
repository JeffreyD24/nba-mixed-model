# Nov 6, 2026 (Fable fix check): a season with no box scores (no players files) must give NaN roster/lineup columns, not an error. Branch f6230eb raised AttributeError here.
#   python ncaab/layer_features_empty_check.py WORKDIR -> ncaab/research/layer_features_empty_check_output.txt
import sys, importlib.util, pandas as pd
W = sys.argv[1]
spec = importlib.util.spec_from_file_location("lf", W + "/ncaab/layer_features.py"); lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
X = pd.DataFrame([dict(espn_id=999999991, season=2029, date="2028-11-03", hk="2", ak="8", neutral=False, city="Auburn", state="AL")])
F = lf.build(W, [2029], extra=X)   # no players_2028/2029 files: roster and lineup passes have nothing
print(F.T.to_string()); print("diffs:", lf.diffs(F).tolist())
