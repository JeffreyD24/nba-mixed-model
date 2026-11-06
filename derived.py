"""
Saved build products (Nov 5, 2026). Expensive intermediate files (walk-forward predictions, joined game tables) are kept in git
under derived/ so they are never rebuilt by accident. See derived/MANIFEST.md for what each file is and how it was built.

  python derived.py WORK            restore every derived/*.gz (and *.json) into WORK/_tmp/ where the scripts expect them
  python derived.py WORK --save     copy every known build product from WORK/_tmp/ into derived/ (gzipped), then update MANIFEST.md by hand

In a script:  import derived; derived.ensure(WORK, ["dk_holdout_2022.csv", ...])   # restores the files if _tmp/ lacks them
"""
import os, sys, glob, gzip, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "derived")
SAVE = ("props_features.csv", "rule_audit_R8.csv")   # NBA (Nov 5, 2026): add patterns as new build products are saved


def ensure(work, names=None):
    """put derived/<name>(.gz) into work/_tmp/<name> unless it is already there; returns the names that are still missing"""
    tmp = os.path.join(work, "_tmp"); os.makedirs(tmp, exist_ok=True)
    if names is None:
        names = [os.path.basename(p)[:-3] if p.endswith(".gz") else os.path.basename(p)
                 for p in glob.glob(os.path.join(D, "*")) if not p.endswith(".md")]
    missing = []
    for n in names:
        dst = os.path.join(tmp, n)
        if os.path.exists(dst): continue
        gz, raw = os.path.join(D, n + ".gz"), os.path.join(D, n)
        if os.path.exists(gz):
            with gzip.open(gz, "rb") as a, open(dst, "wb") as b: shutil.copyfileobj(a, b)
        elif os.path.exists(raw): shutil.copy(raw, dst)
        else: missing.append(n)
    return missing


def save(work):
    tmp = os.path.join(work, "_tmp"); os.makedirs(D, exist_ok=True); n = 0
    for pat in SAVE:
        for p in glob.glob(os.path.join(tmp, pat)):
            if p.endswith(".json"): shutil.copy(p, D)
            else:
                with open(p, "rb") as a, gzip.open(os.path.join(D, os.path.basename(p) + ".gz"), "wb", compresslevel=9) as b: shutil.copyfileobj(a, b)
            n += 1
    print(f"saved {n} files to derived/; add or update their rows in derived/MANIFEST.md")


if __name__ == "__main__":
    w = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else HERE)
    if "--save" in sys.argv: save(w)
    else:
        miss = ensure(w); print("restored derived/ into _tmp/" + (f"; missing: {miss}" if miss else ""))
