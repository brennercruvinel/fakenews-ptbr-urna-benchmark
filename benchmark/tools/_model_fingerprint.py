"""Model fingerprint and model_hash, vendored from Urna so a corpus built here
carries the model_hash Urna computes when it embeds a query.

Copied from hoffresearch/urna python/model_fingerprint.py at 3b1afe5960e8 (MIT).
Only the hashing is kept; the offline switch and the hub-cache resolution are
not, because build.py always passes an explicit snapshot directory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

RELEVANT_FILES: tuple[str, ...] = (
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "sentence_bert_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "1_Pooling/config.json",
    "model.safetensors",
    "pytorch_model.bin",
)

PLACEHOLDER_HASH = "sha256:" + "0" * 64


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json_safe(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


@dataclass(frozen=True)
class ModelFingerprint:
    """Structured fingerprint of a sentence-transformers / HF model snapshot.

    Stable across machines: only depends on the bytes of the relevant
    files plus a few config-derived facts. Serializable via `to_dict`.
    """

    model_id: str
    files_hash: str  # sha256 over the relevant files (sorted)
    tokenizer_hash: str | None
    pooling_config_hash: str | None
    embedding_dim: int
    normalize_embeddings: bool

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "files_hash": self.files_hash,
            "tokenizer_hash": self.tokenizer_hash,
            "pooling_config_hash": self.pooling_config_hash,
            "embedding_dim": self.embedding_dim,
            "normalize_embeddings": self.normalize_embeddings,
        }


def compute_model_fingerprint(
    model_dir: str | Path,
    *,
    model_id: str | None = None,
) -> ModelFingerprint:
    """Compute a reproducible fingerprint of a model snapshot directory.

    `model_dir` should be the local path of an unpacked HF / sentence-
    transformers model - the same directory `SentenceTransformer` would
    load. Missing files are tolerated (some models don't ship every
    relevant file); `RELEVANT_FILES` order is the canonical order.

    If `model_id` is provided (e.g. the HF identifier the caller used),
    it goes into the fingerprint verbatim. Otherwise we read it from
    `config.json`'s `_name_or_path` (which can be local-path-flavored
    and unstable across machines).
    """
    md = Path(model_dir).resolve()
    if not md.is_dir():
        raise FileNotFoundError(f"model directory not found: {md}")

    files_h = hashlib.sha256()
    for rel in RELEVANT_FILES:
        p = md / rel
        sha = _sha256_file(p)
        if sha is None:
            continue
        files_h.update(rel.encode("utf-8"))
        files_h.update(b"\0")
        files_h.update(sha.encode("utf-8"))
        files_h.update(b"\0")
    files_hash = "sha256:" + files_h.hexdigest()

    cfg = _read_json_safe(md / "config.json")
    st_cfg = _read_json_safe(md / "config_sentence_transformers.json")
    pooling_cfg = _read_json_safe(md / "1_Pooling/config.json")

    resolved_id = model_id or cfg.get("_name_or_path") or md.name
    embedding_dim = int(
        st_cfg.get("hidden_size")
        or cfg.get("hidden_size")
        or cfg.get("dim")
        or pooling_cfg.get("word_embedding_dimension")
        or 0
    )
    normalize = bool(
        st_cfg.get("normalize_embeddings", pooling_cfg.get("pooling_mode_mean_tokens", True))
    )

    tokenizer_sha = _sha256_file(md / "tokenizer.json")
    tokenizer_hash = f"sha256:{tokenizer_sha}" if tokenizer_sha else None

    pooling_sha = _sha256_file(md / "1_Pooling/config.json")
    pooling_hash = f"sha256:{pooling_sha}" if pooling_sha else None

    return ModelFingerprint(
        model_id=str(resolved_id),
        files_hash=files_hash,
        tokenizer_hash=tokenizer_hash,
        pooling_config_hash=pooling_hash,
        embedding_dim=embedding_dim,
        normalize_embeddings=normalize,
    )


def fingerprint_to_model_hash(fp: ModelFingerprint) -> str:
    """Compact `sha256:<hex>` hash of the canonical JSON of `fp`.

    Stored in the manifest as `model_hash`. Reproducible across
    machines because the JCS-style serialization (sort_keys, no
    whitespace) is stable.
    """
    canonical = json.dumps(fp.to_dict(), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
