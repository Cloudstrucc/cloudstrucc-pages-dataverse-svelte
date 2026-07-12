#!/usr/bin/env bash
set -euo pipefail

PAC_BIN="${PAC_BIN:-pac}"
ENVIRONMENT_URL=""
SOLUTION_PATH=""
SETTINGS_FILE=""

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/import-solution.sh \
    --environment-url https://YOURORG.crm3.dynamics.com \
    --solution-path ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip \
    [--settings-file ./config/deployment-settings.dev.json]

Options:
  --environment-url  Target Dataverse environment URL. Required.
  --solution-path    Path to a managed or unmanaged solution ZIP. Required.
  --settings-file    Optional deployment settings JSON file.
  -h, --help         Show this help text.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment-url)
      ENVIRONMENT_URL="${2:-}"
      shift 2
      ;;
    --solution-path)
      SOLUTION_PATH="${2:-}"
      shift 2
      ;;
    --settings-file)
      SETTINGS_FILE="${2:-}"
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

if [[ -z "$ENVIRONMENT_URL" || -z "$SOLUTION_PATH" ]]; then
  echo "Error: --environment-url and --solution-path are required." >&2
  usage >&2
  exit 2
fi

if ! command -v "$PAC_BIN" >/dev/null 2>&1; then
  echo "Error: '$PAC_BIN' was not found in PATH." >&2
  exit 127
fi

if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "Error: solution file not found: $SOLUTION_PATH" >&2
  exit 1
fi

SOLUTION_PATH="$(cd "$(dirname "$SOLUTION_PATH")" && pwd)/$(basename "$SOLUTION_PATH")"

args=(
  solution import
  --environment "$ENVIRONMENT_URL"
  --path "$SOLUTION_PATH"
  --publish-changes
  --async
)

if [[ -n "$SETTINGS_FILE" ]]; then
  if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "Error: settings file not found: $SETTINGS_FILE" >&2
    exit 1
  fi
  SETTINGS_FILE="$(cd "$(dirname "$SETTINGS_FILE")" && pwd)/$(basename "$SETTINGS_FILE")"
  args+=(--settings-file "$SETTINGS_FILE")
fi

echo "Importing solution into $ENVIRONMENT_URL"
"$PAC_BIN" "${args[@]}"
