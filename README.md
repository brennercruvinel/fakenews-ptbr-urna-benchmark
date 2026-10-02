![urna: offline-first vector database, rust and python](https://raw.githubusercontent.com/hoffresearch/urna/main/assets/images/urna-hoff-research-db-thumb.png)

# fakenews-ptbr-urna-benchmark

Seven public Brazilian Portuguese fake-news datasets, deduplicated into one corpus of 23,335 documents and packed into single `.urna` files, with 2,601 queries and the relevance judgments that say how well search over them works.

This is the rebuildable successor of the text corpus in [Urna](https://github.com/hoffresearch/urna). Urna's regression gate measures `data/corpus_next.v1.urna`, a file that can no longer be rebuilt: its loader read csv files and a mirror that are gone upstream. Here every source is pinned to a revision and a tree hash, the build runs on the published `urna` wheel without a checkout, and the embedder is yours to pick.

> Status: v0.1, private. Every source is licensed MIT or Apache-2.0; the evidence for three maintainer-verified licenses is still to be recorded ([docs/sources.md](docs/sources.md)).

## Pick a model

Three example embedders, all on the same corpus and the same queries. None is a default: `profiles/models.toml` lists them, and adding one is a new entry there.

| Model | Dim | nDCG@10 | recall@10 | Embed the corpus (CPU) | Query from an installed Urna |
|---|---:|---:|---:|---:|---|
| `mpnet` (paraphrase-multilingual-mpnet-base-v2) | 768 | 0.528 | 0.690 | about 7 min | the release after 0.5.1, `--model-path` |
| `minilm` (paraphrase-multilingual-MiniLM-L12-v2) | 384 | 0.503 | 0.660 | about 3 min | the release after 0.5.1, `--model-path` |
| `potion` (potion-base-8M, bundled with the wheel) | 256 | 0.326 | 0.399 | seconds | Urna 0.5.1, out of the box |

Numbers are for the `exact` preset on an Apple M4 CPU; the `tiny` and `hybrid` presets of each model are in [RESULTS.md](RESULTS.md). The two multilingual models read the first 128 tokens of each document. Potion is an English static table: Portuguese rides English subwords, and it shows.

## Build one

```sh
uv sync
export FAKENEWS_DATA=/path/to/fakenews-data      # sources, models and caches land here, never in the repo
```

```sh
uv run python benchmark/tools/fetch_sources.py   # seven sources at their pinned revisions, tree hashes checked
uv run python benchmark/tools/prepare.py         # normalize, dedup, conflicts, splits
uv run python benchmark/tools/build.py --model minilm --preset exact
uv run python benchmark/tools/evaluate.py candidates/minilm-exact
```

`build.py` downloads the model at its pinned revision into `$FAKENEWS_DATA/models/` and writes `candidates/<model>-<preset>/`: the `.urna`, the chunk map, a build lock (corpus and source hashes, the model snapshot's file hashes and `model_hash`, package versions, platform, device, output hashes) and the manifest Urna reads back. A rebuild on the same machine gives the same `file_hash`. `evaluate.py` writes a TREC run under `benchmark/runs/` and its scores. `sh benchmark/tools/check_clean.sh WORK_DIR` runs all of this from a fresh clone and checks every pinned identity ([experiment 04](benchmark/experiments/04-clean-install/)).

## Query one

```sh
urna retrieve candidates/potion-exact/fakenews.urna "vacina altera o dna" -k 5 --format jsonl
```

```sh
urna retrieve candidates/minilm-exact/fakenews.urna "vacina altera o dna" -k 5 --format jsonl \
  --model-path "$FAKENEWS_DATA/models/minilm-e8f8c211226b"
```

The potion file answers any Urna 0.5.1 install. The sentence-transformers files need the query route merged into Urna's `main` in [#264](https://github.com/hoffresearch/urna/pull/264), which ships with the release after 0.5.1: run `urna setup --yes` with that binary (it replaces a 0.5.1 payload and keeps the venv), add `torch` and `sentence-transformers` to Urna's venv, and pass `--model-path` pointing at the pinned snapshot `build.py` downloaded. When something is missing, the query says what and prints the fix: the install line for the interpreter it ran, or the missing weights. The [dataset card](https://huggingface.co/datasets/brennercruvinel/fakenews-ptbr-urna-benchmark) has the full steps. From Python, `urna.open(path).search(vector, k)` takes a vector embedded by the same model.

## Documents, chunks and conflicts

The overlap between sources is large: 10,381 documents appear in more than one source (FakeBr-hf and Fake.br-Corpus share 7,199, FakeTrue.Br and its vzani copy 3,182). The corpus is deduplicated by the SHA-256 of the normalized text, and that hash is the `doc_id`, the unit `qrels` judges.

A `doc_id` is not a citation. Inside a `.urna` file the identity of a chunk is its `chunk_id`, which Urna derives from the canonical text, the `source_uri`, the byte span and the chunker version ([`chunk.rs`](https://github.com/hoffresearch/urna/blob/main/crates/urna-format/src/chunk.rs)). Each build writes a chunk map (`chunk_id`, `doc_id`, `source_uri`, `byte_start`, `byte_end`, `chunker_version`), and both `build.py` and `evaluate.py` refuse a file whose chunk ids differ from it. Here one chunk is one whole document, so the map is the same for every model and preset.

The evaluation turns chunk hits into a document ranking before scoring. Each hit maps to its `doc_id`, the first hit of a document takes the next document rank and later hits of the same document are dropped, so `A, A, B` becomes `A, B` at ranks 1 and 2. Metrics at k use the first k distinct documents, and a query that returns fewer than k distinct documents is run again with more chunks. The result is a TREC run scored against `qrels.tsv` (`query_id 0 doc_id relevance`); `ir_measures` gives the same numbers.

Every occurrence of a text is kept in `origins`, and two conflicts are recorded explicitly:

- `label_conflict`: the origins disagree on the label. None happen in v0.1, across all 10,381 shared texts.
- `split_conflict`: the text is in an upstream train split and an upstream test split; it goes to `test`. 1,746 do, all from the bilstm test split overlapping the vzani train splits.

## What it measures

Reported apart, never mixed:

- Retrieval quality ([experiment 02](benchmark/experiments/02-retrieval/)): nDCG@10, recall@10, recall@100 and hit@1 against silver qrels derived from FakeTrue.Br headlines and FACTCK.BR titles. No person judged them and they are incomplete, so every number is a lower bound shared by all rows. [docs/methodology.md](docs/methodology.md) says what that allows.
- Stability ([experiment 03](benchmark/experiments/03-stability/)): re-embedding and rebuilding give the same bytes, and how much of each preset's top-10 matches `exact` of the same model. Agreement with `exact` is about ranking, not relevance.
- The corpus itself ([experiment 01](benchmark/experiments/01-corpus/)): what each source contributed, the overlap, and the FACTCK.BR labels the numeric rating scale gets wrong (469 claims rated "Falso" would be true; Urna's old loader used that scale).

<details>
<summary>Layout</summary>

```
sources/                 sources.toml: pinned revision, files, tree hash and license per upstream
profiles/                models.toml (the example embedders), presets.toml (exact, tiny, hybrid)
benchmark/queries/       queries.jsonl and qrels.tsv (TREC), written by make_queries.py
benchmark/experiments/   NN-slug/{README.md, results.json, table.md}
benchmark/tools/         fetch_sources, prepare, overlap_report, make_queries, build, evaluate,
                         report, stability, promote, export_parquet, render_report
release/v0.1/<build>/    build lock, manifest, SHA256SUMS, CITATION_KEY (the .urna and chunk map are on the hub)
docs/                    methodology, sources (license bill of materials), the gate inside Urna, the MTG reference
```

Sources, models, `.urna` files, Parquet and runs are gitignored. CI lints the tools and checks that `RESULTS.md` is rendered from the tracked results.

</details>

<details>
<summary>Artifacts</summary>

The corpus, the chunk map, the queries and the qrels as Parquet, and every `.urna` of v0.1, are on Hugging Face: [brennercruvinel/fakenews-ptbr-urna-benchmark](https://huggingface.co/datasets/brennercruvinel/fakenews-ptbr-urna-benchmark). `release/v0.1/<build>/SHA256SUMS` pins the bytes; `CITATION_KEY` pins the identity read from inside the file with `urna inspect --json`; `python benchmark/tools/promote.py --check release/v0.1/*` verifies a download.

</details>

## Before the first publication

- [x] Every source in `sources/sources.toml` has a pinned revision, a tree hash and its declared license.
- [x] The embedder is the user's choice, from pinned examples.
- [x] The gate baseline stays the frozen `corpus_next.v1.urna`, identified by its `file_hash`; [docs/urna-gate.md](docs/urna-gate.md) says why it cannot be rebuilt.
- [x] Every source has a license: Apache-2.0 or MIT as declared upstream, and MIT for Fake.br-Corpus, FakeRecogna and FakeTrue.Br as verified by the maintainer, whose repos carry no license file.
- [ ] Each of those three verifications has a checkable source in `license_evidence` ([docs/sources.md](docs/sources.md)).

## License

MIT (`LICENSE`) covers the code, the recipes and the results written in this repo. The corpus text and the queries, which are headlines and titles taken from the sources, keep the license of their source: MIT or Apache-2.0, per source in `docs/sources.md` and per row in the corpus. A built `.urna` carries both, with the attribution each source asks for.
