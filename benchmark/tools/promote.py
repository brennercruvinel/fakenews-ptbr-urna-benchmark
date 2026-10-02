#!/usr/bin/env python3
"""Promote a candidate build to release/<version>/<model>-<preset>/.

What a release dir holds:
  fakenews.urna       the artifact (gitignored, hosted on hugging face)
  chunk_map.parquet   chunk_id -> doc_id (gitignored, hosted on hugging face)
  build.lock.json     corpus, sources, model snapshot, preset, environment, output hashes
  manifest.json       what urna reads back from the file, plus timings
  SHA256SUMS          sha256 of the four files above
  CITATION_KEY        identity of the file, read with `urna inspect --json`

The CITATION_KEY is read by the urna cli (`URNA_BIN`, else `urna` on PATH), not by
the python library that wrote the file, so the key is what an installed urna sees.

usage (repo root):
  python benchmark/tools/promote.py candidates/minilm-exact v0.1 [--force]
  python benchmark/tools/promote.py --check release/v0.1/minilm-exact
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402

FILES = ("fakenews.urna", "chunk_map.parquet", "build.lock.json", "manifest.json")
KEY_FIELDS = ("content_hash", "file_hash", "chunker_version", "title", "n_chunks", "embedding_model")


def urna_bin() -> str:
    b = os.environ.get("URNA_BIN") or shutil.which("urna")
    if not b:
        env.die("urna cli not found; put it on PATH or export URNA_BIN=/path/to/urna")
    return b


def inspect(path: Path) -> dict:
    r = subprocess.run([urna_bin(), "inspect", "--json", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        env.die(f"urna inspect failed on {env.rel(path)}: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def citation_key(path: Path) -> str:
    info = inspect(path)
    man = info.get("manifest", {})
    values = {
        "content_hash": info.get("content_hash"),
        "file_hash": info.get("file_hash"),
        "chunker_version": man.get("chunker_version"),
        "title": man.get("title"),
        "n_chunks": info.get("n_chunks", man.get("n_chunks")),
        "embedding_model": man.get("embedding_model"),
    }
    missing = [k for k in KEY_FIELDS if values[k] in (None, "")]
    if missing:
        env.die(f"urna inspect did not report {missing} for {env.rel(path)}")
    version = subprocess.run([urna_bin(), "--version"], capture_output=True, text=True).stdout.strip()
    lines = [f"{k} = {values[k]}" for k in KEY_FIELDS]
    lines += [f"read_with = {version or 'urna'} inspect --json"]
    return "\n".join(lines) + "\n"


def sums(release_dir: Path) -> str:
    return "".join(f"{env.sha256_file(release_dir / n)}  {n}\n" for n in FILES if (release_dir / n).is_file())


def check(release_dir: Path) -> int:
    want = (release_dir / "SHA256SUMS").read_text()
    got = sums(release_dir)
    lock = json.loads((release_dir / "build.lock.json").read_text())
    file_hash = "sha256:" + env.sha256_file(release_dir / "fakenews.urna")
    ok = want == got and file_hash == lock["output"]["file_hash"]
    ok = ok and f"file_hash = {file_hash}" in (release_dir / "CITATION_KEY").read_text()
    print(f"{env.rel(release_dir)}: {'ok' if ok else 'MISMATCH'}")
    return 0 if ok else 1


def promote(cand: Path, version: str, force: bool) -> int:
    for n in FILES:
        if not (cand / n).is_file():
            env.die(f"{env.rel(cand)}: missing {n}")
    env.require_corpus(json.loads((cand / "build.lock.json").read_text())["corpus"]["corpus_hash"], env.rel(cand))
    dest = env.RELEASE / version / cand.name
    if dest.exists() and any(dest.iterdir()) and not force:
        env.die(f"{env.rel(dest)} exists; pass --force to overwrite")
    dest.mkdir(parents=True, exist_ok=True)
    for n in FILES:
        env.place(cand / n, dest / n)
    (dest / "CITATION_KEY").write_text(citation_key(dest / "fakenews.urna"))
    (dest / "SHA256SUMS").write_text(sums(dest))
    print(f"promoted {env.rel(cand)} to {env.rel(dest)}")
    return check(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", nargs="?")
    ap.add_argument("version", nargs="?")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", nargs="+", metavar="RELEASE_DIR", help="verify release dirs against their sums")
    args = ap.parse_args()
    if args.check:
        return max(check(Path(d)) for d in args.check)
    if not (args.candidate and args.version):
        ap.error("candidate and version are required unless --check is given")
    return promote(Path(args.candidate), args.version, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
