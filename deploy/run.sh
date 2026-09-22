#!/usr/bin/env bash
# LinkedIn Auto Apply 单轮运行封装（由 systemd timer / 手动调用）
# 被 install.sh 复制到 /usr/local/bin/linkedin-run.sh
set -euo pipefail

APP_DIR=/opt/linkedin-auto
cd "$APP_DIR"

export LINKEDIN_DATA_DIR="$APP_DIR/data"
export LINKEDIN_RESUME="$APP_DIR/resume/BendyLin_Resume0903.pdf"
export LINKEDIN_CHANNEL="${LINKEDIN_CHANNEL:-chrome}"   # 没装 Chrome 会自动回退 chromium

# root 环境 Chrome 需要 --no-sandbox
if [ "$(id -u)" = "0" ]; then
  export LINKEDIN_NO_SANDBOX=1
fi

# 清理上次异常退出残留的浏览器进程（避免 profile 目录被锁）
pkill -f "user-data-dir=$APP_DIR/data/linkedin_profile" 2>/dev/null || true
sleep 1

# 服务器无桌面：用 xvfb 虚拟显示跑"有头"浏览器（指纹更接近真实用户）
exec xvfb-run -a -s "-screen 0 1920x1080x24" \
  "$APP_DIR/.venv/bin/python" -X utf8 "$APP_DIR/run_linkedin_auto.py"
