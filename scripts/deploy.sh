#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENVIRONMENT_URL=""
PACKAGE_TYPE="managed"
SETTINGS_FILE="$ROOT_DIR/config/deployment-settings.prod.json"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/deploy.sh \
    --environment-url https://YOURORG.crm3.dynamics.com \
    [--package-type managed|unmanaged] \
    [--settings-file ./config/deployment-settings.prod.json]

Options:
  --environment-url  Target Dataverse environment URL. Required.
  --package-type     managed or unmanaged. Default: managed.
  --settings-file    Deployment settings JSON. Use an empty string to omit it.
  -h, --help         Show this help text.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment-url)
      ENVIRONMENT_URL="${2:-}"
      shift 2
      ;;
    --package-type)
      PACKAGE_TYPE="${2:-}"
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

if [[ -z "$ENVIRONMENT_URL" ]]; then
  echo "Error: --environment-url is required." >&2
  usage >&2
  exit 2
fi

if [[ "$PACKAGE_TYPE" != "managed" && "$PACKAGE_TYPE" != "unmanaged" ]]; then
  echo "Error: --package-type must be 'managed' or 'unmanaged'." >&2
  exit 2
fi

"$SCRIPT_DIR/build-solutions.sh"

SOLUTION_PATH="$ROOT_DIR/solution/full/packed/CloudstruccPagesStudio_1_0_0_0_${PACKAGE_TYPE}.zip"
IMPORT_ARGS=(
  --environment-url "$ENVIRONMENT_URL"
  --solution-path "$SOLUTION_PATH"
)

if [[ -n "$SETTINGS_FILE" ]]; then
  IMPORT_ARGS+=(--settings-file "$SETTINGS_FILE")
fi

"$SCRIPT_DIR/import-solution.sh" "${IMPORT_ARGS[@]}"
