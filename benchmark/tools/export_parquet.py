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
export refuses a release whose builds disagree.
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version")
    ap.add_argument("out")
    args = ap.parse_args()
    out = Path(args.out)
    prep = json.loads((env.prepared_dir() / "prepare.json").read_text())
    corpus = pd.read_parquet(env.prepared_dir() / "corpus.parquet")

    (out / "data" / "corpus").mkdir(parents=True, exist_ok=True)
    for split in ("train", "test"):
        part = corpus[corpus["split"] == split].drop(columns=["split"])
        part.to_parquet(out / "data" / "corpus" / shard(split), index=False)

    rel_root = env.RELEASE / args.version
    builds = sorted(d for d in rel_root.iterdir() if d.is_dir())
    if not builds:
        env.die(f"no builds under {env.rel(rel_root)}")
    maps = [pd.read_parquet(b / "chunk_map.parquet") for b in builds]
    if any(not m.equals(maps[0]) for m in maps[1:]):
        env.die(f"the builds of {args.version} do not share one chunk map")
    (out / "data" / "chunk_map").mkdir(parents=True, exist_ok=True)
    maps[0].to_parquet(out / "data" / "chunk_map" / shard(args.version), index=False)

    queries, qrels = load_queries()
    (out / "data" / "queries").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(queries)[["query_id", "text", "origin"]].to_parquet(out / "data" / "queries" / shard("queries"), index=False)
    rows = [
        {"query_id": q, "iteration": 0, "doc_id": d, "relevance": r}
        for q, judged in qrels.items()
        for d, r in sorted(judged.items())
    ]
    pd.DataFrame(rows).to_parquet(out / "data" / "queries" / shard("qrels"), index=False)

    for b in builds:
        dest = out / "release" / args.version / b.name
        dest.mkdir(parents=True, exist_ok=True)
        for f in sorted(b.iterdir()):
            if f.is_file():
                env.place(f, dest / f.name)
    (out / "results").mkdir(exist_ok=True)
    for rj in sorted(env.EXPERIMENTS.glob("*/results.json")):
        shutil.copy2(rj, out / "results" / f"{rj.parent.name}.json")

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in ("CHECKSUMS.json", "README.md", "CITATION.cff") and not p.name.startswith("."))
    checks = {
        "corpus_hash": prep["corpus_hash"],
        "release": args.version,
        "files": {p.relative_to(out).as_posix(): "sha256:" + env.sha256_file(p) for p in files},
    }
    env.write_json(out / "CHECKSUMS.json", checks)
    print(f"{len(files)} files under {out}, corpus_hash {prep['corpus_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
