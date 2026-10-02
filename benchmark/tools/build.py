#!/usr/bin/env python3
"""Build one .urna from the prepared corpus with one example model and one preset.

  python benchmark/tools/build.py --model minilm --preset exact

The model comes from profiles/models.toml, the preset from profiles/presets.toml.
Writes candidates/<model>-<preset>/:
  fakenews.urna       one chunk per document, the whole normalized text
  chunk_map.parquet   chunk_id, doc_id, source_uri, byte_start, byte_end, chunker_version
  build.lock.json     corpus and source identity, model snapshot and model_hash,
                      preset, package versions, platform, device, output hashes
  manifest.json       what urna reads back from the file, plus timings

Every chunk's source_uri is fakenews-ptbr://doc/<doc_id hex>, its span the whole
text, its chunker version CHUNKER_VERSION, so chunk_id is fixed by the text alone
and the map is the same for every model and preset. After the build the chunk ids
read from the file must equal the map, in order, or the build fails.

Document vectors are cached per model, revision, device and corpus_hash under
$FAKENEWS_DATA/embed/, so the three presets of a model embed once.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _embed  # noqa: E402

CHUNKER_VERSION = "fakenews-ptbr/0.1"
URI_PREFIX = "fakenews-ptbr://doc/"
URNA_NAME = "fakenews.urna"
PACKAGES = (
    "urna",
    "numpy",
    "pandas",
    "pyarrow",
    "sentence-transformers",
    "transformers",
    "torch",
    "tokenizers",
    "huggingface_hub",
)


def preset_entry(name: str) -> dict:
    found = {p["name"]: p for p in env.load_toml(env.PRESETS_TOML)["preset"]}
    if name not in found:
        env.die(f"unknown preset {name!r}; profiles/presets.toml has {', '.join(found)}")
    return found[name]


def versions() -> dict[str, str]:
    out = {}
    for p in PACKAGES:
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = "absent"
    return out


def chunk_map(corpus: pd.DataFrame) -> pd.DataFrame:
    import urna

    rows = []
    for did, text in zip(corpus["doc_id"], corpus["text"]):
        uri = URI_PREFIX + did.split(":", 1)[1]
        end = len(text.encode("utf-8"))
        rows.append(
            {
                "chunk_id": urna.chunk_id(text, uri, 0, end, CHUNKER_VERSION),
                "doc_id": did,
                "source_uri": uri,
                "byte_start": 0,
                "byte_end": end,
                "chunker_version": CHUNKER_VERSION,
            }
        )
    return pd.DataFrame(rows)


def doc_vectors(emb, corpus: pd.DataFrame, corpus_hash: str) -> tuple[np.ndarray, float]:
    m = emb.entry
    cache = env.data_root() / "embed" / f"{m['name']}-{m['revision'][:12]}-{emb.device}-{corpus_hash[7:19]}.npy"
    if cache.is_file():
        return np.load(cache), 0.0
    t0 = time.perf_counter()
    rows = emb.embed(list(corpus["text"]), progress=True)
    secs = time.perf_counter() - t0
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, rows)
    return rows, secs


def snapshot_files(path: Path) -> dict[str, str]:
    out = {}
    for p in sorted(path.rglob("*")):
        rel = p.relative_to(path).as_posix()
        if p.is_file() and not rel.startswith(".cache/"):
            out[rel] = env.sha256_file(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="a name from profiles/models.toml")
    ap.add_argument("--preset", required=True, help="a name from profiles/presets.toml")
    ap.add_argument("--device", default="cpu", help="torch device for sentence-transformers (default cpu)")
    ap.add_argument("--out", default=None, help="output dir (default candidates/<model>-<preset>)")
    args = ap.parse_args()

    preset = preset_entry(args.preset)
    prepared = env.prepared_dir()
    prep = json.loads((prepared / "prepare.json").read_text())
    corpus = pd.read_parquet(prepared / "corpus.parquet", columns=["doc_id", "text"])
    out = Path(args.out) if args.out else env.CANDIDATES / f"{args.model}-{args.preset}"
    emb = _embed.load(args.model, args.device)
    print(f"{args.model} ({emb.embedding_model}, {emb.dim}d) x {args.preset}: {len(corpus)} docs")

    vecs, embed_s = doc_vectors(emb, corpus, prep["corpus_hash"])
    cmap = chunk_map(corpus)
    chunks = [
        {
            "canonical_text": t,
            "source_uri": r.source_uri,
            "byte_start": 0,
            "byte_end": int(r.byte_end),
            "embedding": v.tolist(),
        }
        for t, r, v in zip(corpus["text"], cmap.itertuples(), vecs)
    ]

    import urna

    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    t0 = time.perf_counter()
    urna.build(
        str(tmp / URNA_NAME),
        emb.embedding_model,
        emb.dim,
        CHUNKER_VERSION,
        emb.model_hash,
        chunks,
        title=f"fakenews-ptbr {args.model} {args.preset}",
        version="0.1.0",
        description="Seven pt-br fake-news datasets, deduplicated by text; one chunk per document.",
        license="mixed (per-source, see docs/sources.md)",
        provenance={"corpus_hash": prep["corpus_hash"], "model": args.model, "preset": args.preset},
        reproducible=True,
        **preset["kwargs"],
    )
    build_s = time.perf_counter() - t0

    f = urna.open(str(tmp / URNA_NAME))
    ids = list(f.chunk_ids())
    if ids != list(cmap["chunk_id"]):
        env.die("chunk ids read from the file do not match the chunk map")
    info = f.inspect()
    file_hash = "sha256:" + env.sha256_file(tmp / URNA_NAME)
    cmap.to_parquet(tmp / "chunk_map.parquet", index=False)

    lock = {
        "corpus": {
            "corpus_hash": prep["corpus_hash"],
            "n_docs": prep["n_docs"],
            "source_tree_hashes": prep["source_tree_hashes"],
        },
        "model": {
            **{k: emb.entry[k] for k in ("name", "kind", "id", "revision", "dim")},
            "model_hash": emb.model_hash,
            "fingerprint": emb.fingerprint,
            "snapshot_files": snapshot_files(emb.path),
        },
        "build": {
            "preset": args.preset,
            "kwargs": preset["kwargs"],
            "chunker_version": CHUNKER_VERSION,
            "source_uri": URI_PREFIX + "<doc_id hex>",
            "reproducible": True,
        },
        "environment": {
            "packages": versions(),
            "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.machine()}",
            "device": emb.device,
        },
        "output": {
            "file_hash": file_hash,
            "content_hash": info.get("content_hash"),
            "bytes": (tmp / URNA_NAME).stat().st_size,
            "n_chunks": len(ids),
        },
    }
    env.write_json(tmp / "build.lock.json", lock)
    env.write_json(tmp / "manifest.json", {"inspect": info, "timings_s": {"embed": round(embed_s, 1), "build": round(build_s, 1)}})
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    print(f"  {env.rel(out / URNA_NAME)}: {lock['output']['bytes']} bytes, {file_hash}")
    print(f"  embed {embed_s:.0f} s (0 = cached), build {build_s:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
