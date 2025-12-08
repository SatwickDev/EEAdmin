#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Migrate ChromaDB environment variable implementation to ADIBPoc project
.DESCRIPTION
    Copies modified files and applies necessary changes to enable ChromaDB
    configuration via environment variables in the target project.
#>

$ErrorActionPreference = "Stop"

$source = "C:\Users\saipr\Documents\GitHub\EEAIAdmin"
$target = "C:\Users\saipr\Downloads\ADIB_WorkingPOC 2\ADIB_WorkingPOC 2\ADIBPoc"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "ChromaDB Environment Variable Migration" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if target exists
if (-not (Test-Path $target)) {
    Write-Host "[ERROR] Target folder not found: $target" -ForegroundColor Red
    exit 1
}

Write-Host "Source: $source" -ForegroundColor Gray
Write-Host "Target: $target`n" -ForegroundColor Gray

# Step 1: Copy modified core files
Write-Host "[1/6] Copying chroma_manager.py..." -ForegroundColor Yellow
$sourceFile = Join-Path $source "app\utils\chroma_manager.py"
$targetFile = Join-Path $target "app\utils\chroma_manager.py"

if (Test-Path $sourceFile) {
    # Backup existing file
    if (Test-Path $targetFile) {
        $backup = "$targetFile.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $targetFile $backup -Force
        Write-Host "      Backed up existing file to: $backup" -ForegroundColor Gray
    }
    Copy-Item $sourceFile $targetFile -Force
    Write-Host "      [OK] chroma_manager.py copied" -ForegroundColor Green
} else {
    Write-Host "      [SKIP] Source file not found" -ForegroundColor Yellow
}

# Step 2: Copy setup script
Write-Host "[2/6] Copying setup_chroma_config.py..." -ForegroundColor Yellow
$sourceFile = Join-Path $source "setup_chroma_config.py"
$targetFile = Join-Path $target "setup_chroma_config.py"

if (Test-Path $sourceFile) {
    if (Test-Path $targetFile) {
        $backup = "$targetFile.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $targetFile $backup -Force
    }
    Copy-Item $sourceFile $targetFile -Force
    Write-Host "      [OK] setup_chroma_config.py copied" -ForegroundColor Green
} else {
    Write-Host "      [SKIP] Source file not found" -ForegroundColor Yellow
}

# Step 3: Copy .env.example
Write-Host "[3/6] Copying .env.example..." -ForegroundColor Yellow
$sourceFile = Join-Path $source ".env.example"
$targetFile = Join-Path $target ".env.example"

if (Test-Path $sourceFile) {
    Copy-Item $sourceFile $targetFile -Force
    Write-Host "      [OK] .env.example copied" -ForegroundColor Green
} else {
    Write-Host "      [SKIP] Source file not found" -ForegroundColor Yellow
}

# Step 4: Copy ENV_SETUP_GUIDE.txt
Write-Host "[4/6] Copying ENV_SETUP_GUIDE.txt..." -ForegroundColor Yellow
$sourceFile = Join-Path $source "ENV_SETUP_GUIDE.txt"
$targetFile = Join-Path $target "ENV_SETUP_GUIDE.txt"

if (Test-Path $sourceFile) {
    Copy-Item $sourceFile $targetFile -Force
    Write-Host "      [OK] ENV_SETUP_GUIDE.txt copied" -ForegroundColor Green
} else {
    Write-Host "      [SKIP] Source file not found" -ForegroundColor Yellow
}

# Step 5: Copy documentation
Write-Host "[5/6] Copying CHROMA_ENV_VAR_IMPLEMENTATION.md..." -ForegroundColor Yellow
$sourceFile = Join-Path $source "CHROMA_ENV_VAR_IMPLEMENTATION.md"
$targetFile = Join-Path $target "CHROMA_ENV_VAR_IMPLEMENTATION.md"

if (Test-Path $sourceFile) {
    Copy-Item $sourceFile $targetFile -Force
    Write-Host "      [OK] Documentation copied" -ForegroundColor Green
} else {
    Write-Host "      [SKIP] Source file not found" -ForegroundColor Yellow
}

# Step 6: Update run.py and app/__init__.py
Write-Host "[6/6] Updating run.py and app/__init__.py..." -ForegroundColor Yellow

# Update run.py
$runPyPath = Join-Path $target "run.py"
if (Test-Path $runPyPath) {
    $content = Get-Content $runPyPath -Raw
    
    # Check if dotenv lines already exist
    if ($content -notmatch "from dotenv import load_dotenv") {
        # Add after "import os"
        $newContent = $content -replace "(import os)", "`$1`n`n# Load environment variables from .env file (optional - uncomment to use)`n# from dotenv import load_dotenv`n# load_dotenv()  # Load .env before anything else"
        Set-Content -Path $runPyPath -Value $newContent -NoNewline
        Write-Host "      [OK] run.py updated" -ForegroundColor Green
    } else {
        Write-Host "      [SKIP] run.py already has dotenv code" -ForegroundColor Gray
    }
} else {
    Write-Host "      [SKIP] run.py not found in target" -ForegroundColor Yellow
}

# Update app/__init__.py
$initPyPath = Join-Path $target "app\__init__.py"
if (Test-Path $initPyPath) {
    $content = Get-Content $initPyPath -Raw
    
    # Check if dotenv lines already exist
    if ($content -notmatch "from dotenv import load_dotenv") {
        # Find the import section and add before load_dotenv() call if it exists
        if ($content -match "from app.utils.app_config import load_dotenv") {
            $newContent = $content -replace "(from app.utils.app_config import load_dotenv)", "# Load environment variables from .env file (optional - uncomment to use)`n# from dotenv import load_dotenv as load_env_file`n# load_env_file()  # Load .env before anything else`n`n`$1"
        } else {
            # Add after imports
            $newContent = $content -replace "(import logging)", "`$1`n`n# Load environment variables from .env file (optional - uncomment to use)`n# from dotenv import load_dotenv as load_env_file`n# load_env_file()  # Load .env before anything else"
        }
        Set-Content -Path $initPyPath -Value $newContent -NoNewline
        Write-Host "      [OK] app/__init__.py updated" -ForegroundColor Green
    } else {
        Write-Host "      [SKIP] app/__init__.py already has dotenv code" -ForegroundColor Gray
    }
} else {
    Write-Host "      [SKIP] app/__init__.py not found in target" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Files migrated:" -ForegroundColor Green
Write-Host "  [OK] app/utils/chroma_manager.py" -ForegroundColor Gray
Write-Host "  [OK] setup_chroma_config.py" -ForegroundColor Gray
Write-Host "  [OK] .env.example" -ForegroundColor Gray
Write-Host "  [OK] ENV_SETUP_GUIDE.txt" -ForegroundColor Gray
Write-Host "  [OK] CHROMA_ENV_VAR_IMPLEMENTATION.md" -ForegroundColor Gray
Write-Host "  [OK] run.py (updated)" -ForegroundColor Gray
Write-Host "  [OK] app/__init__.py (updated)" -ForegroundColor Gray

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Review the changes in the ADIBPoc folder" -ForegroundColor White
Write-Host "2. Test the configuration:" -ForegroundColor White
Write-Host "   cd '$target'" -ForegroundColor Gray
Write-Host "   python setup_chroma_config.py --show-env" -ForegroundColor Gray
Write-Host "`n3. For Terraform deployment, set environment variables:" -ForegroundColor White
Write-Host "   CHROMA_MODE=disabled (or enabled/allowlist)" -ForegroundColor Gray
Write-Host "   CHROMA_CUSTOMERS=bankA,bankB (for allowlist mode)" -ForegroundColor Gray

Write-Host "`nDocumentation: Read CHROMA_ENV_VAR_IMPLEMENTATION.md for full details`n" -ForegroundColor Cyan
