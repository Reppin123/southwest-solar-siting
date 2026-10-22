#!/usr/bin/env bash
# Package the processed files that are too big for git (over 95 MB) and upload
# them to the GitHub release v1.0-data, one file at a time to keep disk use low.
# Also uploads a bundle of every other processed layer for people who do not use git.
#
# Usage: scripts/package_release.sh [--dry-run]     (or ONLY=<path>|bundle scripts/package_release.sh)
# Needs: gh (logged in), zstd, tar. Writes only to release-staging/ (deleted per file).
set -euo pipefail
cd "$(dirname "$0")/.."

GH=${GH:-/opt/homebrew/bin/gh}
REPO=Reppin123/southwest-solar-siting
TAG=v1.0-data
STAGE=release-staging
SUMS="$STAGE/SHA256SUMS.txt"
DRY=${1:-}

BIG_FILES=(
  data/processed/land/slope.tif
  data/processed/land/exclusions_full.gpkg
  data/processed/land/ownership.gpkg
  data/processed/land/blm_solar_available.gpkg
)

# ONLY=<path>|bundle processes one item per run (keeps each run short).
if [ -n "${ONLY:-}" ]; then
  [ "$ONLY" = bundle ] && BIG_ONLY=() || BIG_ONLY=("$ONLY")
else
  BIG_ONLY=("${BIG_FILES[@]}")
fi

mkdir -p "$STAGE"
touch "$SUMS"   # kept between runs so finished uploads are skipped

if ! "$GH" release view "$TAG" -R "$REPO" >/dev/null 2>&1; then
  [ "$DRY" = "--dry-run" ] || "$GH" release create "$TAG" -R "$REPO" --target main \
    --title "v1.0-data: large processed layers" \
    --notes "Processed data files too large for git (over 95 MB), compressed with zstd, plus a bundle of all other processed layers. See DATA.md in the repo for what each file is, checksums and how to unpack. Raw downloads (about 11 GB) are not here; re-fetch them with uv run --script pipeline/run_all.py."
fi

upload() {  # $1 = file in $STAGE, $2 = optional extra checksum line; lines recorded only after a successful upload
  local line; line="sha256 $(shasum -a 256 "$1" | cut -d' ' -f1)  $(basename "$1")  ($(du -h "$1" | cut -f1))"
  [ "$DRY" = "--dry-run" ] || "$GH" release upload "$TAG" "$1" -R "$REPO" --clobber
  { [ -n "${2:-}" ] && echo "$2"; echo "$line"; } | tee -a "$SUMS"
  rm -f "$1"
}

for f in "${BIG_ONLY[@]+"${BIG_ONLY[@]}"}"; do
  out="$STAGE/$(basename "$f").zst"
  if grep -q " $(basename "$out")  " "$SUMS"; then echo "skip $out (already uploaded)"; continue; fi
  orig="original sha256 $(shasum -a 256 "$f" | cut -d' ' -f1)  $f"
  zstd -q -T0 -10 -f "$f" -o "$out"
  upload "$out" "$orig"
done

# Bundle of every other processed layer (same files as in git, minus the work/ cache).
bundle="$STAGE/processed_layers_small.tar.zst"
if [ -z "${ONLY:-}" -o "${ONLY:-}" = bundle ] && ! grep -q " $(basename "$bundle")  " "$SUMS"; then
tar --exclude 'data/processed/sites/work' --exclude '.DS_Store' \
    $(printf -- "--exclude %s " "${BIG_FILES[@]}") \
    -cf - data/processed | zstd -q -T0 -10 -o "$bundle"
upload "$bundle"
fi

[ "$DRY" = "--dry-run" ] || "$GH" release upload "$TAG" "$SUMS" -R "$REPO" --clobber
echo "done; checksums in $SUMS"
