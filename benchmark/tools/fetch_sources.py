#!/usr/bin/env python3
"""Download every upstream dataset at its pinned revision into $FAKENEWS_DATA/<name>/.

Reads sources/sources.toml. A source with an empty `revision` is refused. After
the download, the tree hash of the fetched files is compared with `tree_hash`;
a mismatch stops the run. `--record` writes the tree hash of a source whose
`tree_hash` is still empty, which is how a new pin gets its hash.

GitHub sources come from the commit tarball (codeload.github.com), hub sources
through huggingface_hub at the pinned revision. Nothing is cloned.

usage (repo root):
  python benchmark/tools/fetch_sources.py [--only NAME ...] [--record]
"""

from __future__ import annotations

import argparse
import io
import re
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402


def wanted(path: str, files: list[str]) -> bool:
    return any(path == f or (f.endswith("/") and path.startswith(f)) for f in files)


def fetch_github(src: dict, dest: Path) -> None:
    url = f"https://codeload.github.com/{src['repo']}/tar.gz/{src['revision']}"
    with urllib.request.urlopen(url, timeout=120) as r:
        blob = r.read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            relpath = m.name.split("/", 1)[1] if "/" in m.name else ""
            if not relpath or not wanted(relpath, src["files"]):
                continue
            out = dest / relpath
            out.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as f, out.open("wb") as o:
                shutil.copyfileobj(f, o)


def fetch_hub(src: dict, dest: Path) -> None:
    from huggingface_hub import snapshot_download

    repo_type = "dataset" if src["kind"] == "hf-dataset" else "model"
    patterns = [f + "*" if f.endswith("/") else f for f in src["files"]]
    snapshot_download(
        src["repo"], repo_type=repo_type, revision=src["revision"], allow_patterns=patterns, local_dir=dest
    )
    shutil.rmtree(dest / ".cache", ignore_errors=True)


def fetched_files(dest: Path, files: list[str]) -> list[Path]:
    return [p for p in sorted(dest.rglob("*")) if p.is_file() and wanted(p.relative_to(dest).as_posix(), files)]


def record_tree_hash(name: str, value: str) -> None:
    text = env.SOURCES_TOML.read_text()
    block = re.compile(r'(name = "' + re.escape(name) + r'"\n(?:(?!\[\[source\]\]).*\n)*?tree_hash = )""')
    new, n = block.subn(lambda m: f'{m.group(1)}"{value}"', text, count=1)
    if n != 1:
        env.die(f"could not record tree_hash for {name} in {env.rel(env.SOURCES_TOML)}")
    env.SOURCES_TOML.write_text(new)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=None, help="source names to fetch (default: all)")
    ap.add_argument("--record", action="store_true", help="write the tree hash of sources whose tree_hash is empty")
    args = ap.parse_args()
    root = env.data_root()
    failed = 0
    for src in env.sources():
        if args.only and src["name"] not in args.only:
            continue
        if not src.get("revision"):
            env.die(f"{src['name']}: no pinned revision in {env.rel(env.SOURCES_TOML)}")
        dest = root / src["name"]
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        print(f"{src['name']}: {src['repo']} @ {src['revision'][:12]}")
        if src["kind"] == "github":
            fetch_github(src, dest)
        elif src["kind"] in ("hf-dataset", "hf-model"):
            fetch_hub(src, dest)
        else:
            env.die(f"{src['name']}: unknown kind {src['kind']!r}")
        files = fetched_files(dest, src["files"])
        if not files:
            env.die(f"{src['name']}: nothing matched {src['files']}")
        th = env.tree_hash(dest, files)
        print(f"  {len(files)} files, tree_hash {th}")
        if not src.get("tree_hash"):
            if args.record:
                record_tree_hash(src["name"], th)
                print("  recorded")
            else:
                print("  no tree_hash pinned; rerun with --record to pin it")
                failed += 1
        elif src["tree_hash"] != th:
            print(f"  MISMATCH: sources.toml pins {src['tree_hash']}")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
