# ============================================================
# 一键远程部署：从 Windows 把整套系统装到服务器（密钥免密）
# 前置：服务器已创建、部署公钥已粘贴（见 deploy/oracle-free-tier.md 第 3 步）
# 用法（在本项目根目录）：
#   powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1 -Server <服务器IP>
#   # Oracle Ubuntu 默认用户 ubuntu；其他厂商若是 root：
#   powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1 -Server <IP> -User root
# ============================================================
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$User = "ubuntu",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\linkedin-auto-deploy",
    [string]$ResumePath = "C:\Users\林耀国\Desktop\BendyLin_Resume0903.pdf",
    [string]$RunsDir = "C:\freelance-auto\data\linkedin_runs"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $KeyPath)) { throw "找不到部署私钥: $KeyPath" }

$Target = "$User@$Server"
$SshOpts = @("-i", $KeyPath, "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=15", "-o", "BatchMode=yes")

function Invoke-Remote {
    param([string]$Cmd)
    Write-Host "  > $Cmd" -ForegroundColor DarkGray
    & ssh @SshOpts $Target $Cmd
    if ($LASTEXITCODE -ne 0) { throw "远程命令失败(exit $LASTEXITCODE): $Cmd" }
}

Write-Host "==> [0/6] 连接测试 ($Target)" -ForegroundColor Cyan
& ssh @SshOpts $Target "echo CONNECTED: `$(whoami)@`$(hostname)"
if ($LASTEXITCODE -ne 0) { throw "SSH 连接失败。检查 IP/用户名/公钥是否已粘贴" }

Write-Host "==> [1/6] 拉取项目代码" -ForegroundColor Cyan
Invoke-Remote "sudo apt-get update -qq && sudo apt-get install -y -qq git"
Invoke-Remote "test -d /opt/linkedin-auto/.git && echo REPO-EXISTS || sudo git clone https://github.com/xiaolin-bot/linkedin-auto.git /opt/linkedin-auto"

Write-Host "==> [2/6] 执行安装脚本（约 3-8 分钟：依赖 + Chrome + Playwright）" -ForegroundColor Cyan
Invoke-Remote "sudo bash /opt/linkedin-auto/deploy/install.sh"

Write-Host "==> [3/6] 上传简历" -ForegroundColor Cyan
if (Test-Path $ResumePath) {
    & scp @SshOpts $ResumePath "${Target}:/tmp/resume_upload.pdf"
    if ($LASTEXITCODE -ne 0) { throw "简历上传失败" }
    Invoke-Remote "sudo mkdir -p /opt/linkedin-auto/resume && sudo mv /tmp/resume_upload.pdf /opt/linkedin-auto/resume/BendyLin_Resume0903.pdf && sudo ls -l /opt/linkedin-auto/resume/"
} else {
    Write-Warning "简历文件不存在，跳过: $ResumePath（记得之后手动上传）"
}

Write-Host "==> [4/6] 迁移投递历史（用于去重，避免重复投已投岗位）" -ForegroundColor Cyan
if (Test-Path $RunsDir) {
    $tmpTar = Join-Path $env:TEMP "linkedin_runs_upload.tar.gz"
    if (Test-Path $tmpTar) { Remove-Item $tmpTar -Force }
    & tar -czf $tmpTar -C $RunsDir .
    & scp @SshOpts $tmpTar "${Target}:/tmp/linkedin_runs_upload.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw "历史上传失败" }
    Invoke-Remote "sudo tar -xzf /tmp/linkedin_runs_upload.tar.gz -C /opt/linkedin-auto/data/linkedin_runs && sudo rm -f /tmp/linkedin_runs_upload.tar.gz && printf '历史文件数: ' && sudo ls /opt/linkedin-auto/data/linkedin_runs | wc -l"
} else {
    Write-Warning "投递历史目录不存在，跳过: $RunsDir"
}

Write-Host "==> [5/6] 验证安装" -ForegroundColor Cyan
Invoke-Remote 'sudo /opt/linkedin-auto/.venv/bin/python -c "import playwright, linkedin.runner" && echo PYTHON-IMPORT-OK'
Invoke-Remote "systemctl list-timers linkedin-auto.timer --no-pager || true"

Write-Host ""
Write-Host "==> [6/6] 部署完成！还差最后一步：VNC 登录 LinkedIn" -ForegroundColor Green
Write-Host ""
Write-Host "  1) 在服务器上执行：  bash /opt/linkedin-auto/deploy/login-vnc.sh" -ForegroundColor Yellow
Write-Host "  2) 本机另开一个终端，运行隧道："
Write-Host "       powershell -ExecutionPolicy Bypass -File deploy\open-vnc-tunnel.ps1 -Server $Server -User $User" -ForegroundColor Yellow
Write-Host "  3) 用 VNC Viewer 连接 localhost:5900，在弹出的浏览器里登录 LinkedIn"
Write-Host "  4) 登录成功后，在服务器执行：  sudo systemctl start linkedin-auto.timer"
Write-Host ""
Write-Host "  完成后可手动验证一轮：  sudo bash /usr/local/bin/linkedin-run.sh"
Write-Host ""
