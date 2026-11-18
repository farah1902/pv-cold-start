"""Write data/MANIFEST_sha256.csv: path, size and SHA-256 of every input file under data/.

The data themselves are not committed (about 1.6 GB). This manifest is committed instead, so any copy of the
data (local, Google Drive, a re-download) can be checked against the files the results were computed from.

Usage (from the repository root):
    python tools/make_data_manifest.py            # write the manifest
    python tools/make_data_manifest.py --check    # compare the files on disk with the committed manifest

The manifest is written all-or-nothing: to a temporary file first, then renamed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST = DATA / "MANIFEST_sha256.csv"
SKIP = {MANIFEST.name, "README.md"}  # files at data/ top level that describe the data, not data


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def scan() -> list[dict]:
    rows = []
    for path in sorted(DATA.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(DATA).as_posix()
        if path.parent == DATA and path.name in SKIP:
            continue
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return rows


def write(rows: list[dict]) -> None:
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, MANIFEST)


def check(rows: list[dict]) -> int:
    with MANIFEST.open(encoding="utf-8") as f:
        ref = {r["path"]: r for r in csv.DictReader(f)}
    now = {r["path"]: r for r in rows}
    bad = 0
    for p in sorted(set(ref) | set(now)):
        if p not in now:
            print(f"MISSING  {p}"); bad += 1
        elif p not in ref:
            print(f"NEW      {p}"); bad += 1
        elif ref[p]["sha256"] != now[p]["sha256"]:
            print(f"CHANGED  {p}"); bad += 1
    print(f"{len(now)} files on disk, {len(ref)} in manifest, {bad} differences")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare disk with the committed manifest")
    args = ap.parse_args()
    rows = scan()
    if args.check:
        return check(rows)
    write(rows)
    total = sum(r["bytes"] for r in rows)
    print(f"Wrote {MANIFEST.relative_to(ROOT).as_posix()}: {len(rows)} files, {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
