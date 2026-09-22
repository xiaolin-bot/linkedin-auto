# ============================================================
# 从 Windows 电脑推送 简历 + 投递历史 到服务器
# 用法（在本项目根目录）：
#   powershell -ExecutionPolicy Bypass -File deploy\push-from-windows.ps1 -Server root@1.2.3.4
# 可选参数：
#   -ResumePath "C:\Users\林耀国\Desktop\BendyLin_Resume0903.pdf"
#   -RunsDir    "C:\freelance-auto\data\linkedin_runs"
# ============================================================
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$ResumePath = "C:\Users\林耀国\Desktop\BendyLin_Resume0903.pdf",
    [string]$RunsDir = "C:\freelance-auto\data\linkedin_runs"
)

$ErrorActionPreference = "Stop"
$APP_DIR = "/opt/linkedin-auto"

Write-Host "==> 创建服务器目录"
ssh $Server "mkdir -p $APP_DIR/resume $APP_DIR/data/linkedin_runs"

if (Test-Path $ResumePath) {
    Write-Host "==> 上传简历: $ResumePath"
    scp $ResumePath "${Server}:$APP_DIR/resume/"
} else {
    Write-Warning "简历不存在: $ResumePath（跳过）"
}

if (Test-Path $RunsDir) {
    $runs = Get-ChildItem "$RunsDir\run_*.json"
    Write-Host "==> 上传投递历史 $($runs.Count) 个文件（用于去重，避免重复投递）"
    scp "$RunsDir\run_*.json" "${Server}:$APP_DIR/data/linkedin_runs/"
} else {
    Write-Warning "投递历史目录不存在: $RunsDir（跳过）"
}

Write-Host "==> 完成。可在服务器上验证: ssh $Server 'ls /opt/linkedin-auto/resume /opt/linkedin-auto/data/linkedin_runs | head'"
