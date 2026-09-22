# ============================================================
# 打开 VNC 隧道（用于服务器上一次性登录 LinkedIn）
# 保持这个窗口开着，然后用 VNC Viewer 连 localhost:5900
# 用法：powershell -ExecutionPolicy Bypass -File deploy\open-vnc-tunnel.ps1 -Server <服务器IP>
# ============================================================
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$User = "ubuntu",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\linkedin-auto-deploy",
    [int]$LocalPort = 5900
)

if (-not (Test-Path $KeyPath)) { throw "找不到部署私钥: $KeyPath" }

Write-Host "建立隧道: localhost:$LocalPort  ->  $User@$Server:5900" -ForegroundColor Cyan
Write-Host "（保持本窗口开着；VNC 操作用完按 Ctrl+C 结束）"
Write-Host ""

& ssh -i $KeyPath -o StrictHostKeyChecking=accept-new -N -L "${LocalPort}:localhost:5900" "$User@$Server"
