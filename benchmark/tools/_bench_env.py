"""Shared plumbing for the bench tools: repo paths, the data root and the sources list.

Every tool imports this instead of guessing where it sits. The data root is
FAKENEWS_DATA, with no default: the upstream datasets never land inside the repo.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCES_TOML = REPO / "sources" / "sources.toml"
MODELS_TOML = REPO / "profiles" / "models.toml"
PRESETS_TOML = REPO / "profiles" / "presets.toml"
QUERIES = REPO / "benchmark" / "queries"
EXPERIMENTS = REPO / "benchmark" / "experiments"
RUNS = REPO / "benchmark" / "runs"
CANDIDATES = REPO / "candidates"
RELEASE = REPO / "release"


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def data_root() -> Path:
    raw = os.environ.get("FAKENEWS_DATA", "").strip()
    if not raw:
        die("FAKENEWS_DATA is not set; export FAKENEWS_DATA=/path/to/fakenews-data")
    return Path(os.path.expanduser(raw)).resolve()


def prepared_dir() -> Path:
    return data_root() / "prepared"


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def sources() -> list[dict]:
    return load_toml(SOURCES_TOML)["source"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hash(root: Path, files: list[Path]) -> str:
    """sha256 over the sorted `relpath sha256` lines of `files`, the identity of a fetched source."""
    lines = sorted(f"{f.relative_to(root).as_posix()} {sha256_file(f)}" for f in files)
    return "sha256:" + hashlib.sha256("\n".join(lines).encode()).hexdigest()


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
