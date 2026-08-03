#!/bin/sh
set -eu
SOURCE="${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
OUTPUT="${2:-$SOURCE/dist}"
RELEASE="${BAMBO_RELEASE:-local}"
API_BASE_URL="${BAMBO_API_BASE_URL:-/backend}"
rm -rf "$OUTPUT"
mkdir -p "$OUTPUT"
cp "$SOURCE/index.html" "$OUTPUT/index.html"
cp -R "$SOURCE/src" "$OUTPUT/src"
rm -rf "$OUTPUT/src/documents"
sed -e "s|\${BAMBO_API_BASE_URL}|$API_BASE_URL|g" \
    -e "s|\${BAMBO_ENVIRONMENT}|production|g" \
    -e "s|\${BAMBO_RELEASE}|$RELEASE|g" \
    -e "s|\${BAMBO_REQUEST_TIMEOUT_MS}|30000|g" \
    "$SOURCE/runtime-config.template.js" > "$OUTPUT/runtime-config.js"
if grep -RIE 'useMockApi[[:space:]]*:[[:space:]]*true|127\.0\.0\.1|localhost|debug_code[[:space:]]*:' "$OUTPUT"; then
  echo "Forbidden development value found in production artifact" >&2
  exit 1
fi
printf 'Production artifact created: %s (release %s)\n' "$OUTPUT" "$RELEASE"

