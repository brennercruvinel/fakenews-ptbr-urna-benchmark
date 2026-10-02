# 04 clean install

hypothesis: the instructions in the README rebuild the same data and the same files on a machine that has only git, uv and the urna cli.
method: `benchmark/tools/check_clean.sh` clones the repo into an empty directory, runs `uv sync`, fetches the seven sources into an empty FAKENEWS_DATA, prepares the corpus, checks the queries, and builds the potion and minilm `exact` files, comparing each identity with what the repo pins; `record_clean.py` writes this result only when every check passed, on the commit the checkout is at, for the prepared corpus.
verdict: on commit 1bc33d5, every identity came back: the seven tree hashes, corpus_hash e884b982, the queries and qrels, and the potion and minilm file_hashes, the minilm one after downloading the model and embedding the corpus from scratch. The installed urna 0.5.1 validated both files. Same machine class as the builds (Apple M4, cpu); another platform may embed to different floats, which the build lock would show.

The table is in `table.md`.
