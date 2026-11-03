"""Rebuild MANIFEST.csv: every file under data/external (except .gitkeep) with size and sha256. Run: python3 -I make_manifest.py"""
import csv, hashlib, os
root = os.path.dirname(os.path.abspath(__file__))
LIC = {"sbr": ("sportsbookreview.com odds via FinnedAI scraper", "scraper MIT; odds belong to SBR; private research use", "https://github.com/FinnedAI/sportsbookreview-scraper"),
       "hockeyr": ("hockeyR / hockeyR-data", "code MIT; derived table ours; raw pbp unlicensed, not committed", "https://github.com/danmorse314/hockeyR"),
       "beatthebookie": ("BeatTheBookie", "code GPL-3.0; data license unstated, not committed", "https://github.com/Lisandro79/BeatTheBookie")}
rows = []
for d, (src, lic, url) in LIC.items():
    for dp, _, fs in os.walk(os.path.join(root, d)):
        for f in sorted(fs):
            if f == ".gitkeep": continue
            p = os.path.join(dp, f); h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            rows.append([os.path.relpath(p, root), d, src, lic, url, os.path.getsize(p), h])
with open(os.path.join(root, "MANIFEST.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["path","folder","source","license_note","url","bytes","sha256"]); w.writerows(sorted(rows))
print(len(rows), "files")
