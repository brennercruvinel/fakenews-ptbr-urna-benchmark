#!/bin/sh
# Follow the README from a fresh clone and an empty data dir, and compare every
# identity with what the repo pins: source tree hashes, corpus_hash, the queries,
# and the file_hash of release/<version>/<model>-exact for each model given.
#
#   sh benchmark/tools/check_clean.sh WORK_DIR [MODEL ...]     (default models: potion minilm)
#   python benchmark/tools/record_clean.py WORK_DIR            (writes experiment 04 from the result)
#
# Needs git, uv and the urna cli on PATH. WORK_DIR must not exist yet. Every check
# lands in WORK_DIR/checks.tsv (status, check, value) next to WORK_DIR/commit.
set -eu
WORK=${1:?usage: check_clean.sh WORK_DIR [MODEL ...]}
shift
MODELS=${*:-potion minilm}
VERSION=v0.1
REPO_URL=$(git -C "$(dirname "$0")" remote get-url origin)
[ -e "$WORK" ] && { echo "error: $WORK exists" >&2; exit 2; }
mkdir -p "$WORK"
WORK=$(cd "$WORK" && pwd)
git clone -q "$REPO_URL" "$WORK/repo"
cd "$WORK/repo"
git rev-parse HEAD > "$WORK/commit"
uv sync -q
export FAKENEWS_DATA="$WORK/data" HF_HUB_DISABLE_PROGRESS_BARS=1
: > "$WORK/checks.tsv"
fail=0
check() {  # status check value
  printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$WORK/checks.tsv"
  printf '%-4s %s %s\n' "$1" "$2" "$3"
  [ "$1" = ok ] || fail=1
}
if uv run python benchmark/tools/fetch_sources.py >/dev/null; then check ok "source tree hashes" "match sources.toml"; else check FAIL "source tree hashes" "see fetch_sources.py"; fi
want=$(git show HEAD:benchmark/experiments/01-corpus/results.json | python3 -c "import json,sys;print(json.load(sys.stdin)['corpus_hash'])")
got=$(uv run python benchmark/tools/prepare.py | python3 -c "import json,sys;print(json.load(sys.stdin)['corpus_hash'])")
if [ "$want" = "$got" ]; then check ok corpus_hash "$got"; else check FAIL corpus_hash "want $want got $got"; fi
if uv run python benchmark/tools/make_queries.py --check; then check ok "queries and qrels" "match the tracked files"; else check FAIL "queries and qrels" "differ"; fi
for m in $MODELS; do
  uv run python benchmark/tools/build.py --model "$m" --preset exact >/dev/null 2>&1
  w=$(python3 -c "import json;print(json.load(open('release/$VERSION/$m-exact/build.lock.json'))['output']['file_hash'])")
  g=$(python3 -c "import json;print(json.load(open('candidates/$m-exact/build.lock.json'))['output']['file_hash'])")
  if [ "$w" = "$g" ]; then check ok "$m-exact file_hash" "$g"; else check FAIL "$m-exact file_hash" "want $w got $g"; fi
  if urna validate "candidates/$m-exact/fakenews.urna" >/dev/null; then check ok "$m-exact urna validate" "$(urna --version)"; else check FAIL "$m-exact urna validate" "failed"; fi
done
exit $fail
