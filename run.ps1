<# 
.SYNOPSIS
    LinkedIn Auto Apply 一键启动脚本
.DESCRIPTION
    自动检查环境、安装依赖、运行投递
#>

param(
    [switch]$InstallOnly,
    [switch]$LoginOnly,
    [int]$MaxJobs = 10,
    [string]$Keywords = "AI sales,SaaS sales,technical sales",
    [string]$SleepRange = "30,90"
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = $PSScriptRoot
$VENV_DIR = Join-Path $PROJECT_DIR ".venv"
$PYTHON = Join-Path $VENV_DIR "Scripts\python.exe"
$REQUIREMENTS = "pyproject.toml"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

# 检查虚拟环境
if (-not (Test-Path $PYTHON)) {
    Write-Log "创建虚拟环境..." "INFO"
    python -m venv .venv
    & $PYTHON -m pip install --upgrade pip
    & $PYTHON -m pip install -e .
    Write-Log "依赖安装完成" "INFO"
}

if ($InstallOnly) {
    Write-Log "安装完成，退出" "INFO"
    exit 0
}

if ($LoginOnly) {
    Write-Log "启动登录流程..." "INFO"
    & $PYTHON -X utf8 login_linkedin.py
    exit 0
}

# 运行投递
Write-Log "启动投递: keywords=$Keywords, max-jobs=$MaxJobs, sleep=$SleepRange" "INFO"
& $PYTHON -X utf8 run_linkedin_auto.py `
    --keywords $Keywords `
    --max-jobs $MaxJobs `
    --sleep-range $SleepRange `
    --no-login-prompt

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Log "投递完成" "INFO"
} else {
    Write-Log "投递异常退出，代码: $exitCode" "ERROR"
}
exit $exitCode