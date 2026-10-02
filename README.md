# fakenews-ptbr-urna-benchmark

Seven public Brazilian Portuguese fake-news datasets, normalized into one deduplicated corpus and packed into single `.urna` files, with the queries and the relevance judgments that say whether search over them works.

This is the benchmark behind the text corpus of [Urna](https://github.com/hoffresearch/urna): the `data/corpus_next.v1.urna` file its regression gate measures. Until now that corpus was rebuilt by a script inside the engine repo, from datasets nobody else could fetch in the same state. This repo moves the preparation, the build and the evaluation out of the engine, pins every source, and publishes the result on Hugging Face so the gate's baseline has an identity anyone can check.

> Status: scaffold for review. No data, no results, no releases yet.

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

Each one is pinned to a commit or a Hub revision in `sources/sources.toml`, with its license and the loader that reads it. The overlap is real (FakeRecogna republishes Fake.br articles, FakeTrue.Br shares headlines with FakeBr-hf), so every row keeps the list of sources it was found in, and dedup never crosses a train/test line silently.

## What it measures

Two things, reported apart:

- Stability: the same sources and the same recipe give the same `file_hash`, and a compressed preset keeps the exact preset's top-k. This is what Urna's gate checks today, with self-perturbed corpus vectors as queries.
- Retrieval quality: real claims as queries, judged relevant articles as the answer, recall@k and nDCG@k per preset. This is the ruler the gate is missing.

## Build one

Install the `urna` binary from any channel in the [Urna README](https://github.com/hoffresearch/urna), no checkout, then:

```sh
urna setup --yes && urna doctor
```

```sh
export FAKENEWS_DATA=/path/to/fakenews-data   # where the upstream datasets land
```

```sh
python benchmark/tools/fetch_sources.py   # pinned revisions into $FAKENEWS_DATA
```

```sh
python benchmark/tools/prepare.py         # normalize, dedup, splits -> corpus.jsonl + parquet
```

```sh
urna build --spec profiles/exact.toml     # lands in candidates/exact/
```

```sh
python benchmark/tools/evaluate.py candidates/exact/fakenews.urna
```

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

The datasets, `.urna` files and caches are gitignored. `render_report.py --check` is the CI gate.

</details>

<details>
<summary>Artifacts</summary>

The corpus as Parquet and the `.urna` files are on Hugging Face: [brennercruvinel/fakenews-ptbr-urna-benchmark](https://huggingface.co/datasets/brennercruvinel/fakenews-ptbr-urna-benchmark). `release/v0.1/<profile>/SHA256SUMS` pins the bytes, and `CITATION_KEY` pins the identity read from inside the file with `urna inspect --json`.

</details>

## Open before v0.1

- The embedder. The current corpus uses `paraphrase-multilingual-MiniLM-L12-v2`, which is not a preset in Urna's model registry, so `urna build --spec` cannot select it yet. Either the registry gains a multilingual text preset, or the build stays on a Python script here. Potion is English-only and weak on Portuguese.
- Redistribution. Several upstreams are academic releases with no explicit grant, and factck-br may be share-alike. The Hugging Face dataset stays private until each license is confirmed in `docs/sources.md`.
- The gate baseline. Either this build reproduces the current `file_hash` of `corpus_next.v1.urna`, or the gate moves to the v0.1 release and the old hash is kept as history.

## License

Code, recipes, queries and results: MIT (`LICENSE`). The corpus text belongs to its upstream datasets and keeps their terms, listed per source in `docs/sources.md`; a built `.urna` carries the most restrictive of them.
