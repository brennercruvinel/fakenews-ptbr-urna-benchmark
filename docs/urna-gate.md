# The corpus inside Urna

What the Urna repository holds that depends on the fake-news corpus, as of Urna 0.5.4 (`hoffresearch/urna`, tag `v0.5.4` at `12498808`; first written against 0.5.1, `main` at `3b1afe59`). Urna 0.5.4 renamed its folders, so the paths below are the 0.5.4 ones. This is the map the migration works from: what this benchmark replaces, and what stays in Urna.

## The artifact

| Path | Role |
|---|---|
| `data/corpus_next.v1.urna` | The corpus, in git lfs. 30,725 chunks, `exact` preset, MiniLM 384d. `file_hash sha256:4229b7b3abfb85ddd75ebf183e0518acf60b8c4c7816c2f1df4c9041ef9b3233`, `content_hash sha256:0ef1cf8f5d682f4614a0c4ea38f093a432c352de3a350362d09fcef2ff05917e`. |
| `data/measure/fakerecogna_exact.urna` | A FakeRecogna-only corpus kept in lfs for measurements. Nothing read it; Urna 0.5.2 removed it from the tree (it stays in history). |
| `.gitattributes`, `.gitignore`, `script/precommit` | Track both files in lfs and allow them past the data-artifact guard. |

## The build

| Path | Role |
|---|---|
| `python/tools/_corpus_sources.py` | Seven loaders that read the datasets from `data/demo/<name>/` and normalize them to `text, label, source, title, url`. |
| `python/tools/urna_build_corpus.py` | Concatenates the loaders, drops texts of 20 characters or less, deduplicates by the SHA-256 of the text, embeds with MiniLM through `builder.Pipeline` and writes the file. `source_uri` is `corpus-next://<source>/<sha256>`, chunker `corpus-next/v0.1.0`. Urna 0.5.2 removed it with `_corpus_sources.py`; both stay in history. |
| `data/demo/Instructions.md` | The upstream links, the fetch commands and the license bill of materials. The datasets themselves are gitignored and have no pinned revision. |

This benchmark replaces both scripts: `benchmark/tools/fetch_sources.py` and `prepare.py` take the loaders' place with pinned revisions and the new schema, and `build.py` builds with the published wheel instead of a checkout.

## Why the file cannot be rebuilt

The loader read files that are gone upstream:

- `vzani/corpus-fake-br` and `vzani/corpus-faketrue-br` now carry `corpus_train_df.parquet` and `corpus_test_df.parquet`; the `train.csv` and `test.csv` the loader opened are not there.
- FakeRecogna ships `dataset/FakeRecogna.xlsx`; the `FakeRecogna.csv` the loader opened is not there.
- `opit-research/factck-br` no longer exists. The original is `jghm-f/FACTCK.BR`, with the same `FACTCKBR.tsv`.

So `corpus_next.v1.urna` stays what it is: a frozen file, identified by its `file_hash`. Two things in it are known, and neither changes what the gate measures (rank stability under quantization):

- The 7,200 Fake.br articles are in it twice. The loader read both the vzani copy and Fake.br's `preprocessed/pre-processed.csv`, whose text has stopwords, accents and diacritics removed, so the two never deduplicated. That accounts for most of the gap between its 30,725 chunks and the 23,335 documents here.
- The FACTCK.BR labels came from the numeric rating (`<= 2` fake, `3` dropped, `>= 4` true). The scale differs per agency, and 469 claims rated "Falso" carry a 4, so they are labeled true. Experiment 01 has the table.

## The gate

| Path | Role |
|---|---|
| `python/tools/measure_presets.py` | Rebuilds the corpus at the other presets and compares them with the `exact` file: size, recall@10, score drift, latency. Queries are corpus vectors plus noise (the self-perturbation ruler): it measures stability, not relevance. |
| `python/tools/_baseline_decoder.py` | `DEFAULT_BASELINE` points at `data/corpus_next.v1.urna`. |
| `data/measure/baseline.json`, `ladder.json`, `archive/*.json` | The recorded numbers, keyed by the baseline's `file_hash` and `content_hash`. |
| `script/fullcheck.sh` | Runs `measure_presets.py` and `compare_measure.py` against `baseline.json` (`scripts/release_check.sh` before 0.5.4). |

The gate needs the file, not the build: it reads `corpus_next.v1.urna` and never rebuilds it from the datasets. Moving the build out of Urna does not change what the gate measures.

## Mentions

`docs/USAGE.md` (docker example), `Dockerfile`, `docs/CONTRIBUTING.md`, `docs/SECURITY.md` (the corpus license), `python/urna_cli.py` (docstring), `docs/ARC.toml` (file inventory and the build flow), `data/demo/Instructions.md`, and the MiniLM model id in `README.md`, `tests/test_askrouter.py` and `tests/test_catalogue.py`.

## The query side

A MiniLM corpus is queried through `python/embed_query.py`. Urna 0.5.1 refuses it from an installed binary. Pull request #264, merged on 2026-10-02 and released in Urna 0.5.3 (0.5.2 reached PyPI only), fixes that: the payload ships `embed_query.py`, `urna setup` replaces an older payload and keeps the venv, the registry gains `minilm-multilingual` with the same fingerprint, and a failed query names its cause and the fix.
