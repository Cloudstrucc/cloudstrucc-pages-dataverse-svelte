#!/usr/bin/env bash
set -euo pipefail

PAC_BIN="${PAC_BIN:-pac}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENVIRONMENT_URL=""
SOLUTION_NAME="CloudstruccPagesStudio"
OUTPUT_DIR="$ROOT_DIR/dist"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/export-validated-solution.sh \
    --environment-url https://YOURORG.crm3.dynamics.com \
    [--solution-name CloudstruccPagesStudio] \
    [--output-dir ./dist]

Options:
  --environment-url  Source Dataverse environment URL. Required.
  --solution-name    Solution unique name. Default: CloudstruccPagesStudio.
  --output-dir       Export destination. Default: ./dist.
  -h, --help         Show this help text.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment-url)
      ENVIRONMENT_URL="${2:-}"
      shift 2
      ;;
    --solution-name)
      SOLUTION_NAME="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$ENVIRONMENT_URL" ]]; then
  echo "Error: --environment-url is required." >&2
  usage >&2
  exit 2
fi

if ! command -v "$PAC_BIN" >/dev/null 2>&1; then
  echo "Error: '$PAC_BIN' was not found in PATH." >&2
  exit 127
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

"$PAC_BIN" solution export \
  --environment "$ENVIRONMENT_URL" \
  --name "$SOLUTION_NAME" \
  --path "$OUTPUT_DIR/${SOLUTION_NAME}_unmanaged.zip" \
  --overwrite

"$PAC_BIN" solution export \
  --environment "$ENVIRONMENT_URL" \
  --name "$SOLUTION_NAME" \
  --path "$OUTPUT_DIR/${SOLUTION_NAME}_managed.zip" \
  --managed \
  --overwrite

echo "Validated solution exports written to $OUTPUT_DIR"
