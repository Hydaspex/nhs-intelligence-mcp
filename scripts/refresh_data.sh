#!/bin/bash
set -e

DB_DIR="$HOME/Library/Application Support/nhs-intel"
LOG="$HOME/Library/Logs/nhs-intel-refresh.log"

echo "$(date): starting refresh" >> "$LOG"

RELEASE_URL="https://github.com/Hydaspex/nhs-intelligence-mcp/releases/latest/download/nhs_intel.db"
SHA_URL="https://github.com/Hydaspex/nhs-intelligence-mcp/releases/latest/download/nhs_intel.db.sha256"

curl -fsSL "$RELEASE_URL" -o "$DB_DIR/nhs_intel.db.tmp"
curl -fsSL "$SHA_URL"     -o "$DB_DIR/nhs_intel.db.sha256"

# The .sha256 file was produced by `sha256sum nhs_intel.db` on Linux; its
# first field is the hash.  Compare directly so we don't need the filename to
# match (we downloaded to .tmp to keep the old DB intact during the check).
cd "$DB_DIR"
EXPECTED=$(awk '{print $1}' nhs_intel.db.sha256)
ACTUAL=$(shasum -a 256 nhs_intel.db.tmp | awk '{print $1}')

if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "$(date): checksum failed — aborting" >> "$LOG"
  rm -f nhs_intel.db.tmp
  exit 1
fi

mv nhs_intel.db.tmp nhs_intel.db
echo "$(date): refresh complete" >> "$LOG"
