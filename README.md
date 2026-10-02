# fakenews-ptbr-urna-benchmark

Seven public Brazilian Portuguese fake-news datasets, normalized into one deduplicated corpus and packed into single `.urna` files, with the queries and the relevance judgments that say whether search over them works.

This is the benchmark behind the text corpus of [Urna](https://github.com/hoffresearch/urna): the `data/corpus_next.v1.urna` file its regression gate measures. Until now that corpus was rebuilt by a script inside the engine repo, from datasets nobody else could fetch in the same state. This repo moves the preparation, the build and the evaluation out of the engine, pins every source, and publishes the result on Hugging Face so the gate's baseline has an identity anyone can check.

> Status: scaffold for review. No data, no tools, no profiles, no results and no releases yet.

## Sources

| Source | Upstream | Rows | Splits kept |
|---|---|---:|---|
| `FakeBr-hf` | [vzani/corpus-fake-br](https://huggingface.co/datasets/vzani/corpus-fake-br) | 7.2k | train, test |
| `FakeTrue.Br-hf` | [vzani/corpus-faketrue-br](https://huggingface.co/datasets/vzani/corpus-faketrue-br) | 3.6k | train, test |
| `Fake.br-Corpus` | [roneysco/Fake.br-Corpus](https://github.com/roneysco/Fake.br-Corpus) | 7.2k | none upstream |
| `FakeRecogna` | [Gabriel-Lino-Garcia/FakeRecogna](https://github.com/Gabriel-Lino-Garcia/FakeRecogna) | 11.9k | none upstream |
| `FakeTrue.Br` | [jpchav98/FakeTrue.Br](https://github.com/jpchav98/FakeTrue.Br) | 3.6k | none upstream |
| `factck-br` | [opit-research/factck-br](https://github.com/opit-research/factck-br) | 1.3k | none upstream |
| `bilstm-combined` | [vzani/portuguese-fake-news-classifier-bilstm-combined](https://huggingface.co/vzani/portuguese-fake-news-classifier-bilstm-combined) | 2.2k | test |

Each one gets pinned to a commit or a Hub revision in `sources/sources.toml`, with its license and the loader that reads it. Those fields are empty in this scaffold and have to be filled before the first publication.

## Documents, chunks and conflicts

The overlap between sources is real (FakeRecogna republishes Fake.br articles, FakeTrue.Br shares headlines with FakeBr-hf), so the corpus is deduplicated by the hash of the normalized text. That hash is the `doc_id`, and it is what `qrels` judges.

A `doc_id` is not a citation. Inside a `.urna` file the identity of a chunk is its `chunk_id`, which Urna derives from the canonical text, the `source_uri`, the byte span and the chunker version ([`chunk.rs`](https://github.com/hoffresearch/urna/blob/main/crates/urna-format/src/chunk.rs)). Each release publishes a chunk map (`chunk_id`, `doc_id`, `source_uri`, `byte_start`, `byte_end`, `chunker_version`), and the evaluation converts every hit to its `doc_id` through that map before scoring, keeping the best rank when several chunks of one document are hit. The map is checked against the chunk ids read from each `.urna`.

Every occurrence of a text is kept in its `origins` list, and two conflicts are recorded explicitly:

- `label_conflict`: the origins disagree on the label. The row stays in the corpus with a null `label`, the divergent labels stay in `origins`, and the row is left out of any label-based metric.
- `split_conflict`: the text appears in an upstream train split and an upstream test split. It goes to `test`, so no test text is also a training text.

The full schema is in the [dataset card](https://huggingface.co/datasets/brennercruvinel/fakenews-ptbr-urna-benchmark).

## What it measures

Two things, reported apart:

- Stability: the same sources and the same recipe give the same `file_hash`, and the compressed and approximate profiles are compared with `exact`, which is the reference for ranking agreement. This is what Urna's gate checks today, with self-perturbed corpus vectors as queries.
- Retrieval quality: real claims as queries and `qrels` as the judged answer, recall@k and nDCG@k for every profile, `exact` included. Relevance comes from the judgments, never from agreement with `exact`. This is the ruler the gate is missing.

## Planned workflow

None of the scripts or profiles below exist yet. This is the flow the tasks build toward, not a set of working instructions.

```sh
urna setup --yes && urna doctor
export FAKENEWS_DATA=/path/to/fakenews-data
python benchmark/tools/fetch_sources.py                  # pinned revisions into $FAKENEWS_DATA
python benchmark/tools/prepare.py                        # normalize, dedup, conflicts, splits
urna build --spec profiles/exact.toml                    # lands in candidates/exact/
python benchmark/tools/evaluate.py candidates/exact/fakenews.urna
```

Running `urna build` from an installed binary, without a checkout of the engine, depends on two things Urna does not do yet:

- shipping the build runner (`urna_forge.py`) and its Python dependencies in the payload `urna setup` installs;
- a registry preset for `paraphrase-multilingual-MiniLM-L12-v2`, the multilingual model the current corpus uses. Potion is English-only and weak on Portuguese.

Until both land, the build either runs against a checkout of Urna or stays on a Python script in this repo.

<details>
<summary>Layout</summary>

```
sources/                 sources.toml: url, pinned revision, license, loader per upstream
profiles/                the build recipes (exact, tiny, hybrid), urna build --spec
benchmark/queries/       queries.jsonl and qrels.tsv: real claims and judged relevance
benchmark/experiments/   NN-slug/{README.md, results.json, table.md}
benchmark/tools/         fetch_sources, prepare, overlap_report, export_parquet, evaluate, promote, render_report
release/v0.1/<profile>/  build lock, stripped manifest, SHA256SUMS, CITATION_KEY
docs/                    methodology, sources (license bill of materials), changelog
```

The datasets, `.urna` files, Parquet and caches are gitignored. `render_report.py --check` will be the CI gate.

</details>

<details>
<summary>Artifacts</summary>

The corpus and the chunk map as Parquet, and the `.urna` files, will be on Hugging Face: [brennercruvinel/fakenews-ptbr-urna-benchmark](https://huggingface.co/datasets/brennercruvinel/fakenews-ptbr-urna-benchmark). `release/v0.1/<profile>/SHA256SUMS` pins the bytes, and `CITATION_KEY` pins the identity read from inside the file with `urna inspect --json`.

</details>

## Before the first publication

- [ ] Every source in `sources/sources.toml` has a pinned revision and a license.
- [ ] `docs/sources.md` confirms the redistribution terms of each source; factck-br may be share-alike.
- [ ] The embedder is decided: a multilingual registry preset in Urna, or a script here.
- [ ] The gate baseline is decided: either this build reproduces the current `file_hash` of `corpus_next.v1.urna`, or the gate moves to the v0.1 release and the old hash is kept as history.

The Hugging Face dataset stays private until all four are done.

## Citation

`CITATION.cff` cites Urna, the one reference for this benchmark and its corpus. Cite the upstream datasets when you use their rows.

## License

MIT (`LICENSE`) covers the code, the recipes and the results written in this repo. It does not cover the corpus text, nor queries taken from upstream sources: those keep the terms of their source, listed in `docs/sources.md`, and a built `.urna` carries the most restrictive of them.
