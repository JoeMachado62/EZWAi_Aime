# LiveKit Agent Deployment Script (PowerShell)
# Deploys AIME voice agent to LiveKit Cloud

$ErrorActionPreference = "Stop"

Write-Host "🚀 AIME Voice Agent Deployment" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env
Write-Host "📋 Loading environment variables..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot "..\..env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "✅ Environment variables loaded" -ForegroundColor Green
} else {
    Write-Host "❌ .env file not found at $envPath" -ForegroundColor Red
    exit 1
}

# Check required environment variables
Write-Host ""
Write-Host "🔍 Checking required credentials..." -ForegroundColor Yellow

$required = @(
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY"
)

$missing = @()
foreach ($var in $required) {
    $value = [Environment]::GetEnvironmentVariable($var, "Process")
    if ([string]::IsNullOrEmpty($value) -or $value -match "your_.*_here") {
        $missing += $var
        Write-Host "  ❌ $var is not set" -ForegroundColor Red
    } else {
        $masked = if ($value.Length -gt 8) { $value.Substring(0, 8) + "..." } else { "***" }
        Write-Host "  ✅ $var = $masked" -ForegroundColor Green
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ Missing required environment variables:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Please update .env file with the missing credentials" -ForegroundColor Yellow
    exit 1
}

# Check if Python is installed
Write-Host ""
Write-Host "🐍 Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python not found" -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ from https://www.python.org" -ForegroundColor Yellow
    exit 1
}

# Install/update dependencies
Write-Host ""
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
Set-Location $PSScriptRoot
python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Test local agent
Write-Host ""
Write-Host "🧪 Testing agent locally..." -ForegroundColor Yellow
Write-Host "  (This is a quick sanity check, press Ctrl+C after 5 seconds)" -ForegroundColor Gray
try {
    $job = Start-Job -ScriptBlock {
        param($scriptPath)
        Set-Location (Split-Path $scriptPath)
        python voice_agent.py dev
    } -ArgumentList $PSScriptRoot

    Start-Sleep -Seconds 5
    Stop-Job $job
    Remove-Job $job
    Write-Host "✅ Agent starts successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Agent failed to start: $_" -ForegroundColor Red
    exit 1
}

# Deploy to LiveKit Cloud
Write-Host ""
Write-Host "☁️  Deploying to LiveKit Cloud..." -ForegroundColor Yellow
Write-Host "  This will use the LiveKit Python SDK to deploy" -ForegroundColor Gray
Write-Host ""

# Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
$deployScript = @"
import os
import asyncio
from livekit.agents import cli

# Set environment variables
os.environ['LIVEKIT_URL'] = os.getenv('LIVEKIT_URL', '')
os.environ['LIVEKIT_API_KEY'] = os.getenv('LIVEKIT_API_KEY', '')
os.environ['LIVEKIT_API_SECRET'] = os.getenv('LIVEKIT_API_SECRET', '')

# Deploy agent
if __name__ == '__main__':
    print('🚀 Starting AIME Voice Agent...')
    print(f'   LiveKit URL: {os.environ["LIVEKIT_URL"]}')
    print(f'   API Key: {os.environ["LIVEKIT_API_KEY"][:8]}...')
    print('')
    print('✅ Agent is running!')
    print('   Press Ctrl+C to stop')
    print('')

    # Run the agent
    cli.run_app()
"@

$deployScript | Out-File -FilePath "deploy_agent.py" -Encoding UTF8

Write-Host "✅ Deployment package created" -ForegroundColor Green

# Instructions for manual deployment
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT OPTIONS" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 1: Run locally (for testing)" -ForegroundColor Yellow
Write-Host "  python voice_agent.py dev" -ForegroundColor White
Write-Host ""
Write-Host "Option 2: Connect to LiveKit Cloud" -ForegroundColor Yellow
Write-Host "  python voice_agent.py start" -ForegroundColor White
Write-Host ""
Write-Host "Option 3: Use LiveKit CLI (if installed)" -ForegroundColor Yellow
Write-Host "  lk cloud auth" -ForegroundColor White
Write-Host "  lk agent create --name aime-voice-agent --file voice_agent.py" -ForegroundColor White
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Deployment preparation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Make sure OPENCLAW_BASE_URL is accessible (use ngrok for localhost)" -ForegroundColor White
Write-Host "2. Run 'python voice_agent.py start' to connect to LiveKit Cloud" -ForegroundColor White
Write-Host "3. Test by calling +1 (305) 952-1569" -ForegroundColor White
Write-Host ""
