"""The example embedders of profiles/models.toml behind one interface.

An embedder knows its manifest name (`embedding_model`), its dimension, its
`model_hash` and how to turn texts into L2-normalized float32 rows. Documents and
queries go through the same call: these models have no query/document modes.

sentence-transformers models are downloaded once, at the pinned revision, into
$FAKENEWS_DATA/models/<name>-<revision12>/, and loaded from that directory, so the
snapshot that embeds is the snapshot that is hashed. The encode matches Urna's
python/embed_query.py: normalize_embeddings=True, then a defensive re-normalize.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _model_fingerprint as mf  # noqa: E402


def models() -> dict[str, dict]:
    return {m["name"]: m for m in env.load_toml(env.MODELS_TOML)["model"]}


def model_entry(name: str) -> dict:
    found = models()
    if name not in found:
        env.die(f"unknown model {name!r}; profiles/models.toml has {', '.join(found)}")
    return found[name]


# weights in other runtimes and formats; sentence-transformers loads model.safetensors
SKIP = ["onnx/*", "openvino/*", "*.onnx", "*.h5", "*.msgpack", "*.ot", "pytorch_model.bin", "tf_model*", "flax_model*"]


def snapshot_dir(m: dict) -> Path:
    return env.data_root() / "models" / f"{m['name']}-{m['revision'][:12]}"


def fetch_snapshot(m: dict) -> Path:
    from huggingface_hub import snapshot_download

    dest = snapshot_dir(m)
    # idempotent: files already on disk at this revision are not fetched again
    snapshot_download(m["id"], revision=m["revision"], local_dir=dest, ignore_patterns=SKIP)
    return dest


def _renorm(rows: np.ndarray) -> np.ndarray:
    rows = rows.astype(np.float32, copy=False)
    n = np.linalg.norm(rows, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (rows / n).astype(np.float32)


class STEmbedder:
    def __init__(self, m: dict, device: str):
        # the pinned snapshot is fetched first; loading it never touches the hub
        self.path = fetch_snapshot(m)
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        self.entry = m
        self.device = device
        self.model = SentenceTransformer(str(self.path), device=device)
        self.embedding_model = m["id"]
        self.dim = int(self.model.get_sentence_embedding_dimension())
        fp = mf.compute_model_fingerprint(self.path, model_id=m["id"])
        self.fingerprint = fp.to_dict()
        self.model_hash = mf.fingerprint_to_model_hash(fp)

    def embed(self, texts: list[str], batch_size: int = 64, progress: bool = False) -> np.ndarray:
        rows = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=progress,
        )
        return _renorm(np.asarray(rows))


class PotionEmbedder:
    def __init__(self, m: dict, device: str):
        import urna
        from urna import embed_potion

        self.entry = m
        self.device = "cpu"
        self.inner = embed_potion.default_embedder()
        self.path = Path(urna.potion_model_path())
        self.embedding_model = self.inner.embedding_model
        self.dim = int(self.inner.embedding_dim)
        self.fingerprint = self.inner.fingerprint()
        self.model_hash = self.inner.model_hash()

    def embed(self, texts: list[str], batch_size: int = 512, progress: bool = False) -> np.ndarray:
        out = []
        for i in range(0, len(texts), batch_size):
            out.extend(self.inner.embed_texts(texts[i : i + batch_size]))
        return _renorm(np.asarray(out, dtype=np.float32))


def load(name: str, device: str = "cpu"):
    m = model_entry(name)
    if m["kind"] == "sentence-transformers":
        return STEmbedder(m, device)
    if m["kind"] == "potion":
        return PotionEmbedder(m, device)
    env.die(f"{name}: unknown kind {m['kind']!r}")
