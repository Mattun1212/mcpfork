#!/bin/bash
set -e

# Set up logging (stdout + file)
LOG_FILE="$HOME/.mcp/mcp-atlassian-mutton-install.log"
mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "====== Install started: $(date) ======"

echo "======================================"
echo "MCP Atlassian Installer"
echo "======================================"
echo ""

# Show log file path on error exit
trap 'rc=$?; [ $rc -ne 0 ] && echo "Installation failed. Log file: $LOG_FILE"' EXIT

# Check if uv is installed
check_uv() {
    if command -v uv &> /dev/null; then
        echo "[OK] uv found: $(uv --version)"
        return 0
    fi
    return 1
}

# Check if git is installed
check_git() {
    if command -v git &> /dev/null; then
        echo "[OK] git found: $(git --version)"
        return 0
    fi
    return 1
}

# Install git
install_git() {
    echo "[..] Installing git..."
    if [[ "$(uname)" == "Darwin" ]]; then
        if command -v brew &> /dev/null; then
            brew install git
        else
            echo "[..] Homebrew not found. Installing git via Xcode Command Line Tools..."
            xcode-select --install
        fi
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y git
    else
        echo "[FAIL] Could not install git automatically."
        echo "Please install Git from https://git-scm.com/ and re-run this script."
        exit 1
    fi

    if ! command -v git &> /dev/null; then
        echo "[FAIL] git installation failed."
        echo "Please install Git from https://git-scm.com/ and re-run this script."
        exit 1
    fi
    echo "[OK] git installed: $(git --version)"
}

# Install uv
install_uv() {
    echo "[..] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        echo "[FAIL] uv installation failed."
        echo "Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    echo "[OK] uv installed: $(uv --version)"
}

main() {
    # Check/Install uv
    if ! check_uv; then
        install_uv
    fi

    # Check/Install git (required for uvx --from git+https://...)
    if ! check_git; then
        install_git
    fi

    # Prompt for tokens
    echo ""
    echo "======================================"
    echo "Configuration Setup"
    echo "======================================"
    echo ""
    echo "Please generate your API tokens:"
    echo "  JIRA: https://jira.rakuten-it.com/jira > Profile > Personal Access Tokens"
    echo "  Confluence: https://confluence.rakuten-it.com/confluence > Settings > Personal Access Tokens"
    echo ""
    read -sp "Enter your JIRA Personal Access Token: " JIRA_TOKEN
    echo ""
    read -sp "Enter your Confluence Personal Access Token: " CONFLUENCE_TOKEN
    echo ""
    echo ""

    # Update .claude.json
    CLAUDE_JSON="$HOME/.claude.json"
    echo "[..] Updating .claude.json..."

    if [ ! -f "$CLAUDE_JSON" ]; then
        echo "[FAIL] .claude.json not found. Please run Claude Code first, then re-run this script."
        exit 1
    fi

    export JIRA_TOKEN CONFLUENCE_TOKEN
    python3 <<'PYEOF'
import json, os, sys

jira_token = os.environ['JIRA_TOKEN']
confluence_token = os.environ['CONFLUENCE_TOKEN']
claude_json_path = os.path.expanduser("~/.claude.json")

with open(claude_json_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['mcp-atlassian-mutton'] = {
    "type": "stdio",
    "command": "uvx",
    "args": [
        "--from", "git+https://github.com/Mattun1212/mcpfork.git",
        "mcp-atlassian"
    ],
    "env": {
        "CONFLUENCE_URL": "https://confluence.rakuten-it.com/confluence",
        "CONFLUENCE_PERSONAL_TOKEN": confluence_token,
        "JIRA_URL": "https://jira.rakuten-it.com/jira",
        "JIRA_PERSONAL_TOKEN": jira_token
    }
}

with open(claude_json_path, 'w') as f:
    json.dump(config, f, indent=2)

print("Configuration updated successfully")
PYEOF

    echo "[OK] .claude.json updated"

    echo ""
    echo "======================================"
    echo "Installation Complete!"
    echo "======================================"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code"
    echo "  2. Run: /mcp"
    echo "  3. Verify 'mcp-atlassian-mutton' is connected"
    echo ""
    echo "Log file: $LOG_FILE"
    echo ""
}

main
