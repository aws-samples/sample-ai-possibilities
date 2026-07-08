<#
.SYNOPSIS
    Deploy all 5 AI Team (Gateway) agents using the AgentCore CLI (@aws/agentcore)
.DESCRIPTION
    Sets up Lambda functions and MCP Gateway, then creates a single CDK project
    with all 5 agents as runtimes and deploys them all in one CDK stack.

    Prerequisites:
      npm install -g @aws/agentcore
      cdk bootstrap aws://ACCOUNT_ID/REGION  (one-time per account/region)
      aws configure (or set AWS_PROFILE)

    IMPORTANT: Clone/run from a short path (NOT OneDrive). Example: C:\dev\

    Override auto-setup by pre-setting GATEWAY_URL.

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

$GATEWAY_NAME = "afwc-tactical-tools"
$LAMBDA_PREFIX = "afwc-gateway-tool"
$LAMBDA_ROLE_NAME = "afwc-gateway-tool-lambda-role"
$GW_ROLE_NAME = "AfwcGatewayExecutionRole"

$allAgents = @("ai-gk", "ai-def", "ai-mid", "ai-fwd1", "ai-fwd2")
if ($AgentName) {
    if ($allAgents -notcontains $AgentName) {
        Write-Host "ERROR: Unknown agent '$AgentName'. Valid: $($allAgents -join ', ')" -ForegroundColor Red
        exit 1
    }
    $allAgents = @($AgentName)
}
$TOOLS = @("calculate_pass_options", "evaluate_shot", "find_open_space", "get_defensive_assignment")

Write-Host ""
Write-Host "=========================================="
Write-Host "  AI Team (Gateway) - Deploy All Agents (New CLI)"
Write-Host "=========================================="
Write-Host ""

# ============================================================
# Pre-flight checks
# ============================================================
Write-Host "Checking prerequisites..."

$npmPrefix = npm config get prefix
$agentcorePath = Join-Path $npmPrefix "agentcore.cmd"
if (-not (Test-Path $agentcorePath)) {
    Write-Host "  ERROR: AgentCore CLI not found. Install: npm install -g @aws/agentcore" -ForegroundColor Red
    exit 1
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
$env:AWS_ACCOUNT_ID = $awsAccountId
Write-Host "  AWS Account: $awsAccountId" -ForegroundColor Green
Write-Host "  AWS Region:  $($env:AWS_DEFAULT_REGION)" -ForegroundColor Green

# Check CDK bootstrap — CDKToolkit stack must be pre-provisioned by Workshop Studio
$ErrorActionPreference = "Continue"
$cdkToolkitStatus = aws cloudformation describe-stacks --stack-name CDKToolkit --query "Stacks[0].StackStatus" --output text 2>$null
if ($LASTEXITCODE -ne 0 -or -not $cdkToolkitStatus -or $cdkToolkitStatus -notin @("CREATE_COMPLETE","UPDATE_COMPLETE")) {
    Write-Host "  CDK bootstrap: Not found or not ready (status: $cdkToolkitStatus)" -ForegroundColor Yellow
    Write-Host "  Attempting cdk bootstrap..." -ForegroundColor Yellow
    # Clean up broken stack if exists
    if ($cdkToolkitStatus -and $cdkToolkitStatus -notin @("CREATE_COMPLETE","UPDATE_COMPLETE")) {
        aws cloudformation delete-stack --stack-name CDKToolkit --region $env:AWS_DEFAULT_REGION 2>$null
        aws cloudformation wait stack-delete-complete --stack-name CDKToolkit --region $env:AWS_DEFAULT_REGION 2>$null
    }
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

# ======================================================================
# GATEWAY SETUP (skipped if GATEWAY_URL is pre-set)
# ======================================================================

if ($env:GATEWAY_URL) {
    $GATEWAY_URL = $env:GATEWAY_URL
    Write-Host "Using pre-set GATEWAY_URL: $GATEWAY_URL"
    Write-Host ""
} else {

    # ---- Step 1: Lambda IAM Role ----
    Write-Host "=========================================="
    Write-Host "  Step 1: Lambda IAM Role"
    Write-Host "=========================================="

    $ErrorActionPreference = "Continue"
    $LAMBDA_ROLE_ARN = (aws iam get-role --role-name $LAMBDA_ROLE_NAME --query "Role.Arn" --output text 2>$null)
    $roleExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = "Stop"

    if (-not $roleExists) {
        Write-Host "  Creating Lambda execution role..."
        $trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        $LAMBDA_ROLE_ARN = (aws iam create-role `
            --role-name $LAMBDA_ROLE_NAME `
            --assume-role-policy-document $trustPolicy `
            --query "Role.Arn" --output text)
        aws iam attach-role-policy `
            --role-name $LAMBDA_ROLE_NAME `
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        Write-Host "  Waiting 10s for role propagation..."
        Start-Sleep -Seconds 10
    }
    Write-Host "  Role ARN: $LAMBDA_ROLE_ARN"
    Write-Host ""

    # ---- Step 2: Deploy Lambda Functions ----
    Write-Host "=========================================="
    Write-Host "  Step 2: Deploy Lambda Functions"
    Write-Host "=========================================="

    foreach ($tool in $TOOLS) {
        $funcName = "$LAMBDA_PREFIX-$($tool -replace '_', '-')"
        $toolFile = Join-Path $ScriptDir "gateway_tools\$tool.py"

        $ErrorActionPreference = "Continue"
        $null = aws lambda get-function --function-name $funcName --region $env:AWS_DEFAULT_REGION 2>$null
        $funcExists = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = "Stop"

        # Create temp directory for Lambda packaging
        $tmpDir = Join-Path $env:TEMP "lambda_$funcName_$(Get-Random)"
        New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

        # Copy tool file and rename handler
        $lambdaContent = Get-Content $toolFile -Raw
        $lambdaContent = $lambdaContent -replace '(?m)^def handler\(', 'def lambda_handler('
        [IO.File]::WriteAllText("$tmpDir\lambda_function.py", $lambdaContent, [System.Text.UTF8Encoding]::new($false))

        # Create zip using Compress-Archive
        $zipPath = "$tmpDir\function.zip"
        Compress-Archive -Path "$tmpDir\lambda_function.py" -DestinationPath $zipPath -Force

        if (-not $funcExists) {
            Write-Host "  Creating: $funcName"
            aws lambda create-function `
                --function-name $funcName `
                --runtime python3.12 `
                --handler lambda_function.lambda_handler `
                --role $LAMBDA_ROLE_ARN `
                --zip-file "fileb://$zipPath" `
                --timeout 10 --memory-size 128 `
                --region $env:AWS_DEFAULT_REGION | Out-Null
        } else {
            Write-Host "  Updating: $funcName"
            aws lambda update-function-code `
                --function-name $funcName `
                --zip-file "fileb://$zipPath" `
                --region $env:AWS_DEFAULT_REGION | Out-Null
        }

        Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
    }
    Write-Host ""

    # ---- Step 3: Gateway Execution Role ----
    Write-Host "=========================================="
    Write-Host "  Step 3: Gateway Execution Role"
    Write-Host "=========================================="

    $ErrorActionPreference = "Continue"
    $GW_ROLE_ARN = (aws iam get-role --role-name $GW_ROLE_NAME --query "Role.Arn" --output text 2>$null)
    $gwRoleExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = "Stop"

    if (-not $gwRoleExists) {
        Write-Host "  Creating gateway execution role..."
        $gwTrust = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"bedrock-agentcore.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        $GW_ROLE_ARN = (aws iam create-role `
            --role-name $GW_ROLE_NAME `
            --assume-role-policy-document $gwTrust `
            --query "Role.Arn" --output text)

        # Allow gateway to invoke Lambda targets
        $lambdaPolicyDoc = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"lambda:InvokeFunction","Resource":"arn:aws:lambda:*:*:function:afwc-gateway-tool-*"}]}'
        $tempLambdaPolicy = [System.IO.Path]::GetTempFileName()
        [IO.File]::WriteAllText($tempLambdaPolicy, $lambdaPolicyDoc, [System.Text.UTF8Encoding]::new($false))
        aws iam put-role-policy `
            --role-name $GW_ROLE_NAME `
            --policy-name "InvokeLambdaTargets" `
            --policy-document "file://$tempLambdaPolicy"
        Remove-Item $tempLambdaPolicy -ErrorAction SilentlyContinue

        Write-Host "  Waiting 10s for role propagation..."
        Start-Sleep -Seconds 10
    }
    Write-Host "  Role ARN: $GW_ROLE_ARN"
    Write-Host ""

    # ---- Step 4: MCP Gateway + Targets (via boto3) ----
    Write-Host "=========================================="
    Write-Host "  Step 4: MCP Gateway + Register Targets"
    Write-Host "=========================================="

    $env:GATEWAY_ROLE_ARN = $GW_ROLE_ARN
    $env:LAMBDA_PREFIX = $LAMBDA_PREFIX
    # AWS_ACCOUNT_ID already set

    $ErrorActionPreference = "Continue"
    $gwOutput = python "$ScriptDir\manage_gateway.py" 2>&1 | Out-String
    $gwExitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($gwExitCode -ne 0) {
        Write-Host "  ERROR: manage_gateway.py failed." -ForegroundColor Red
        Write-Host "  $gwOutput" -ForegroundColor Red
        exit 1
    }

    # Parse output lines: GATEWAY_ID=xxx, GATEWAY_URL=xxx
    $GATEWAY_ID = ""
    $GATEWAY_URL = ""
    foreach ($line in ($gwOutput -split "`n")) {
        if ($line -match "^GATEWAY_ID=(.+)$") { $GATEWAY_ID = $Matches[1].Trim() }
        if ($line -match "^GATEWAY_URL=(.+)$") { $GATEWAY_URL = $Matches[1].Trim() }
    }

    if (-not $GATEWAY_URL) {
        Write-Host "  ERROR: Could not parse GATEWAY_URL from manage_gateway.py output." -ForegroundColor Red
        Write-Host "  Output: $gwOutput" -ForegroundColor Red
        exit 1
    }

    $env:GATEWAY_URL = $GATEWAY_URL
    Write-Host "  Gateway ID:  $GATEWAY_ID"
    Write-Host "  Gateway URL: $GATEWAY_URL"
    Write-Host ""
}

# ============================================================
# Create project structure with all 5 agents
# ============================================================
Write-Host "Setting up deployment project..."

if (Test-Path $BuildDir) { cmd /c "rmdir /s /q `"$BuildDir`"" 2>$null; Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue }

# Use agentcore create to scaffold the CDK project
$projectName = "aiteamgateway"
Push-Location (Split-Path $BuildDir -Parent)
$buildDirName = Split-Path $BuildDir -Leaf
$ErrorActionPreference = "Continue"
Write-Host "  Running: agentcore create --name ai_gk_agent --project-name $projectName --output-dir $buildDirName"
& $agentcorePath create --name "ai_gk_agent" --project-name $projectName --build CodeZip --framework Strands --model-provider Bedrock --memory none --skip-git --skip-python-setup --output-dir $buildDirName 2>&1 | ForEach-Object { Write-Host "    $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: agentcore create exited with code $LASTEXITCODE" -ForegroundColor Yellow
}
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
if (-not (Test-Path $cdkDir)) {
    Write-Host ""
    Write-Host "  ERROR: CDK directory not found at: $cdkDir" -ForegroundColor Red
    Write-Host "  'agentcore create' failed to scaffold the project." -ForegroundColor Red
    Write-Host "  This usually happens due to long path issues (OneDrive)." -ForegroundColor Red
    Write-Host "  Try: Copy project to C:\dev\ and run from there." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Build directory contents:" -ForegroundColor Yellow
    if (Test-Path $BuildDir) { Get-ChildItem $BuildDir -Recurse -Depth 2 | Select-Object FullName }
    else { Write-Host "    (build directory does not exist)" }
    exit 1
}
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

    # Copy main.py into src/ subdirectory (preserves ../lib relative path)
    $srcDir = Join-Path $appDir "src"
    New-Item -ItemType Directory -Path $srcDir -Force | Out-Null
    Copy-Item "$ScriptDir\$agent\src\main.py" "$srcDir\main.py"

    # Copy shared lib (at same level as src/ so ../lib works)
    $libSource = Join-Path $ScriptDir "..\lib"
    if (Test-Path $libSource) {
        $libDest = Join-Path $appDir "lib"
        New-Item -ItemType Directory -Path $libDest -Force | Out-Null
        robocopy $libSource $libDest /E /XD __pycache__ /NJH /NJS /NFL /NDL /NC /NS | Out-Null
    }

    # Copy gateway_agent_base.py and gateway_invoke_handler.py into each app/<agent>/
    Copy-Item "$ScriptDir\gateway_agent_base.py" "$appDir\gateway_agent_base.py"
    Copy-Item "$ScriptDir\gateway_invoke_handler.py" "$appDir\gateway_invoke_handler.py"

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
      "entrypoint": "src/main.py",
      "codeLocation": "app/$name/",
      "runtimeVersion": "PYTHON_3_12",
      "networkMode": "PUBLIC",
      "protocol": "HTTP",
      "environmentVariables": {
        "GATEWAY_URL": "$GATEWAY_URL",
        "AWS_DEFAULT_REGION": "$($env:AWS_DEFAULT_REGION)"
      }
    }
"@
}

$agentcoreJson = @"
{
  "`$schema": "https://schema.agentcore.aws.dev/v1/agentcore.json",
  "name": "aiteamgateway",
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
# Attach gateway permissions to execution roles
# ============================================================
Write-Host ""
Write-Host "Attaching AgentCore Gateway permissions to execution roles..."

$ErrorActionPreference = "Continue"
$execRoles = (aws iam list-roles --query "Roles[?starts_with(RoleName, 'AgentCore-aiteamgateway-')].RoleName" --output text 2>$null)
$ErrorActionPreference = "Stop"

if ($execRoles -and $execRoles.Trim()) {
    foreach ($execRoleName in ($execRoles.Trim() -split '\s+')) {
        $policyDoc = @"
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "bedrock-agentcore:InvokeGateway"
        ],
        "Resource": "arn:aws:bedrock-agentcore:$($env:AWS_DEFAULT_REGION):${awsAccountId}:gateway/*"
    }]
}
"@
        $tempPolicyFile = [System.IO.Path]::GetTempFileName()
        [IO.File]::WriteAllText($tempPolicyFile, $policyDoc, [System.Text.UTF8Encoding]::new($false))

        $ErrorActionPreference = "Continue"
        aws iam put-role-policy --role-name $execRoleName --policy-name AgentCoreGatewayAccess --policy-document "file://$tempPolicyFile" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  `u{2705} Gateway permissions attached to: $execRoleName" -ForegroundColor Green
        } else {
            Write-Host "  `u{26A0}`u{FE0F}  Failed to attach gateway permissions to: $execRoleName" -ForegroundColor Yellow
        }
        $ErrorActionPreference = "Stop"

        Remove-Item $tempPolicyFile -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  `u{26A0}`u{FE0F}  Could not find execution roles - attach AgentCoreGatewayAccess policy manually" -ForegroundColor Yellow
}

# ============================================================
# Set GATEWAY_URL environment variable on each runtime
# (agentcore deploy via CDK does not pass environmentVariables from agentcore.json)
# ============================================================
Write-Host ""
Write-Host "Setting GATEWAY_URL environment variable on deployed runtimes..."

$runtimePrefix = "aiteamgateway"
$envVarScript = @"
import boto3, sys
client = boto3.client('bedrock-agentcore-control', region_name='$($env:AWS_DEFAULT_REGION)')
runtimes = client.list_agent_runtimes()['agentRuntimes']
prefix = '$runtimePrefix'
gateway_url = '$GATEWAY_URL'
region = '$($env:AWS_DEFAULT_REGION)'
updated = 0
for rt in runtimes:
    name = rt.get('agentRuntimeName', '')
    if name.startswith(prefix + '_'):
        rid = rt['agentRuntimeId']
        r = client.get_agent_runtime(agentRuntimeId=rid)
        client.update_agent_runtime(
            agentRuntimeId=rid,
            agentRuntimeArtifact=r['agentRuntimeArtifact'],
            roleArn=r['roleArn'],
            networkConfiguration=r['networkConfiguration'],
            environmentVariables={'GATEWAY_URL': gateway_url, 'AWS_DEFAULT_REGION': region}
        )
        print(f'  Set GATEWAY_URL on: {name} ({rid})')
        updated += 1
if updated == 0:
    print('  WARNING: No runtimes found with prefix ' + prefix)
"@
python -c $envVarScript

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
Write-Host "  Gateway:  $GATEWAY_URL"
Write-Host ""

# List Agent ARNs
if ($deployExitCode -eq 0) {
    Write-Host "  Agent ARNs (copy these to the Player Portal):" -ForegroundColor Cyan
    $ErrorActionPreference = "Continue"
    $allRuntimes = aws bedrock-agentcore-control list-agent-runtimes --query "agentRuntimes[].{name:agentRuntimeName,arn:agentRuntimeArn}" --output json --region $env:AWS_DEFAULT_REGION 2>$null | ConvertFrom-Json
    $ErrorActionPreference = "Stop"
    foreach ($agent in $allAgents) {
        $agentNameClean = ($agent -replace '-', '_') + "_agent"
        $match = $allRuntimes | Where-Object { $_.name -eq "aiteamgateway_$agentNameClean" }
        if ($match) {
            $displayName = $agent.ToUpper() -replace 'AI-',''
            Write-Host "    $($displayName): $($match.arn)" -ForegroundColor White
        }
    }
    Write-Host ""
}

# Cleanup
Write-Host "Cleaning up build directory..."
if (Test-Path $BuildDir) { cmd /c "rmdir /s /q `"$BuildDir`"" 2>$null; Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue }

if ($deployExitCode -ne 0) { exit 1 }
