# MCP Atlassian Auto Installer for Windows
# Requires PowerShell 5.1 or later

$ErrorActionPreference = "Stop"

Write-Host "======================================"
Write-Host "MCP Atlassian Installer"
Write-Host "======================================"
Write-Host ""

function Check-Uv {
    try {
        $uvVersion = & uv --version 2>&1
        Write-Host "[OK] uv found: $uvVersion"
        return $true
    } catch {
        return $false
    }
}

function Check-Git {
    try {
        $gitVersion = & git --version 2>&1
        Write-Host "[OK] git found: $gitVersion"
        return $true
    } catch {
        return $false
    }
}

function Install-Git {
    Write-Host "[..] Installing git via winget..."
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    if (-not (Check-Git)) {
        throw "git installation failed. Please install manually from https://git-scm.com/ and re-run this script."
    }
}

function Install-Uv {
    Write-Host "[..] Installing uv..."
    Invoke-Expression (Invoke-RestMethod "https://astral.sh/uv/install.ps1")

    # Refresh PATH
    $env:Path = "$env:USERPROFILE\.local\bin;" + [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    if (-not (Check-Uv)) {
        throw "uv installation failed. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
    }
}

function Main {
    # Set up logging
    $logFile = Join-Path $HOME ".mcp\mcp-atlassian-mutton-install.log"
    New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
    Start-Transcript -Path $logFile -Append | Out-Null
    Write-Host "====== Install started: $(Get-Date) ======"

    # Check/Install uv
    if (-not (Check-Uv)) {
        Install-Uv
    }

    # Check/Install git (required for uvx --from git+https://...)
    if (-not (Check-Git)) {
        Install-Git
    }

    # Resolve uvx full path (avoid PATH lookup issues when Claude Code starts)
    $uvxPath = (Get-Command uvx).Source
    Write-Host "[OK] uvx path: $uvxPath"

    # Prompt for tokens
    Write-Host ""
    Write-Host "======================================"
    Write-Host "Configuration Setup"
    Write-Host "======================================"
    Write-Host ""
    Write-Host "Please generate your API tokens:"
    Write-Host "  JIRA: https://jira.rakuten-it.com/jira > Profile > Personal Access Tokens"
    Write-Host "  Confluence: https://confluence.rakuten-it.com/confluence > Settings > Personal Access Tokens"
    Write-Host ""

    $jiraToken = Read-Host "Enter your JIRA Personal Access Token" -AsSecureString
    $jiraTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($jiraToken))

    $confluenceToken = Read-Host "Enter your Confluence Personal Access Token" -AsSecureString
    $confluenceTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($confluenceToken))
    Write-Host ""

    # Update .claude.json
    $claudeJsonPath = Join-Path $HOME ".claude.json"
    Write-Host "[..] Updating .claude.json..."

    if (-not (Test-Path $claudeJsonPath)) {
        throw ".claude.json not found. Please run Claude Code first, then re-run this script."
    }

    # Read and update JSON
    $config = Get-Content $claudeJsonPath -Raw | ConvertFrom-Json

    # Add to top-level mcpServers (global, applies regardless of working directory)
    if (-not $config.mcpServers) {
        $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{}) -Force
    }

    $mcpConfig = [PSCustomObject]@{
        type    = "stdio"
        command = $uvxPath
        args    = @(
            "--from", "git+https://github.com/Mattun1212/mcpfork.git",
            "mcp-atlassian"
        )
        env     = [PSCustomObject]@{
            CONFLUENCE_URL            = "https://confluence.rakuten-it.com/confluence"
            CONFLUENCE_PERSONAL_TOKEN = $confluenceTokenPlain
            JIRA_URL                  = "https://jira.rakuten-it.com/jira"
            JIRA_PERSONAL_TOKEN       = $jiraTokenPlain
        }
    }

    $config.mcpServers | Add-Member -NotePropertyName "mcp-atlassian-mutton" -NotePropertyValue $mcpConfig -Force

    # Save UTF-8 without BOM (PS5.x Set-Content adds BOM which breaks Node.js JSON.parse)
    $jsonContent = $config | ConvertTo-Json -Depth 10
    $utf8NoBOM = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($claudeJsonPath, $jsonContent, $utf8NoBOM)

    Write-Host "[OK] .claude.json updated"

    # Final instructions
    Write-Host ""
    Write-Host "======================================"
    Write-Host "Installation Complete!"
    Write-Host "======================================"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart Claude Code"
    Write-Host "  2. Run: /mcp"
    Write-Host "  3. Verify 'mcp-atlassian-mutton' is connected"
    Write-Host ""
    Write-Host "Log file: $logFile"
    Write-Host ""
    Stop-Transcript | Out-Null
}

$script:logFile = Join-Path $HOME ".mcp\mcp-atlassian-mutton-install.log"
try {
    Main
} catch {
    Write-Host ""
    Write-Host "[FAIL] $_"
    Write-Host "Log file: $($script:logFile)"
    exit 1
}
