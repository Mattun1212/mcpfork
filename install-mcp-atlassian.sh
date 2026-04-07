#!/bin/bash
set -e

echo "======================================"
echo "MCP Atlassian Auto Installer"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3.10+ is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
            return 0
        fi
    fi
    return 1
}

# Install Python on macOS
install_python_mac() {
    echo -e "${YELLOW}Python 3.10+ not found. Installing...${NC}"

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add Homebrew to PATH
        if [[ $(uname -m) == 'arm64' ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi

    echo -e "${YELLOW}Installing Python...${NC}"
    brew install python@3.12
    echo -e "${GREEN}✓${NC} Python installed successfully"
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    OS='Mac';;
        Linux*)     OS='Linux';;
        *)          echo -e "${RED}✗${NC} Unsupported OS"; exit 1;;
    esac
    echo -e "${GREEN}✓${NC} Detected OS: $OS"
}

# Main installation
main() {
    detect_os

    # Check/Install Python
    if ! check_python; then
        if [ "$OS" = "Mac" ]; then
            install_python_mac
        else
            echo -e "${RED}✗${NC} Python 3.10+ required. Please install: https://www.python.org/downloads/"
            exit 1
        fi
    fi

    # Create MCP directory
    MCP_DIR="$HOME/.mcp/mcp-atlassian"
    echo ""
    echo -e "${YELLOW}Creating installation directory...${NC}"
    mkdir -p "$MCP_DIR"
    cd "$MCP_DIR"
    echo -e "${GREEN}✓${NC} Directory created: $MCP_DIR"

    # Create virtual environment
    echo ""
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓${NC} Virtual environment created"

    # Activate virtual environment
    source .venv/bin/activate

    # Upgrade pip
    echo ""
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} pip upgraded"

    # Install MCP Atlassian
    echo ""
    echo -e "${YELLOW}Installing MCP Atlassian (this may take a few minutes)...${NC}"
    pip install git+https://github.com/Mattun1212/mcpfork.git > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} MCP Atlassian installed"

    # Test installation
    echo ""
    echo -e "${YELLOW}Testing installation...${NC}"
    if .venv/bin/mcp-atlassian --help > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Installation successful!"
    else
        echo -e "${RED}✗${NC} Installation test failed"
        exit 1
    fi

    # Prompt for configuration
    echo ""
    echo "======================================"
    echo "Configuration Setup"
    echo "======================================"
    echo ""

    read -p "Enter your Rakuten email address: " RAKUTEN_EMAIL
    echo ""
    echo "Please generate your API tokens:"
    echo "  JIRA: https://jira.rakuten-it.com/jira → Profile → Personal Access Tokens"
    echo "  Confluence: https://confluence.rakuten-it.com/confluence → Settings → Personal Access Tokens"
    echo ""
    read -sp "Enter your JIRA Personal Access Token: " JIRA_TOKEN
    echo ""
    read -sp "Enter your Confluence Personal Access Token: " CONFLUENCE_TOKEN
    echo ""
    echo ""

    # Update .claude.json
    CLAUDE_JSON="$HOME/.claude.json"
    VENV_PATH="$MCP_DIR/.venv/bin/mcp-atlassian"

    echo -e "${YELLOW}Updating .claude.json...${NC}"

    if [ ! -f "$CLAUDE_JSON" ]; then
        echo -e "${RED}✗${NC} .claude.json not found. Please run Claude Code first."
        exit 1
    fi

    # Create temporary Python script to update JSON
    python3 << EOF
import json
import os

claude_json_path = os.path.expanduser("$CLAUDE_JSON")
with open(claude_json_path, 'r') as f:
    config = json.load(f)

# Ensure projects structure exists
if 'projects' not in config:
    config['projects'] = {}

home_dir = os.path.expanduser("~")
if home_dir not in config['projects']:
    config['projects'][home_dir] = {}

if 'mcpServers' not in config['projects'][home_dir]:
    config['projects'][home_dir]['mcpServers'] = {}

# Add or update AIPRDReviewer
config['projects'][home_dir]['mcpServers']['AIPRDReviewer'] = {
    "type": "stdio",
    "command": "$VENV_PATH",
    "args": [
        "--confluence-url", "https://confluence.rakuten-it.com/confluence",
        "--confluence-personal-token", "$CONFLUENCE_TOKEN",
        "--jira-url", "https://jira.rakuten-it.com/jira",
        "--jira-username", "$RAKUTEN_EMAIL",
        "--jira-personal-token", "$JIRA_TOKEN"
    ],
    "env": {
        "MCP_VERY_VERBOSE": "true"
    }
}

with open(claude_json_path, 'w') as f:
    json.dump(config, f, indent=2)

print("Configuration updated successfully")
EOF

    echo -e "${GREEN}✓${NC} .claude.json updated"

    # Final instructions
    echo ""
    echo "======================================"
    echo "Installation Complete!"
    echo "======================================"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code"
    echo "  2. Run: /mcp"
    echo "  3. Verify 'AIPRDReviewer' is connected"
    echo ""
    echo "Installation location: $MCP_DIR"
    echo ""
}

main
