# contributing

one experiment per directory under `benchmark/experiments/NN-slug/`, with a `README.md` (the question and the answer), a `results.json` (the numbers) and a `table.md` (rendered). run `python benchmark/tools/render_report.py` after changing any `results.json`; ci fails when `RESULTS.md` is stale. no em dash and no machine-local path in a tracked file.
