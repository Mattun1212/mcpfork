# MCP Atlassian Auto Installer for Windows
# Requires PowerShell 5.1 or later

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "MCP Atlassian Auto Installer" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python 3.10+ is installed
function Check-Python {
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]

            if ($major -ge 3 -and $minor -ge 10) {
                Write-Host "[✓] Python $major.$minor found" -ForegroundColor Green
                return $true
            }
        }
    } catch {
        # Python not found
    }
    return $false
}

# Install Python
function Install-Python {
    Write-Host "[!] Python 3.10+ not found. Installing..." -ForegroundColor Yellow

    # Try winget first (Windows 11, or Windows 10 with App Installer)
    try {
        $null = Get-Command winget -ErrorAction Stop
        Write-Host "[!] Installing Python via winget..." -ForegroundColor Yellow
        winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        Write-Host "[✓] Python installed successfully" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "[!] winget not available, downloading Python installer..." -ForegroundColor Yellow
    }

    # Fallback: Download and install Python directly
    try {
        $pythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        $installerPath = Join-Path $env:TEMP "python-installer.exe"

        Write-Host "[!] Downloading Python 3.12.8..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath

        Write-Host "[!] Installing Python (this may take a few minutes)..." -ForegroundColor Yellow
        Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        # Clean up
        Remove-Item $installerPath -Force

        Write-Host "[✓] Python installed successfully" -ForegroundColor Green
        Write-Host "[!] Please restart PowerShell and run this script again" -ForegroundColor Yellow
        exit 0
    } catch {
        Write-Host "[✗] Automatic installation failed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python manually:" -ForegroundColor Yellow
        Write-Host "  1. Visit https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "  2. Download Python 3.11 or later" -ForegroundColor Yellow
        Write-Host "  3. Run the installer and check 'Add Python to PATH'" -ForegroundColor Yellow
        Write-Host "  4. Restart PowerShell and run this script again" -ForegroundColor Yellow
        exit 1
    }
}

# Check if Git is installed
function Check-Git {
    try {
        $null = & git --version 2>&1
        Write-Host "[✓] Git found" -ForegroundColor Green
        return $true
    } catch {
        # Git not found
    }
    return $false
}

# Install Git
function Install-Git {
    Write-Host "[!] Git not found. Installing..." -ForegroundColor Yellow

    # Try winget first
    try {
        $null = Get-Command winget -ErrorAction Stop
        Write-Host "[!] Installing Git via winget..." -ForegroundColor Yellow
        winget install Git.Git --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        Write-Host "[✓] Git installed successfully" -ForegroundColor Green
        Write-Host "[!] Please restart PowerShell and run this script again" -ForegroundColor Yellow
        exit 0
    } catch {
        Write-Host "[✗] winget not available. Please install Git manually:" -ForegroundColor Red
        Write-Host "  https://git-scm.com/download/win" -ForegroundColor Yellow
        Write-Host "  インストール後、PowerShellを再起動してスクリプトを再実行してください" -ForegroundColor Yellow
        exit 1
    }
}

# Main installation
function Main {
    # Check/Install Git (required for pip install git+https://...)
    if (-not (Check-Git)) {
        Install-Git
    }

    # Check/Install Python
    if (-not (Check-Python)) {
        Install-Python

        # Verify installation
        Start-Sleep -Seconds 2
        if (-not (Check-Python)) {
            Write-Host "[✗] Python installation failed. Please install manually." -ForegroundColor Red
            exit 1
        }
    }

    # Create MCP directory
    $mcpDir = Join-Path $HOME ".mcp\mcp-atlassian"
    Write-Host ""
    Write-Host "[!] Creating installation directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $mcpDir | Out-Null
    Set-Location $mcpDir
    Write-Host "[✓] Directory created: $mcpDir" -ForegroundColor Green

    # Create virtual environment
    Write-Host ""
    Write-Host "[!] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "[✓] Virtual environment created" -ForegroundColor Green

    # Activate virtual environment
    $activateScript = Join-Path $mcpDir ".venv\Scripts\Activate.ps1"
    & $activateScript

    # Upgrade pip
    Write-Host ""
    Write-Host "[!] Upgrading pip..." -ForegroundColor Yellow
    python -m pip install --upgrade pip | Out-Null
    Write-Host "[✓] pip upgraded" -ForegroundColor Green

    # Install MCP Atlassian
    Write-Host ""
    Write-Host "[!] Installing MCP Atlassian (this may take a few minutes)..." -ForegroundColor Yellow
    pip install --upgrade --no-cache-dir git+https://github.com/Mattun1212/mcpfork.git | Out-Null
    Write-Host "[✓] MCP Atlassian installed" -ForegroundColor Green

    # Pin pydantic to a compatible version
    # pydantic 2.12+ introduced a breaking change in FieldInfo that is incompatible with fastmcp 2.3.x
    Write-Host ""
    Write-Host "[!] Pinning pydantic to compatible version..." -ForegroundColor Yellow
    pip install "pydantic>=2.0,<2.12" | Out-Null
    Write-Host "[✓] pydantic pinned" -ForegroundColor Green

    # Test installation (verifies server can actually start, not just --help)
    Write-Host ""
    Write-Host "[!] Testing installation..." -ForegroundColor Yellow
    $mcpExe = Join-Path $mcpDir ".venv\Scripts\mcp-atlassian.exe"
    if (Test-Path $mcpExe) {
        & $mcpExe --help | Out-Null
        python -c "from mcp_atlassian.servers import main_mcp" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[✓] Installation successful!" -ForegroundColor Green
        } else {
            Write-Host "[✗] Installation test failed" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "[✗] Installation test failed" -ForegroundColor Red
        exit 1
    }

    # Prompt for configuration
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Configuration Setup" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""

    $rakutenEmail = Read-Host "Enter your Rakuten email address"
    Write-Host ""
    Write-Host "Please generate your API tokens:" -ForegroundColor Yellow
    Write-Host "  JIRA: https://jira.rakuten-it.com/jira → Profile → Personal Access Tokens" -ForegroundColor Yellow
    Write-Host "  Confluence: https://confluence.rakuten-it.com/confluence → Settings → Personal Access Tokens" -ForegroundColor Yellow
    Write-Host ""
    $jiraToken = Read-Host "Enter your JIRA Personal Access Token" -AsSecureString
    $jiraTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($jiraToken))

    $confluenceToken = Read-Host "Enter your Confluence Personal Access Token" -AsSecureString
    $confluenceTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($confluenceToken))
    Write-Host ""

    # Update .claude.json
    $claudeJsonPath = Join-Path $HOME ".claude.json"
    $venvPath = Join-Path $mcpDir ".venv\Scripts\mcp-atlassian.exe"
    # Convert to forward slashes for JSON
    $venvPathJson = $venvPath -replace '\\', '\\'

    Write-Host "[!] Updating .claude.json..." -ForegroundColor Yellow

    if (-not (Test-Path $claudeJsonPath)) {
        Write-Host "[✗] .claude.json not found. Please run Claude Code first." -ForegroundColor Red
        exit 1
    }

    # Read and update JSON
    $config = Get-Content $claudeJsonPath -Raw | ConvertFrom-Json

    # Ensure projects structure exists
    if (-not $config.projects) {
        $config | Add-Member -NotePropertyName "projects" -NotePropertyValue @{} -Force
    }

    $homeDir = $HOME
    if (-not $config.projects.$homeDir) {
        $config.projects | Add-Member -NotePropertyName $homeDir -NotePropertyValue @{} -Force
    }

    if (-not $config.projects.$homeDir.mcpServers) {
        $config.projects.$homeDir | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
    }

    # Add or update mcp-atlassian-mutton
    $mcpConfig = @{
        type = "stdio"
        command = $venvPath
        args = @(
            "--confluence-url", "https://confluence.rakuten-it.com/confluence",
            "--confluence-personal-token", $confluenceTokenPlain,
            "--jira-url", "https://jira.rakuten-it.com/jira",
            "--jira-username", $rakutenEmail,
            "--jira-personal-token", $jiraTokenPlain
        )
        env = @{
            MCP_VERY_VERBOSE = "true"
        }
    }

    $config.projects.$homeDir.mcpServers | Add-Member -NotePropertyName "mcp-atlassian-mutton" -NotePropertyValue $mcpConfig -Force

    # Save JSON
    $config | ConvertTo-Json -Depth 10 | Set-Content $claudeJsonPath -Encoding UTF8

    Write-Host "[✓] .claude.json updated" -ForegroundColor Green

    # Final instructions
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Installation Complete!" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Restart Claude Code" -ForegroundColor Yellow
    Write-Host "  2. Run: /mcp" -ForegroundColor Yellow
    Write-Host "  3. Verify 'mcp-atlassian-mutton' is connected" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Installation location: $mcpDir" -ForegroundColor Green
    Write-Host ""
}

# Run main function
Main
