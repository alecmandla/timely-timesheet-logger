#!/bin/bash
# Install script for Timely MCP Server
# Run this once on your Mac to set up everything.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Timely MCP Server Setup ==="
echo ""

# 1. Create a virtual environment
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# 2. Install dependencies
echo "Installing dependencies..."
"$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet

# 3. Install Playwright browsers
echo "Installing Chromium for Playwright (this may take a minute)..."
"$SCRIPT_DIR/venv/bin/python" -m playwright install chromium

# 4. Create the browser data directory
mkdir -p "$HOME/.timely-mcp/browser-data"

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Add this MCP server to your Claude Code / Cowork config."
echo "   Add the following to your MCP settings:"
echo ""
echo "   \"timely-headless\": {"
echo "     \"command\": \"$SCRIPT_DIR/venv/bin/python\","
echo "     \"args\": [\"$SCRIPT_DIR/timely_mcp.py\"]"
echo "   }"
echo ""
echo "2. On first use, call the 'timely_login' tool to sign in."
echo "   This opens a visible browser window ONCE for you to log in."
echo "   After that, everything runs headlessly in the background."
echo ""
