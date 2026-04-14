# MCP Atlassian - Fork with Inline Comment Support

> **Note**: This is a fork of [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) with additional Confluence inline comment features. If you're looking for the original project, please visit the upstream repository.

## What is this?

This fork extends the original MCP Atlassian integration with **Confluence inline comment functionality**, enabling AI-powered document review workflows. The primary use case is **AI PRD Reviewer** - an automated system for reviewing Product Requirement Documents (PRDs) on Confluence.

### Key Differences from Original

| Feature | Original | This Fork |
|---------|----------|-----------|
| Confluence pages | ✅ Read/Write | ✅ Read/Write |
| Confluence comments | ✅ Page-level | ✅ **Inline comments** |
| Jira issues | ✅ Full support | ✅ Full support |
| Use case | General AI assistant | **PRD Review workflows** |

### Added Features

#### Confluence Inline Comments (CRUD)

- **Create inline comments** - Add review comments to specific text ranges
- **Read inline comments** - Retrieve all inline comments from a page
- **Update inline comments** - Modify existing comment content
- **Delete inline comments** - Remove comments after review

These features enable AI assistants to:
- Review documents section-by-section
- Add contextual feedback inline
- Track review progress through comments
- Clean up comments after addressing feedback

## Installation

### Quick Install (uvx)

No virtual environment or Python management needed — [uv](https://docs.astral.sh/uv/) handles everything.

**1. Install uv** (if not already installed):

```bash
# Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Add to Claude Code** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "mcp-atlassian-mutton": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Mattun1212/mcpfork.git", "mcp-atlassian"],
      "env": {
        "CONFLUENCE_URL": "https://confluence.rakuten-it.com/confluence",
        "CONFLUENCE_PERSONAL_TOKEN": "YOUR_CONFLUENCE_PAT",
        "JIRA_URL": "https://jira.rakuten-it.com/jira",
        "JIRA_PERSONAL_TOKEN": "YOUR_JIRA_PAT"
      }
    }
  }
}
```

### Automated Installer

For complete setup including uv installation and Claude Code configuration, use the automated installer:

1. Download installer:
   - Mac/Linux: `install-mcp-atlassian-mutton.sh`
   - Windows: `install-mcp-atlassian-mutton.ps1`

2. Run installer:
   ```bash
   # Mac/Linux
   chmod +x install-mcp-atlassian-mutton.sh
   ./install-mcp-atlassian-mutton.sh

   # Windows
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\install-mcp-atlassian-mutton.ps1
   ```

The installer will:
- Install uv if needed
- Prompt for API tokens
- Configure Claude Code `~/.claude.json`

## Configuration

### For Claude Code

Add to your `~/.claude.json`. Configuration is passed via environment variables:

**Server/Data Center (PAT — token only, no username required):**
```json
{
  "mcpServers": {
    "mcp-atlassian-mutton": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Mattun1212/mcpfork.git", "mcp-atlassian"],
      "env": {
        "CONFLUENCE_URL": "https://confluence.your-company.com",
        "CONFLUENCE_PERSONAL_TOKEN": "YOUR_CONFLUENCE_PAT",
        "JIRA_URL": "https://jira.your-company.com",
        "JIRA_PERSONAL_TOKEN": "YOUR_JIRA_PAT"
      }
    }
  }
}
```

**Cloud (username + API token required):**
```json
{
  "mcpServers": {
    "mcp-atlassian-mutton": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Mattun1212/mcpfork.git", "mcp-atlassian"],
      "env": {
        "CONFLUENCE_URL": "https://your-domain.atlassian.net/wiki",
        "CONFLUENCE_USERNAME": "your-email@example.com",
        "CONFLUENCE_API_TOKEN": "YOUR_CONFLUENCE_API_TOKEN",
        "JIRA_URL": "https://your-domain.atlassian.net",
        "JIRA_USERNAME": "your-email@example.com",
        "JIRA_API_TOKEN": "YOUR_JIRA_API_TOKEN"
      }
    }
  }
}
```

### Authentication

| Deployment | Method | Required env vars |
|-----------|--------|----------|
| **Cloud** | Username + API Token | `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN`, `JIRA_USERNAME`, `JIRA_API_TOKEN` |
| **Server/Data Center** | Personal Access Token | `CONFLUENCE_PERSONAL_TOKEN`, `JIRA_PERSONAL_TOKEN` (username not needed) |

- **Cloud API tokens**: https://id.atlassian.com/manage-profile/security/api-tokens
- **Server/DC PAT**: Profile → Personal Access Tokens in your instance

## Usage

### Basic Examples

**Confluence:**
```
"Search Confluence for 'API documentation' and summarize"
"Create a new page in TEAM space about feature X"
"Add an inline comment to paragraph 3 of page 123456"
"Get all inline comments from page 789012"
```

**Jira:**
```
"Show me all bugs in PROJECT from last week"
"Create a new task in PROJ: Implement feature Y"
"Update PROJ-123 status to In Progress"
```

### PRD Review Workflow

This fork is optimized for automated PRD review:

1. AI reads the PRD page
2. AI analyzes content (grammar, logic, requirements, etc.)
3. AI adds inline comments with feedback
4. Human reviews comments and makes changes
5. AI or human deletes resolved comments

## Available Tools

### Confluence

**Pages:**
- `confluence_search` - Search pages
- `confluence_get_page` - Get page content
- `confluence_create_page` - Create new page
- `confluence_update_page` - Update existing page
- `confluence_delete_page` - Delete page

**Comments:**
- `confluence_get_comments` - Get page-level comments
- `confluence_add_comment` - Add page-level comment
- `confluence_get_inline_comments` - **Get inline comments** ⭐
- `confluence_add_inline_comment` - **Add inline comment** ⭐
- `confluence_update_inline_comment` - **Update inline comment** ⭐
- `confluence_delete_inline_comment` - **Delete inline comment** ⭐

**Attachments:**
- `confluence_download_attachments` - Download page attachments

### Jira

- `jira_search` - Search issues with JQL
- `jira_get_issue` - Get issue details
- `jira_create_issue` - Create new issue
- `jira_update_issue` - Update issue
- `jira_add_comment` - Add comment
- `jira_get_transitions` - Get available transitions
- `jira_transition_issue` - Change issue status
- And more... (see original project for full list)

## Compatibility

| Product | Deployment | Inline Comments |
|---------|-----------|-----------------|
| Confluence Cloud | ✅ | ✅ |
| Confluence Server/Data Center | ✅ | ✅ |
| Jira Cloud | ✅ | N/A |
| Jira Server/Data Center | ✅ | N/A |

Tested on:
- Confluence Server/Data Center 6.0+
- Jira Server/Data Center 8.14+

## Development

This is a fork maintained for specific use cases. For general MCP Atlassian development, please contribute to the upstream project.

### Local Setup

```bash
# Clone this repository
git clone https://github.com/Mattun1212/mcpfork.git
cd mcpfork

# Install dependencies
pip install -e .

# Run
mcp-atlassian --help
```

### Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Troubleshooting

### Connection Issues

**Symptoms:** "Failed to connect" errors

**Solutions:**
1. Verify URLs (include `/wiki` for Confluence, `/jira` for Jira)
2. Check token validity
3. Ensure network access to your Atlassian instance

### Inline Comment Issues

**Symptoms:** Inline comments not appearing

**Solutions:**
1. Verify you have edit permissions on the page
2. Check that the text selection exists on the page
3. Use `confluence_get_inline_comments` to verify comment was created

### Server/Data Center SSL Issues

If using self-signed certificates, add SSL verification flags to the `env` block:

```json
"env": {
  "CONFLUENCE_URL": "https://your-server/confluence",
  "CONFLUENCE_PERSONAL_TOKEN": "YOUR_CONFLUENCE_PAT",
  "CONFLUENCE_SSL_VERIFY": "false",
  "JIRA_URL": "https://your-server/jira",
  "JIRA_PERSONAL_TOKEN": "YOUR_JIRA_PAT",
  "JIRA_SSL_VERIFY": "false"
}
```

## License & Attribution

**License:** MIT License - see [LICENSE](LICENSE) file

**Original Project:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)
- Licensed under MIT
- Copyright (c) 2024 Hyeonsoo Lee

**This Fork:**
- Additional inline comment features
- Copyright (c) 2025 Koutaro Matsushita
- Also licensed under MIT

This is not an official Atlassian product.

## Acknowledgments

This project is built on the excellent work of the [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) team. We've added inline comment functionality to support specific document review workflows while maintaining compatibility with the original project.

For the latest features and general use cases, please refer to the [upstream project](https://github.com/sooperset/mcp-atlassian).
