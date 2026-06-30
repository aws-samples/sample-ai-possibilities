<#
.SYNOPSIS
    Deploy all 5 AI Team (Memory) agents using the AgentCore CLI (@aws/agentcore)
.DESCRIPTION
    Creates a single CDK project with all 5 agents as runtimes, then deploys
    them all in one CDK stack. Includes memory resource creation and permission setup.

    Prerequisites:
      npm install -g @aws/agentcore
      cdk bootstrap aws://ACCOUNT_ID/REGION  (one-time per account/region)
      aws configure (or set AWS_PROFILE)

    IMPORTANT: Clone/run from a short path (NOT OneDrive). Example: C:\dev\

.EXAMPLE
    .\deploy-all.ps1
    .\deploy-all.ps1 -AgentName ai-gk
#>

param(
    [string]$AgentName
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildDir = Join-Path $ScriptDir "_build_newcli"

if (-not $env:AWS_DEFAULT_REGION) {
    $env:AWS_DEFAULT_REGION = "us-east-1"
}

$allAgents = @("ai-gk", "ai-def", "ai-mid", "ai-fwd1", "ai-fwd2")
if ($AgentName) {
    if ($allAgents -notcontains $AgentName) {
        Write-Host "ERROR: Unknown agent '$AgentName'. Valid: $($allAgents -join ', ')" -ForegroundColor Red
        exit 1
    }
    $allAgents = @($AgentName)
}

Write-Host ""
Write-Host "=========================================="
Write-Host "  AI Team (Memory) - Deploy All Agents (New CLI)"
Write-Host "=========================================="
Write-Host ""

# ============================================================
# Pre-flight checks
# ============================================================
Write-Host "Checking prerequisites..."

$agentcorePath = (Get-Command agentcore -ErrorAction SilentlyContinue | Where-Object { $_.Source -match "npm|Roaming" } | Select-Object -First 1).Source
if (-not $agentcorePath) {
    $agentcorePath = "C:\Users\$env:USERNAME\AppData\Roaming\npm\agentcore.cmd"
    if (-not (Test-Path $agentcorePath)) {
        Write-Host "  ERROR: AgentCore CLI not found. Install: npm install -g @aws/agentcore" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  agentcore CLI: OK" -ForegroundColor Green

# Check tsc (TypeScript compiler - required by agentcore deploy for CDK build)
$tscCmd = Get-Command tsc -ErrorAction SilentlyContinue
if (-not $tscCmd) {
    Write-Host "  tsc: Not found. Installing TypeScript globally..." -ForegroundColor Yellow
    npm install -g typescript 2>&1 | Out-Null
    $tscCmd = Get-Command tsc -ErrorAction SilentlyContinue
    if (-not $tscCmd) {
        Write-Host "  ERROR: Could not install TypeScript. Run: npm install -g typescript" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  tsc: OK" -ForegroundColor Green

try { $null = Get-Command aws -ErrorAction Stop; Write-Host "  aws CLI: OK" -ForegroundColor Green }
catch { Write-Host "  ERROR: 'aws' CLI not found." -ForegroundColor Red; exit 1 }

$awsAccountId = (aws sts get-caller-identity --query Account --output text 2>$null).Trim()
if (-not $awsAccountId) { Write-Host "  ERROR: No valid AWS credentials." -ForegroundColor Red; exit 1 }
Write-Host "  AWS Account: $awsAccountId" -ForegroundColor Green
Write-Host "  AWS Region:  $($env:AWS_DEFAULT_REGION)" -ForegroundColor Green

# Check CDK bootstrap
$ErrorActionPreference = "Continue"
$bootstrapVersion = aws ssm get-parameter --name "/cdk-bootstrap/hnb659fds/version" --query "Parameter.Value" --output text 2>$null
if ($LASTEXITCODE -ne 0 -or -not $bootstrapVersion) {
    Write-Host "  CDK bootstrap: Running..." -ForegroundColor Yellow
    $ErrorActionPreference = "Stop"
    cdk bootstrap "aws://$awsAccountId/$($env:AWS_DEFAULT_REGION)"
}
$ErrorActionPreference = "Stop"
Write-Host "  CDK bootstrap: OK" -ForegroundColor Green

if ($ScriptDir -match "OneDrive") {
    Write-Host ""
    Write-Host "  WARNING: OneDrive detected! This may fail due to long paths." -ForegroundColor Yellow
    Write-Host "  Clone to C:\dev\ or similar short path instead." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================
# Memory Resource Setup
# ============================================================
if ($env:MEMORY_ID) {
    $MEMORY_ID = $env:MEMORY_ID
    Write-Host "Using pre-set MEMORY_ID: $MEMORY_ID"
} else {
    Write-Host "Creating memory resource..."
    try {
        $createOutput = python "$ScriptDir\create_memory.py" 2>&1 | Out-String
        Write-Host "  create_memory.py output:"
        Write-Host "  $createOutput"

        # Parse MEMORY_ID from output (format: "Memory resource ready: <id>")
        if ($createOutput -match "Memory resource ready:\s*(\S+)") {
            $MEMORY_ID = $Matches[1]
        } elseif ($createOutput -match "export MEMORY_ID=(\S+)") {
            $MEMORY_ID = $Matches[1]
        }

        if (-not $MEMORY_ID) {
            Write-Host "  ERROR: Could not parse MEMORY_ID from output." -ForegroundColor Red
            exit 1
        }

        $env:MEMORY_ID = $MEMORY_ID
        Write-Host "  Created MEMORY_ID: $MEMORY_ID" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: create_memory.py failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# ============================================================
# Create project structure with all 5 agents
# ============================================================
Write-Host "Setting up deployment project..."

if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

# Use agentcore create to scaffold the CDK project
$projectName = "aiteammemory"
Push-Location (Split-Path $BuildDir -Parent)
$buildDirName = Split-Path $BuildDir -Leaf
$ErrorActionPreference = "Continue"
& $agentcorePath create --name "ai_gk_agent" --project-name $projectName --defaults --build CodeZip --skip-git --skip-python-setup --output-dir $buildDirName 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
Pop-Location

# agentcore create puts project in a subdirectory named after project-name
$projectDir = Join-Path $BuildDir $projectName
if (Test-Path $projectDir) {
    Get-ChildItem $projectDir | Move-Item -Destination $BuildDir -Force
    Remove-Item $projectDir -Force
}

# Wait for npm install to finish (agentcore create runs it)
$cdkDir = Join-Path $BuildDir "agentcore\cdk"
if (-not (Test-Path "$cdkDir\node_modules")) {
    Write-Host "  Installing CDK dependencies..."
    Push-Location $cdkDir
    npm install 2>&1 | Out-Null
    Pop-Location
}

Write-Host "  CDK project ready"

# Copy agent source code into the project
foreach ($agent in $allAgents) {
    $agentNameClean = ($agent -replace '-', '_') + "_agent"
    $appDir = Join-Path $BuildDir "app\$agentNameClean"
    New-Item -ItemType Directory -Path $appDir -Force | Out-Null

    # Copy main.py
    Copy-Item "$ScriptDir\$agent\src\main.py" "$appDir\main.py"

    # Copy shared lib
    $libSource = Join-Path $ScriptDir "..\lib"
    if (Test-Path $libSource) {
        $libDest = Join-Path $appDir "lib"
        New-Item -ItemType Directory -Path $libDest -Force | Out-Null
        robocopy $libSource $libDest /E /XD __pycache__ /NJH /NJS /NFL /NDL /NC /NS | Out-Null
    }

    # Copy memory_agent_base.py into each app/<agent>/ directory
    Copy-Item "$ScriptDir\memory_agent_base.py" "$appDir\memory_agent_base.py"

    # Create pyproject.toml
    $pyprojectContent = @"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "$agentNameClean"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "aws-opentelemetry-distro",
    "bedrock-agentcore >= 1.9.1",
    "strands-agents >= 1.15.0",
]

[tool.hatch.build.targets.wheel]
packages = ["."]
"@
    [IO.File]::WriteAllText("$appDir\pyproject.toml", $pyprojectContent, [System.Text.UTF8Encoding]::new($false))

    Write-Host "  Prepared: $agent -> $agentNameClean"
}

# Generate agentcore.json with all 5 runtimes (including environmentVariables)
$runtimes = $allAgents | ForEach-Object {
    $name = ($_ -replace '-', '_') + "_agent"
    @"
    {
      "name": "$name",
      "build": "CodeZip",
      "entrypoint": "main.py",
      "codeLocation": "app/$name/",
      "runtimeVersion": "PYTHON_3_12",
      "networkMode": "PUBLIC",
      "protocol": "HTTP",
      "environmentVariables": {
        "MEMORY_ID": "$MEMORY_ID",
        "AWS_DEFAULT_REGION": "$($env:AWS_DEFAULT_REGION)"
      }
    }
"@
}

$agentcoreJson = @"
{
  "`$schema": "https://schema.agentcore.aws.dev/v1/agentcore.json",
  "name": "aiteammemory",
  "version": 1,
  "managedBy": "CDK",
  "runtimes": [
$($runtimes -join ",`n")
  ],
  "memories": [],
  "knowledgeBases": [],
  "credentials": [],
  "evaluators": [],
  "onlineEvalConfigs": [],
  "agentCoreGateways": [],
  "policyEngines": [],
  "configBundles": [],
  "abTests": [],
  "harnesses": [],
  "datasets": [],
  "payments": []
}
"@
[IO.File]::WriteAllText("$BuildDir\agentcore\agentcore.json", $agentcoreJson, [System.Text.UTF8Encoding]::new($false))
Write-Host "  Generated agentcore.json with $($allAgents.Count) runtimes"

# ============================================================
# Deploy all agents in one CDK stack
# ============================================================
Write-Host ""
Write-Host "=========================================="
Write-Host "  Deploying all agents via CDK..."
Write-Host "=========================================="
Write-Host ""

Push-Location $BuildDir
$ErrorActionPreference = "Continue"
& $agentcorePath deploy --yes --verbose 2>&1 | ForEach-Object {
    $line = "$_".Trim()
    if ($line -and $line -notmatch '^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s') {
        Write-Host "  $line"
    }
}
$deployExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Pop-Location

# ============================================================
# Attach memory permissions to execution roles
# ============================================================
Write-Host ""
Write-Host "Attaching AgentCore Memory permissions to execution roles..."

$ErrorActionPreference = "Continue"
$execRoles = (aws iam list-roles --query "Roles[?starts_with(RoleName, 'AmazonBedrockAgentCoreSDKRuntime-$($env:AWS_DEFAULT_REGION)-')].RoleName" --output text 2>$null)
$ErrorActionPreference = "Stop"

if ($execRoles -and $execRoles.Trim()) {
    foreach ($execRoleName in ($execRoles.Trim() -split '\s+')) {
        $policyDoc = @"
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "bedrock-agentcore:ListEvents",
            "bedrock-agentcore:CreateEvent",
            "bedrock-agentcore:GetEvent",
            "bedrock-agentcore:DeleteEvent",
            "bedrock-agentcore:RetrieveMemoryRecords",
            "bedrock-agentcore:GetMemoryRecord",
            "bedrock-agentcore:ListMemoryRecords"
        ],
        "Resource": "arn:aws:bedrock-agentcore:$($env:AWS_DEFAULT_REGION):${awsAccountId}:memory/*"
    }]
}
"@
        $tempPolicyFile = [System.IO.Path]::GetTempFileName()
        [IO.File]::WriteAllText($tempPolicyFile, $policyDoc, [System.Text.UTF8Encoding]::new($false))

        $ErrorActionPreference = "Continue"
        aws iam put-role-policy --role-name $execRoleName --policy-name AgentCoreMemoryAccess --policy-document "file://$tempPolicyFile" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  `u{2705} Memory permissions attached to: $execRoleName" -ForegroundColor Green
        } else {
            Write-Host "  `u{26A0}`u{FE0F}  Failed to attach memory permissions to: $execRoleName" -ForegroundColor Yellow
        }
        $ErrorActionPreference = "Stop"

        Remove-Item $tempPolicyFile -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  `u{26A0}`u{FE0F}  Could not find execution roles - attach AgentCoreMemoryAccess policy manually" -ForegroundColor Yellow
}

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host "=========================================="
Write-Host "  Deployment Summary"
Write-Host "=========================================="
Write-Host ""

if ($deployExitCode -eq 0) {
    Write-Host "  All $($allAgents.Count) agents deployed successfully!" -ForegroundColor Green
    Write-Host "  Agents: $($allAgents -join ', ')" -ForegroundColor Green
} else {
    Write-Host "  Deployment FAILED (exit code: $deployExitCode)" -ForegroundColor Red
    Write-Host "  Check the output above for details." -ForegroundColor Red
}

Write-Host "  Account:  $awsAccountId"
Write-Host "  Region:   $($env:AWS_DEFAULT_REGION)"
Write-Host "  Memory:   $MEMORY_ID"
Write-Host ""

# Cleanup
Write-Host "Cleaning up build directory..."
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue }

if ($deployExitCode -ne 0) { exit 1 }
