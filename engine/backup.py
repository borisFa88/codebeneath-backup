# -*- coding: utf-8 -*-
"""
Independent, git-free backup of the whole codebeneath site.
Boris's requirement: always keep an OLD backup in case something happens to git.

Creates a timestamped .zip of the site (excluding transient/vcs files) into a
SIBLING folder OUTSIDE the site tree, so a bad change inside the site can never
touch the backups. Keeps the most recent KEEP snapshots, prunes older ones.

  python backup.py            # take a snapshot now
  python backup.py --list     # list existing snapshots
"""
import os, sys, io, zipfile, datetime, pathlib, argparse

SITE = pathlib.Path(os.environ.get("CB_SITE_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
BACKUPS = pathlib.Path(os.environ.get("CB_BACKUP_DIR") or str(SITE.parent / "codebeneath-backups"))  # outside the site
# Offsite mirror: OneDrive auto-syncs to the cloud, so backups survive a dead machine.
_od = os.environ.get("OneDrive") or str(pathlib.Path.home() / "OneDrive")
OFFSITE = pathlib.Path(_od) / "codebeneath-backups" if pathlib.Path(_od).exists() else None
KEEP = 30                                                            # rolling snapshots to retain (both locations)
EXCLUDE_DIRS = {".git", "__pycache__", "_needs-review", "codebeneath-backups"}
EXCLUDE_EXT = {".pyc"}

def make():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = BACKUPS / f"codebeneath_{stamp}.zip"
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(SITE):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if pathlib.Path(f).suffix in EXCLUDE_EXT:
                    continue
                full = pathlib.Path(root) / f
                z.write(full, full.relative_to(SITE))
                n += 1
    size = out.stat().st_size / 1024 / 1024
    print(f"backup created: {out.name}  ({n} files, {size:.1f} MB)")
    _mirror(out)
    prune()
    return out

def _mirror(zip_path):
    if not OFFSITE:
        print("  (offsite: OneDrive not found, local backup only)"); return
    import shutil
    OFFSITE.mkdir(parents=True, exist_ok=True)
    dst = OFFSITE / zip_path.name
    if not dst.exists():
        shutil.copy2(zip_path, dst)
    print(f"  offsite mirror -> OneDrive/codebeneath-backups/{zip_path.name}")

def prune():
    for folder in [BACKUPS, OFFSITE]:
        if not folder or not folder.exists():
            continue
        snaps = sorted(folder.glob("codebeneath_*.zip"))
        old = snaps[:-KEEP] if len(snaps) > KEEP else []
        for p in old:
            p.unlink()
        if old:
            print(f"pruned {len(old)} old snapshot(s) in {folder.name}, keeping last {KEEP}")

def list_snaps():
    snaps = sorted(BACKUPS.glob("codebeneath_*.zip"))
    if not snaps:
        print("no backups yet at", BACKUPS); return
    print(f"{len(snaps)} snapshot(s) in {BACKUPS}:")
    for p in snaps[-15:]:
        size = p.stat().st_size / 1024 / 1024
        print(f"  {p.name}  ({size:.1f} MB)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        list_snaps()
    else:
        make()
