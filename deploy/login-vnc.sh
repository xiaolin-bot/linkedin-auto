#!/usr/bin/env bash
# ============================================================
# 一次性 LinkedIn 登录（服务器无桌面 → VNC 远程操作）
# 用法：bash /opt/linkedin-auto/deploy/login-vnc.sh
# 流程：启动虚拟显示(:99) + x11vnc(仅localhost) → 你通过 SSH 隧道用
#       VNC Viewer 连上 → 在弹出的浏览器里手动登录 → 脚本自动保存会话
# ============================================================
set -euo pipefail

APP_DIR=/opt/linkedin-auto
cd "$APP_DIR"
export LINKEDIN_DATA_DIR="$APP_DIR/data"
if [ "$(id -u)" = "0" ]; then
  export LINKEDIN_NO_SANDBOX=1
fi
export DISPLAY=:99

cleanup() {
  pkill -f "x11vnc -display :99" 2>/dev/null || true
  pkill -f "Xvfb :99" 2>/dev/null || true
  echo "VNC 已关闭"
}
trap cleanup EXIT

# 清理残留
pkill -f "x11vnc -display :99" 2>/dev/null || true
pkill -f "Xvfb :99" 2>/dev/null || true
sleep 1

echo "==> 启动虚拟显示 :99 ..."
Xvfb :99 -screen 0 1920x1080x24 &
sleep 2

echo "==> 启动 VNC（仅监听 localhost，必须通过 SSH 隧道访问）..."
x11vnc -display :99 -localhost -forever -shared -nopw -rfbport 5900 -quiet &
sleep 2

SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "<服务器IP>")
cat <<EOF

============================================================
VNC 已就绪！在你的 Windows 电脑上完成下面两步：

【第 1 步】开 SSH 隧道（Windows 的 PowerShell 或 CMD 里运行）：
   ssh -N -L 5900:localhost:5900 root@${SERVER_IP}

【第 2 步】用 VNC Viewer 连接：
   - 下载 TightVNC Viewer（免费）: https://www.tightvnc.com/download.php
     或 RealVNC Viewer: https://www.realvnc.com/download/viewer/
   - 连接地址填:  localhost:5900    （无密码）
   - 连接成功后，窗口里会看到 Chrome 浏览器
   - 在浏览器里完成 LinkedIn 登录（如遇验证码/邮箱验证，正常完成即可）

登录成功后脚本会自动检测并保存会话，然后回到本终端按 Ctrl+C 即可。
============================================================
EOF

"$APP_DIR/.venv/bin/python" -X utf8 "$APP_DIR/login_linkedin.py"
