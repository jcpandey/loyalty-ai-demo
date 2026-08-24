param(
    [switch]$SkipCompile,
    [switch]$SkipTests,
    [switch]$SkipIngest,
    [switch]$SkipVerifier,
    [switch]$SkipOpsHealth,
    [string]$PythonExe
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$defaultPythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = $env:PYTHON_EXE
}

if ([string]::IsNullOrWhiteSpace($PythonExe) -and (Test-Path $defaultPythonExe)) {
    $PythonExe = $defaultPythonExe
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        $PythonExe = $pythonCommand.Source
    }
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    throw "Python interpreter not found. Set PYTHON_EXE, pass -PythonExe, or create .venv\\Scripts\\python.exe"
}

Push-Location $repoRoot

try {
    Write-Host "Running MVP smoke checks from $repoRoot using $PythonExe" -ForegroundColor Cyan

    $stepNumber = 1
    $stepTotal = 5

    if (-not $SkipCompile) {
        Write-Host "[$stepNumber/$stepTotal] Compile check" -ForegroundColor Yellow
        & $PythonExe -m compileall simulator lambdas rag tests tools
        if ($LASTEXITCODE -ne 0) {
            throw "Compile check failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipTests) {
        Write-Host "[$stepNumber/$stepTotal] Unit tests" -ForegroundColor Yellow
        & $PythonExe -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Unit tests failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipIngest) {
        Write-Host "[$stepNumber/$stepTotal] RAG document ingest" -ForegroundColor Yellow
        & $PythonExe .\rag\ingest_documents.py
        if ($LASTEXITCODE -ne 0) {
            throw "RAG ingest failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipVerifier) {
        Write-Host "[$stepNumber/$stepTotal] Databricks and assistant verifier" -ForegroundColor Yellow
        & $PythonExe .\tools\mvp_verify.py
        if ($LASTEXITCODE -ne 0) {
            throw "MVP verifier failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipOpsHealth) {
        Write-Host "[$stepNumber/$stepTotal] Operational health gate" -ForegroundColor Yellow
        & $PythonExe .\tools\ops_health_check.py
        if ($LASTEXITCODE -ne 0) {
            throw "Operational health gate failed"
        }
    }

    Write-Host "MVP smoke checks and operational health gate passed." -ForegroundColor Green
}
finally {
    Pop-Location
}