#!/usr/bin/env bash
# ============================================================
# LinkedIn Auto Apply - 云端一键安装（Ubuntu 22.04 / 24.04）
# 用法：sudo bash deploy/install.sh
# 幂等：重复运行 = 更新代码 + 重装依赖
# ============================================================
set -euo pipefail

APP_DIR=/opt/linkedin-auto
DATA_DIR=$APP_DIR/data
RESUME_DIR=$APP_DIR/resume
REPO_URL=https://github.com/xiaolin-bot/linkedin-auto.git

if [ "$(id -u)" = "0" ]; then SUDO=""; else SUDO="sudo"; fi

echo "==> [1/8] 安装系统依赖"
$SUDO apt-get update -y
$SUDO apt-get install -y python3-venv python3-pip xvfb x11vnc git curl wget tzdata

echo "==> [2/8] 设置时区 Asia/Hong_Kong（投递时间窗口 8:00-22:00）"
$SUDO timedatectl set-timezone Asia/Hong_Kong

echo "==> [3/8] 尝试安装 Google Chrome（失败则自动回退 Playwright 自带 Chromium）"
if ! command -v google-chrome >/dev/null 2>&1; then
    if wget -q -O /tmp/chrome.deb --timeout=60 \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb; then
        $SUDO apt-get install -y /tmp/chrome.deb || echo "  Chrome 安装失败，将使用自带 Chromium（不影响运行）"
    else
        echo "  下载 Chrome 失败（网络受限），将使用自带 Chromium（不影响运行）"
    fi
fi

echo "==> [4/8] 拉取/更新项目代码"
if [ -d "$APP_DIR/.git" ]; then
    $SUDO git -C "$APP_DIR" pull --ff-only || echo "  git pull 失败（本地有改动？），跳过"
else
    $SUDO mkdir -p "$APP_DIR"
    $SUDO git clone "$REPO_URL" "$APP_DIR"
fi
$SUDO mkdir -p "$DATA_DIR" "$DATA_DIR/linkedin_runs" "$DATA_DIR/linkedin_schedule" "$RESUME_DIR"
$SUDO chown -R root:root "$APP_DIR"

echo "==> [5/8] Python 依赖（venv + playwright chromium）"
cd "$APP_DIR"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -e . -q
./.venv/bin/python -m playwright install --with-deps chromium

echo "==> [6/8] 安装运行封装脚本 /usr/local/bin/linkedin-run.sh"
$SUDO cp "$APP_DIR/deploy/run.sh" /usr/local/bin/linkedin-run.sh
$SUDO chmod +x /usr/local/bin/linkedin-run.sh

echo "==> [7/8] 安装 systemd 服务与定时器（每天 8/12/16/20 点，±5分钟随机抖动）"
$SUDO cp "$APP_DIR/deploy/linkedin-auto.service" /etc/systemd/system/
$SUDO cp "$APP_DIR/deploy/linkedin-auto.timer" /etc/systemd/system/
$SUDO systemctl daemon-reload
$SUDO systemctl enable linkedin-auto.timer

echo "==> [8/8] 完成"
cat <<'EOF'

============================================================
安装完成！还差两步：

1) 上传简历（在你的 Windows 电脑上执行，或手动 scp）：
   scp "C:\Users\林耀国\Desktop\BendyLin_Resume0903.pdf" root@<服务器IP>:/opt/linkedin-auto/resume/

2) 一次性登录 LinkedIn（VNC 方式，约 3 分钟）：
   bash /opt/linkedin-auto/deploy/login-vnc.sh
   （按屏幕提示开 SSH 隧道 + VNC Viewer 连接）

3) 登录完成后启动定时器：
   systemctl start linkedin-auto.timer

查看状态:  systemctl list-timers linkedin-auto.timer
手动跑一轮: bash /usr/local/bin/linkedin-run.sh
查看日志:  journalctl -u linkedin-auto.service -f
          cat /opt/linkedin-auto/data/linkedin_schedule/linkedin_$(date +%Y%m%d).log
============================================================
EOF
