"""Compare the live constants in alert.py with config/thresholds.csv (the register of every betting threshold, with the date and
data each was chosen on). Prints any constant whose value differs, so a change without a register entry is visible.
Same file in all three repos.   python tools/check_thresholds.py WORKDIR"""
import os, sys, re, csv
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "alert.py")).read()
bad = 0
for r in csv.DictReader(open(os.path.join(W, "config", "thresholds.csv"))):
    if r["file"] != "alert.py": continue
    for name in re.findall(r"[A-Z][A-Z_]{2,}", r["parameter"]):
        m = re.search(rf"^{name}\s*=\s*([^#\n]+)", src, re.M)
        if not m: continue
        live = m.group(1).strip()
        try: same = abs(float(live) - float(r["value"])) < 1e-9
        except ValueError: same = True          # text values (on/off, lists) are described, not compared
        if not same:
            bad += 1; print(f"MISMATCH {name}: alert.py has {live}, register has {r['value']} (set {r['set_on']}). Update config/thresholds.csv.")
print("threshold register matches alert.py" if not bad else f"{bad} threshold(s) changed without a register entry")
