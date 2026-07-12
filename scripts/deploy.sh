#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENVIRONMENT_URL=""
PACKAGE_TYPE="unmanaged"
SOLUTION_PATH=""
SETTINGS_FILE=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy.sh --environment-url URL [--package-type unmanaged|managed]
                      [--solution-path PATH] [--settings-file PATH]

Deploys an authoritative solution ZIP previously exported from Dataverse.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment-url) ENVIRONMENT_URL="${2:-}"; shift 2 ;;
    --package-type) PACKAGE_TYPE="${2:-}"; shift 2 ;;
    --solution-path) SOLUTION_PATH="${2:-}"; shift 2 ;;
    --settings-file) SETTINGS_FILE="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$ENVIRONMENT_URL" ]] || { echo "--environment-url is required" >&2; exit 2; }
[[ "$PACKAGE_TYPE" == "managed" || "$PACKAGE_TYPE" == "unmanaged" ]] || { echo "Invalid --package-type" >&2; exit 2; }

if [[ -z "$SOLUTION_PATH" ]]; then
  SOLUTION_PATH="$ROOT_DIR/solution/exported/full/CloudstruccPagesStudio_1_0_5_0_${PACKAGE_TYPE}.zip"
fi
[[ -f "$SOLUTION_PATH" ]] || {
  echo "Exported solution not found: $SOLUTION_PATH" >&2
  echo "Create it first with scripts/first-install.sh or scripts/export-solutions.sh." >&2
  exit 1
}

args=(--environment-url "$ENVIRONMENT_URL" --solution-path "$SOLUTION_PATH")
[[ -n "$SETTINGS_FILE" ]] && args+=(--settings-file "$SETTINGS_FILE")
exec "$SCRIPT_DIR/import-solution.sh" "${args[@]}"
