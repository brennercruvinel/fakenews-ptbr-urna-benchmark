# What came from mtg-urna-benchmark

This repo follows the layout of [mtg-urna-benchmark](https://github.com/brennercruvinel/mtg-urna-benchmark) at `main` (v0.3.2). This note records what was reused, what was left behind and why, so the two can be compared without reading both trees.

## Reused

- The layout: `benchmark/experiments/NN-slug/{README.md, results.json, table.md}`, `benchmark/tools/`, `release/<version>/<profile>/` and `docs/`.
- `render_report.py`, almost verbatim: the same `results.json` contract, the same `--check` CI gate. Only the header changed.
- The release directory: the artifact, `build.lock.json`, the manifest with its item list moved to `items.jsonl.gz`, `SHA256SUMS`, and `CITATION_KEY` read from inside the file with `urna inspect --json`.
- The CI guards: ruff on the tools, the stale-report check, no em dash and no machine-local path in a tracked file.

## Left behind

- `URNA_REPO`. Every MTG tool needs a checkout of Urna, through `_bench_env.urna_repo()`, because `urna build --spec` runs `python/tools/urna_forge.py` from the checkout. Here the build uses `urna.build` from the published wheel, and no tool reads a checkout.
- `urna build --spec`. The forge is not in the installed payload, and Urna 0.5.1's registry has no multilingual text model. `benchmark/tools/build.py` takes its place; the model list is `profiles/models.toml`.
- The `NEST` magic and the 0.4.0 instructions. The MTG files were built before the rename and its README still asks for a v0.4.0 checkout; nothing here predates 0.5.
- `SPELLBOOK_DATA` and other legacy aliases. One variable, `FAKENEWS_DATA`.

## Found in the MTG repo, not fixed there

- `benchmark/experiments/11-intra-codecs/samples/.!67909!avif-s6-q48.avif` is a partial-copy temp file tracked by mistake.
- The README's build section requires `URNA_REPO` at v0.4.0 or later; with 0.5 the forge path and the payload changed.
- The `RESULTS.md` header still says "mtg card corpus benchmark", not the repo name.

These belong in a pull request on that repo; this one only avoids copying them.
