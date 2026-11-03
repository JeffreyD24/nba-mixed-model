"""Clean the pre-scraped SportsbookReview archives (2011-2021 seasons) into tidy CSVs with quality flags.
Usage: python3 -I clean_sbr.py SRC_DIR OUT_DIR   (SRC_DIR holds {sport}_archive_10Y.json)
Nothing is dropped silently: bad rows keep their raw values and get *_ok = 0; repaired rows get *_repaired = 1."""
import json, sys
import numpy as np, pandas as pd
SRC, OUT = sys.argv[1], sys.argv[2]
RANGE = {"nba": dict(T=(150, 280), S=30), "nfl": dict(T=(25, 80), S=26)}
REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); REPORT.append(s)

def load(sport):
    d = pd.DataFrame(json.load(open(f"{SRC}/{sport}_archive_10Y.json")))
    n0 = len(d)
    str_ok = d.home_team.apply(lambda x: isinstance(x, str)) & d.away_team.apply(lambda x: isinstance(x, str))
    d = d[str_ok].copy()
    say(f"[{sport}] rows {n0}; dropped {n0 - len(d)} with a non-text team name (scrambled playoff rows)")
    d["date"] = pd.to_datetime(d["date"].astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
    d = d[d.date.notna()].copy()
    for c in d.columns:
        if c not in ("home_team", "away_team", "date"): d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.drop_duplicates(["date", "home_team", "away_team", "home_final", "away_final"]).copy()
    return d

def clean_spread_total(d, sport):
    lo, hi = RANGE[sport]["T"]; S = RANGE[sport]["S"]
    inT = lambda x: x.between(lo, hi)
    d["close_repaired"] = 0
    swapped = (~d.home_close_spread.abs().between(0, S)) & inT(d.home_close_spread.abs()) & d.close_over_under.abs().le(S)
    ml_fav = np.sign(d.home_close_ml.where(d.home_close_ml.abs() >= 100))     # -1 = home favourite
    sign = (-1 * (ml_fav < 0) + 1 * (ml_fav > 0)).replace(0, np.nan)
    sign = sign.fillna(np.sign(d.home_open_spread).replace(0, 1))
    newtot = d.home_close_spread.abs(); newsp = d.close_over_under.abs() * sign
    d.loc[swapped, ["home_close_spread", "close_over_under"]] = np.c_[newsp[swapped], newtot[swapped]]
    d.loc[swapped, "close_repaired"] = 1
    d["away_close_spread"] = -d.home_close_spread
    d["open_ok"] = (d.home_open_spread.abs().le(S) & inT(d.open_over_under)).astype(int)
    d["close_ok"] = (d.home_close_spread.abs().le(S) & inT(d.close_over_under)).astype(int)
    say(f"[{sport}] closing spread/total columns were swapped in {int(swapped.sum())} rows ({swapped.mean():.1%}); repaired, sign taken from the closing moneyline (else the opening spread)")
    say(f"[{sport}] still unusable after repair: open {int((1 - d.open_ok).sum())}, close {int((1 - d.close_ok).sum())}")
    rep = d[d.close_repaired == 1]; okk = d[(d.close_repaired == 0) & (d.open_ok == 1) & (d.close_ok == 1)]
    say(f"[{sport}] check, mean |close - open spread|: normal rows {(okk.home_close_spread - okk.home_open_spread).abs().mean():.2f}, repaired rows {(rep.home_close_spread - rep.home_open_spread).abs().mean():.2f} (should be similar); "
        f"mean |close - open total|: normal {(okk.close_over_under - okk.open_over_under).abs().mean():.2f}, repaired {(rep.close_over_under - rep.open_over_under).abs().mean():.2f}")
    say(f"[{sport}] check, share of repaired rows where the repaired spread's sign matches the opening spread's sign: {(np.sign(rep.home_close_spread) == np.sign(rep.home_open_spread)).mean():.1%} (normal rows: {(np.sign(okk.home_close_spread) == np.sign(okk.home_open_spread)).mean():.1%})")
    # trusted flags: what to use for backtests (repaired rows cluster in pick'em games and often carry an opening spread of 0.0)
    d["spread_trusted"] = ((d.open_ok == 1) & (d.close_ok == 1) & (d.close_repaired == 0)).astype(int)
    d["total_trusted"] = ((d.open_ok == 1) & (d.close_ok == 1) & ((d.close_over_under - d.open_over_under).abs() <= 15)).astype(int)
    say(f"[{sport}] trusted for spread backtests: {int(d.spread_trusted.sum())} of {len(d)}; trusted for totals: {int(d.total_trusted.sum())}")
    return d

for sport in ("nba", "nfl"):
    d = clean_spread_total(load(sport), sport)
    keep = ["season", "date", "home_team", "away_team", "home_final", "away_final", "home_open_spread", "home_close_spread", "open_over_under",
            "close_over_under", "home_close_ml", "away_close_ml", "open_ok", "close_ok", "close_repaired", "spread_trusted", "total_trusted"]
    d[keep].sort_values("date").to_csv(f"{OUT}/sbr_{sport}_2011_2021_clean.csv.gz", index=False)
    say(f"[{sport}] wrote {len(d)} games; usable with opening line {int(d.open_ok.sum())}, with closing line {int(d.close_ok.sum())}; seasons {sorted(d.season.unique())}")
    say(f"[{sport}] games per season: {d.groupby('season').size().to_dict()}")

for sport, (lo, hi) in {"nhl": (3.5, 9.5), "mlb": (4.5, 16.5)}.items():
    d = load(sport)
    for tag in ("open", "close"):
        d[f"{tag}_total_ok"] = d[f"{tag}_over_under"].between(lo, hi).astype(int)
        d[f"{tag}_ml_ok"] = (d.get(f"home_{tag}_ml").abs().ge(100) & d.get(f"away_{tag}_ml").abs().ge(100)).astype(int) if f"home_{tag}_ml" in d else 0
    say(f"[{sport}] open total unusable {int((1 - d.open_total_ok).sum())}, close total unusable {int((1 - d.close_total_ok).sum())}, open ml unusable {int((1 - d.open_ml_ok).sum())}, close ml unusable {int((1 - d.close_ml_ok).sum())} of {len(d)}")
    d.sort_values("date").to_csv(f"{OUT}/sbr_{sport}_2011_2021_clean.csv.gz", index=False)
    say(f"[{sport}] games per season: {d.groupby('season').size().to_dict()}")
open(f"{OUT}/sbr_cleaning_report.txt", "w").write("\n".join(REPORT) + "\n")
