#!/bin/sh
# Follow the README from a fresh clone and an empty data dir, and compare every
# identity with what the repo pins: source tree hashes, corpus_hash, the queries,
# and the file_hash of release/<version>/<model>-exact for each model given.
#
#   sh benchmark/tools/check_clean.sh WORK_DIR [MODEL ...]     (default models: potion minilm)
#
# Needs git, uv and the urna cli on PATH. WORK_DIR must not exist yet.
set -eu
WORK=${1:?usage: check_clean.sh WORK_DIR [MODEL ...]}
shift
MODELS=${*:-potion minilm}
VERSION=v0.1
REPO_URL=$(git -C "$(dirname "$0")" remote get-url origin)
[ -e "$WORK" ] && { echo "error: $WORK exists" >&2; exit 2; }
mkdir -p "$WORK"
git clone -q "$REPO_URL" "$WORK/repo"
cd "$WORK/repo"
uv sync -q
export FAKENEWS_DATA="$WORK/data" HF_HUB_DISABLE_PROGRESS_BARS=1
fail=0
uv run python benchmark/tools/fetch_sources.py >/dev/null && echo "ok   source tree hashes match sources.toml" || { echo "FAIL source tree hashes"; fail=1; }
want=$(git show HEAD:benchmark/experiments/01-corpus/results.json | python3 -c "import json,sys;print([n for t in json.load(sys.stdin)['tables'] for n in t.get('notes',[]) if 'corpus_hash' in n][0].split()[1].rstrip(','))")
got=$(uv run python benchmark/tools/prepare.py | python3 -c "import json,sys;print(json.load(sys.stdin)['corpus_hash'])")
[ "$want" = "$got" ] && echo "ok   corpus_hash $got" || { echo "FAIL corpus_hash: want $want got $got"; fail=1; }
uv run python benchmark/tools/make_queries.py --check && echo "ok   queries and qrels match" || { echo "FAIL queries"; fail=1; }
for m in $MODELS; do
  uv run python benchmark/tools/build.py --model "$m" --preset exact >/dev/null 2>&1
  w=$(python3 -c "import json;print(json.load(open('release/$VERSION/$m-exact/build.lock.json'))['output']['file_hash'])")
  g=$(python3 -c "import json;print(json.load(open('candidates/$m-exact/build.lock.json'))['output']['file_hash'])")
  [ "$w" = "$g" ] && echo "ok   $m-exact file_hash $g" || { echo "FAIL $m-exact file_hash: want $w got $g"; fail=1; }
  urna validate "candidates/$m-exact/fakenews.urna" >/dev/null && echo "ok   $m-exact urna validate" || { echo "FAIL $m-exact urna validate"; fail=1; }
done
exit $fail
