#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ENVIRONMENT_URL=""
EXPORT_MANAGED=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment-url) ENVIRONMENT_URL="${2:-}"; shift 2 ;;
    --managed) EXPORT_MANAGED=true; shift ;;
    -h|--help)
      echo "Usage: ./scripts/first-install.sh --environment-url URL [--managed]"
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$ENVIRONMENT_URL" ]] || { echo "--environment-url is required" >&2; exit 2; }

"$ROOT_DIR/scripts/bootstrap-dataverse.sh" --environment-url "$ENVIRONMENT_URL"
args=(--environment-url "$ENVIRONMENT_URL")
[[ "$EXPORT_MANAGED" == true ]] && args+=(--managed)
"$ROOT_DIR/scripts/export-solutions.sh" "${args[@]}"
