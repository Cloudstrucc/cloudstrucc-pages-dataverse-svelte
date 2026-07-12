#!/usr/bin/env bash
set -euo pipefail

PAC_BIN="${PAC_BIN:-pac}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' was not found in PATH." >&2
    exit 127
  fi
}

pack_solution() {
  local folder="$1"
  local zipfile="$2"
  local package_type="$3"

  if [[ ! -d "$folder" ]]; then
    echo "Error: unpacked solution folder not found: $folder" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$zipfile")"

  local args=(
    solution pack
    --zipfile "$zipfile"
    --folder "$folder"
    --packagetype "$package_type"
    --allowWrite
    --clobber
  )

  if [[ "$package_type" == "Managed" ]]; then
    args+=(--useUnmanagedFileForMissingManaged)
  fi

  echo "Packing $package_type solution: $zipfile"
  "$PAC_BIN" "${args[@]}"
}

require_command "$PAC_BIN"

pack_solution \
  "$ROOT_DIR/solution/schema/unpacked" \
  "$ROOT_DIR/solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_unmanaged.zip" \
  "Unmanaged"

pack_solution \
  "$ROOT_DIR/solution/schema/unpacked" \
  "$ROOT_DIR/solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_managed.zip" \
  "Managed"

pack_solution \
  "$ROOT_DIR/solution/full/unpacked" \
  "$ROOT_DIR/solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip" \
  "Unmanaged"

pack_solution \
  "$ROOT_DIR/solution/full/unpacked" \
  "$ROOT_DIR/solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip" \
  "Managed"

echo "Solution packaging completed successfully."
