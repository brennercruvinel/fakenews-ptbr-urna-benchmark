# The corpus inside Urna

What the Urna repository holds that depends on the fake-news corpus, as of Urna 0.5.1 (`hoffresearch/urna`, `main` at `3b1afe59`). This is the map the migration works from: what this benchmark replaces, and what stays in Urna.

## The artifact

| Path | Role |
|---|---|
| `data/corpus_next.v1.urna` | The corpus, in git lfs. 30,725 chunks, `exact` preset, MiniLM 384d. `file_hash sha256:4229b7b3abfb85ddd75ebf183e0518acf60b8c4c7816c2f1df4c9041ef9b3233`, `content_hash sha256:0ef1cf8f5d682f4614a0c4ea38f093a432c352de3a350362d09fcef2ff05917e`. |
| `data/measure/fakerecogna_exact.urna` | A FakeRecogna-only corpus kept in lfs for measurements. |
| `.gitattributes`, `.gitignore`, `scripts/pre-commit` | Track both files in lfs and allow them past the data-artifact guard. |

## The build

| Path | Role |
|---|---|
| `python/tools/_corpus_sources.py` | Seven loaders that read the datasets from `data/demo/<name>/` and normalize them to `text, label, source, title, url`. |
| `python/tools/urna_build_corpus.py` | Concatenates the loaders, drops texts of 20 characters or less, deduplicates by the SHA-256 of the text, embeds with MiniLM through `builder.Pipeline` and writes the file. `source_uri` is `corpus-next://<source>/<sha256>`, chunker `corpus-next/v0.1.0`. |
| `data/demo/Instructions.md` | The upstream links, the fetch commands and the license bill of materials. The datasets themselves are gitignored and have no pinned revision. |

This benchmark replaces both scripts: `benchmark/tools/fetch_sources.py` and `prepare.py` take the loaders' place with pinned revisions and the new schema, and `build.py` builds with the published wheel instead of a checkout.

## The gate

| Path | Role |
|---|---|
| `python/tools/measure_presets.py` | Rebuilds the corpus at the other presets and compares them with the `exact` file: size, recall@10, score drift, latency. Queries are corpus vectors plus noise (the self-perturbation ruler): it measures stability, not relevance. |
| `python/tools/_baseline_decoder.py` | `DEFAULT_BASELINE` points at `data/corpus_next.v1.urna`. |
| `data/measure/baseline.json`, `ladder.json`, `archive/*.json` | The recorded numbers, keyed by the baseline's `file_hash` and `content_hash`. |
| `scripts/release_check.sh` | Runs `measure_presets.py` and `compare_measure.py` against `baseline.json`. |

The gate needs the file, not the build: it reads `corpus_next.v1.urna` and never rebuilds it from the datasets. Moving the build out of Urna does not change what the gate measures.

## Mentions

`docs/USAGE.md` (docker example), `docker/Dockerfile`, `docs/CONTRIBUTING.md`, `python/urna_cli.py` (docstring), `.contracts/.agents/AGENTS.md`, `.contracts/.agents/.skills/AFTERWORK.md`, `docs/arc/ARC.toml` (file inventory and the build flow), `README.md` and `tests/test_query_embedder_routing.py` (the MiniLM model id).

## The query side

A MiniLM corpus is queried through `python/embed_query.py`. Urna 0.5.1 refuses it from an installed binary; the route and a `minilm-multilingual` registry preset are in pull request #264, unreleased.
