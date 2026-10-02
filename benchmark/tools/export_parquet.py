#!/usr/bin/env python3
"""Lay out the Hugging Face dataset tree from the prepared corpus and a release.

  python benchmark/tools/export_parquet.py v0.1 OUT_DIR

Writes, under OUT_DIR:
  data/corpus/train-00000-of-00001.parquet, test-00000-of-00001.parquet
  data/chunk_map/<version>-00000-of-00001.parquet
  data/queries/queries-00000-of-00001.parquet, qrels-00000-of-00001.parquet
  release/<version>/<model>-<preset>/   the release dirs, .urna and chunk map included
  results/                              every results.json under benchmark/experiments
  CHECKSUMS.json                        sha256 of every file above, and the corpus_hash

The chunk map is the same for every build of a release (chunk_id depends on the
text, the source_uri, the span and the chunker version, not on the model); the
export refuses a release whose builds disagree, a build or result from another
corpus version, a results.json without a corpus_hash, and a maintainer-verified
license without license_evidence (--private exports anyway, for a private dataset,
and lists the gap). Every check runs before the first write; data/, release/,
results/ and CHECKSUMS.json are replaced whole.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
from evaluate import load_queries  # noqa: E402


def shard(name: str) -> str:
    return f"{name}-00000-of-00001.parquet"


def validate(version: str, private: bool) -> tuple[list[Path], pd.DataFrame, list[Path], list[str]]:
    """Every check, before anything is written: the builds, the chunk map, the results, the licenses."""
    missing_evidence = env.unproven_licenses()
    if missing_evidence and not private:
        env.require_license_evidence()
    rel_root = env.RELEASE / version
    builds = sorted(d for d in rel_root.iterdir() if d.is_dir()) if rel_root.is_dir() else []
    if not builds:
        env.die(f"no builds under {env.rel(rel_root)}")
    for b in builds:
        env.require_corpus(json.loads((b / "build.lock.json").read_text())["corpus"]["corpus_hash"], env.rel(b))
        for name in ("fakenews.urna", "chunk_map.parquet"):
            if not (b / name).is_file():
                env.die(f"{env.rel(b)}: missing {name}")
    maps = [pd.read_parquet(b / "chunk_map.parquet") for b in builds]
    if any(not m.equals(maps[0]) for m in maps[1:]):
        env.die(f"the builds of {version} do not share one chunk map")
    results = sorted(env.EXPERIMENTS.glob("*/results.json"))
    for rj in results:
        found = json.loads(rj.read_text()).get("corpus_hash")
        if not found:
            env.die(f"{env.rel(rj)} records no corpus_hash; regenerate it with its tool")
        env.require_corpus(found, env.rel(rj))
    return builds, maps[0], results, missing_evidence


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version")
    ap.add_argument("out")
    ap.add_argument(
        "--private",
        action="store_true",
        help="export for a private dataset even when a license_evidence is missing; CHECKSUMS.json lists them",
    )
    args = ap.parse_args()
    out = Path(args.out)
    prep = json.loads((env.prepared_dir() / "prepare.json").read_text())
    corpus = pd.read_parquet(env.prepared_dir() / "corpus.parquet")
    builds, chunk_map, results, missing_evidence = validate(args.version, args.private)
    queries, qrels = load_queries()

    # nothing below runs unless every check passed; the managed paths are replaced whole,
    # so a file of an earlier export never lingers next to this one
    for managed in ("data", "release", "results", "CHECKSUMS.json"):
        target = out / managed
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    (out / "data" / "corpus").mkdir(parents=True)
    for split in ("train", "test"):
        part = corpus[corpus["split"] == split].drop(columns=["split"])
        part.to_parquet(out / "data" / "corpus" / shard(split), index=False)
    (out / "data" / "chunk_map").mkdir(parents=True)
    chunk_map.to_parquet(out / "data" / "chunk_map" / shard(args.version), index=False)
    (out / "data" / "queries").mkdir(parents=True)
    pd.DataFrame(queries)[["query_id", "text", "origin"]].to_parquet(out / "data" / "queries" / shard("queries"), index=False)
    rows = [
        {"query_id": q, "iteration": 0, "doc_id": d, "relevance": r}
        for q, judged in qrels.items()
        for d, r in sorted(judged.items())
    ]
    pd.DataFrame(rows).to_parquet(out / "data" / "queries" / shard("qrels"), index=False)
    for b in builds:
        dest = out / "release" / args.version / b.name
        dest.mkdir(parents=True)
        for f in sorted(b.iterdir()):
            if f.is_file():
                env.place(f, dest / f.name)
    (out / "results").mkdir()
    for rj in results:
        shutil.copy2(rj, out / "results" / f"{rj.parent.name}.json")

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in ("CHECKSUMS.json", "README.md", "CITATION.cff") and not p.name.startswith("."))
    checks = {
        "corpus_hash": prep["corpus_hash"],
        "release": args.version,
        "license_evidence_missing": missing_evidence,
        "files": {p.relative_to(out).as_posix(): "sha256:" + env.sha256_file(p) for p in files},
    }
    env.write_json(out / "CHECKSUMS.json", checks)
    print(f"{len(files)} files under {out}, corpus_hash {prep['corpus_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
