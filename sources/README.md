# sources

`sources.toml` is the one list of upstream datasets: where each comes from, the revision it is pinned to, its license, and the loader in `benchmark/tools/prepare.py` that reads it. `fetch_sources.py` refuses a source whose revision is not pinned.
