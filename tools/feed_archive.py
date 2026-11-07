"""Keep the repo small: move raw feed days older than KEEP_DAYS out of the checkout into GitHub Release archives (Jeffrey, Nov 7, 2026).
Nothing is deleted: each day becomes one file feed_<YYYY-MM-DD>.tar.gz (every research/feed/**/<date>/ folder of that day) attached to the
release tagged feed-archive-<YYYY-MM> in this repo. The upload is downloaded back and checked byte for byte (sha256) BEFORE the day's
folders are removed from main. Git history still has every file; this only keeps checkouts (Actions, new sessions) fast.

  python tools/feed_archive.py archive [--keep-days 21] [--dry-run] [--no-delete] [--tag-prefix feed-archive]
  python tools/feed_archive.py restore --from 2026-11-01 [--to 2026-11-30] [--dest .]   # puts the files back under research/feed/
  python tools/feed_archive.py list

Uses the GitHub REST API: plain HTTPS with GH_TOKEN in Actions (no gh CLI needed); the gh CLI from Claude sessions (GraphQL is blocked there).
Same file in nba-, nhl- and nfl-mixed-model. Weekly workflow: .github/workflows/feed-archive.yml.
"""
import os, sys, re, glob, json, hashlib, tarfile, subprocess, tempfile, argparse, datetime as dt

W = os.getcwd()
FEED = os.path.join(W, "research", "feed")


def repo():
    r = os.environ.get("GITHUB_REPOSITORY")
    if r: return r
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    return re.sub(r"\.git$", "", url.split("github.com/")[-1])


def gh(args, data=None, binary=False):
    """GitHub REST call. In Actions (GH_TOKEN / GITHUB_TOKEN set): plain HTTPS with the token, no gh CLI needed (the Oracle runner has none).
    Elsewhere (Claude sessions): through the gh CLI. args follow `gh api` style: [-X METHOD] [-H "K: V"]... [--input FILE|-] PATH_OR_URL"""
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        p = subprocess.run(["gh", "api"] + args, input=data, capture_output=True)
        if p.returncode != 0:
            raise RuntimeError(f"gh api {' '.join(a for a in args if not a.startswith('-H'))[:120]} failed: {p.stderr.decode()[:300]}")
        return p.stdout if binary else (json.loads(p.stdout) if p.stdout.strip() else {})
    import urllib.request, urllib.error
    method, hdr, body, path, i = "GET", {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, None, None, 0
    while i < len(args):
        a = args[i]
        if a == "-X": method = args[i + 1]; i += 2
        elif a == "-H": k, v = args[i + 1].split(":", 1); hdr[k.strip()] = v.strip(); i += 2
        elif a == "--input": body = data if args[i + 1] == "-" else open(args[i + 1], "rb").read(); i += 2
        else: path = a; i += 1
    url = path if path.startswith("http") else f"https://api.github.com/{path}"
    req = urllib.request.Request(url, data=body, method=method, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=300) as r: out = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url[:120]} failed: HTTP {e.code} {e.read()[:200]}")
    return out if binary else (json.loads(out) if out.strip() else {})


def release(tag, create=True):
    R = repo()
    try: return gh([f"repos/{R}/releases/tags/{tag}"])
    except RuntimeError as e:
        if "404" not in str(e) and "Not Found" not in str(e): raise
        if not create: return None
        body = json.dumps({"tag_name": tag, "name": f"Feed archive {tag.split('-')[-2]}-{tag.split('-')[-1]}",
                           "body": "Raw odds/props feed days moved out of the main checkout (tools/feed_archive.py). One file per day; "
                                   "restore with: python tools/feed_archive.py restore --from YYYY-MM-DD", "draft": False, "prerelease": False})
        return gh(["-X", "POST", f"repos/{R}/releases", "--input", "-"], data=body.encode())


def day_dirs():
    out = {}
    for d in glob.glob(os.path.join(FEED, "**", "20??-??-??"), recursive=True):
        if os.path.isdir(d): out.setdefault(os.path.basename(d), []).append(d)
    return dict(sorted(out.items()))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def archive(a):
    cutoff = (dt.date.today() - dt.timedelta(days=a.keep_days)).isoformat()
    days = {d: v for d, v in day_dirs().items() if d < cutoff}
    print(f"feed days older than {cutoff}: {len(days)}")
    moved = []
    for day, dirs in days.items():
        tag = f"{a.tag_prefix}-{day[:7]}"; name = f"feed_{day}.tar.gz"
        files = sum(len(os.listdir(d)) for d in dirs)
        if a.dry_run:
            print(f"  would archive {day}: {len(dirs)} folders, {files} files -> release {tag} / {name}"); continue
        rel = release(tag)
        tmp = tempfile.mkdtemp(); tp = os.path.join(tmp, name)
        with tarfile.open(tp, "w:gz") as t:
            for d in dirs: t.add(d, arcname=os.path.relpath(d, W))
        want = sha(tp)
        old = [x for x in rel.get("assets", []) if x["name"] == name]
        for x in old:                                     # an earlier partial run: replace it
            gh(["-X", "DELETE", f"repos/{repo()}/releases/assets/{x['id']}"])
        up = f"https://uploads.github.com/repos/{repo()}/releases/{rel['id']}/assets?name={name}"
        asset = gh(["-X", "POST", up, "-H", "Content-Type: application/gzip", "--input", tp])
        back = gh(["-H", "Accept: application/octet-stream", f"repos/{repo()}/releases/assets/{asset['id']}"], binary=True)
        got = hashlib.sha256(back).hexdigest()
        if got != want:
            print(f"  {day}: CHECK FAILED (sha256 differs); folders kept"); continue
        print(f"  {day}: {len(dirs)} folders, {files} files, {os.path.getsize(tp) / 1e6:.1f} MB -> {tag}/{name} (verified)")
        if not a.no_delete:
            subprocess.run(["git", "rm", "-r", "-q", "--"] + [os.path.relpath(d, W) for d in dirs], check=True)
            moved.append(day)
    print(f"archived and removed from the checkout: {len(moved)} days" + (f" ({moved[0]} .. {moved[-1]})" if moved else ""))


def restore(a):
    d0 = dt.date.fromisoformat(a.frm); d1 = dt.date.fromisoformat(a.to) if a.to else dt.date.today()
    months = sorted({(d0 + dt.timedelta(days=i)).isoformat()[:7] for i in range((d1 - d0).days + 1)})
    n = 0
    for m in months:
        rel = release(f"{a.tag_prefix}-{m}", create=False)
        if not rel: continue
        for x in rel.get("assets", []):
            mm = re.match(r"feed_(\d{4}-\d{2}-\d{2})\.tar\.gz$", x["name"])
            if not mm or not (d0.isoformat() <= mm.group(1) <= d1.isoformat()): continue
            b = gh(["-H", "Accept: application/octet-stream", f"repos/{repo()}/releases/assets/{x['id']}"], binary=True)
            tp = os.path.join(tempfile.mkdtemp(), x["name"]); open(tp, "wb").write(b)
            with tarfile.open(tp) as t:
                for mem in t.getmembers():                # only plain files under research/feed
                    if not mem.name.startswith("research/feed/") or ".." in mem.name or not (mem.isfile() or mem.isdir()):
                        raise RuntimeError(f"unexpected path in archive: {mem.name}")
                t.extractall(a.dest)
            n += 1
    print(f"restored {n} days into {os.path.join(a.dest, 'research', 'feed')}")


def delete_release(a):
    """remove a release and its tag (used by the workflow's self-test to clean up feed-archive-test-*)"""
    rel = release(a.tag, create=False)
    if not rel: print("no such release", a.tag); return
    gh(["-X", "DELETE", f"repos/{repo()}/releases/{rel['id']}"])
    gh(["-X", "DELETE", f"repos/{repo()}/git/refs/tags/{a.tag}"])
    print("deleted release and tag", a.tag)


def lst(a):
    for r in gh([f"repos/{repo()}/releases?per_page=100"]):
        if r["tag_name"].startswith(a.tag_prefix):
            print(r["tag_name"], len(r["assets"]), "days", f"{sum(x['size'] for x in r['assets']) / 1e6:.1f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["archive", "restore", "list", "delete-release"])
    ap.add_argument("--keep-days", type=int, default=21)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--no-delete", action="store_true")
    ap.add_argument("--tag-prefix", default="feed-archive")
    ap.add_argument("--from", dest="frm"); ap.add_argument("--to"); ap.add_argument("--dest", default="."); ap.add_argument("--tag")
    a = ap.parse_args()
    {"archive": archive, "restore": restore, "list": lst, "delete-release": delete_release}[a.cmd](a)
