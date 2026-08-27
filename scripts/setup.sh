#!/bin/bash
set -e

# First-time setup for nhs-intel: creates the DB directory, downloads the
# latest release, and registers the weekly refresh job.

REPO="Hydaspex/nhs-intelligence-mcp"
RELEASE_URL="https://github.com/$REPO/releases/latest/download/nhs_intel.db"
SHA_URL="https://github.com/$REPO/releases/latest/download/nhs_intel.db.sha256"

# --------------------------------------------------------------------------
# 1. Determine platform and data directory
# --------------------------------------------------------------------------
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
  DB_DIR="$HOME/Library/Application Support/nhs-intel"
else
  DB_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/nhs-intel"
fi

mkdir -p "$DB_DIR"
echo "DB directory: $DB_DIR"

# --------------------------------------------------------------------------
# 2. Download nhs_intel.db and verify checksum
# --------------------------------------------------------------------------
echo "Downloading nhs_intel.db ..."
curl -fsSL "$RELEASE_URL" -o "$DB_DIR/nhs_intel.db.tmp"
curl -fsSL "$SHA_URL"     -o "$DB_DIR/nhs_intel.db.sha256"

EXPECTED=$(awk '{print $1}' "$DB_DIR/nhs_intel.db.sha256")
ACTUAL=$(shasum -a 256 "$DB_DIR/nhs_intel.db.tmp" | awk '{print $1}')

if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "ERROR: checksum mismatch — download may be corrupt." >&2
  rm -f "$DB_DIR/nhs_intel.db.tmp"
  exit 1
fi

mv "$DB_DIR/nhs_intel.db.tmp" "$DB_DIR/nhs_intel.db"
echo "Downloaded and verified nhs_intel.db"

# --------------------------------------------------------------------------
# 3. Determine where this script lives (for the refresh script path)
# --------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REFRESH_SCRIPT="$SCRIPT_DIR/refresh_data.sh"
chmod +x "$REFRESH_SCRIPT"

# --------------------------------------------------------------------------
# 4. Register weekly refresh job
# --------------------------------------------------------------------------
if [ "$OS" = "Darwin" ]; then
  PLIST_LABEL="com.hydaspex.nhs-intel-refresh"
  PLIST_DIR="$HOME/Library/LaunchAgents"
  PLIST_PATH="$PLIST_DIR/$PLIST_LABEL.plist"

  mkdir -p "$PLIST_DIR"
  cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REFRESH_SCRIPT</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>0</integer>
    <key>Hour</key><integer>2</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$HOME/Library/Logs/nhs-intel-refresh.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/Library/Logs/nhs-intel-refresh.log</string>
</dict>
</plist>
PLIST

  launchctl load "$PLIST_PATH"
  echo "Registered launchd job: $PLIST_LABEL (runs Sundays at 02:00)"

else
  # Linux: write a crontab entry (avoids requiring systemd user session)
  CRON_ENTRY="0 2 * * 0 /bin/bash $REFRESH_SCRIPT"
  (crontab -l 2>/dev/null | grep -v "nhs-intel-refresh"; echo "$CRON_ENTRY") | crontab -
  echo "Registered cron job (runs Sundays at 02:00): $CRON_ENTRY"
fi

# --------------------------------------------------------------------------
# 5. Print .mcp.json snippet
# --------------------------------------------------------------------------
cat <<MCP

Done.  Add the following to your Claude Code .mcp.json (project or global):

{
  "mcpServers": {
    "nhs-intel": {
      "command": "uv",
      "args": ["run", "--project", "$SCRIPT_DIR/..", "nhs-intel-mcp"],
      "env": {
        "NHS_INTEL_DB": "$DB_DIR/nhs_intel.db"
      }
    }
  }
}
MCP
