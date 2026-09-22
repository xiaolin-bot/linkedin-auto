#!/usr/bin/env python3
"""导入登录态 JSON → 服务器持久 profile（免 VNC 备用方案的「导入」端）。

用法（在服务器上执行，一次性）：
    # 先确保已安装依赖：cd /opt/linkedin-auto && ./.venv/bin/pip install -e .
    # 服务器无桌面 → 用 xvfb 跑（import 需要渲染 localStorage）
    xvfb-run -a ./.venv/bin/python -X utf8 deploy/import-login-server.py \
        --state /tmp/linkedin_state.json

导入后验证：
    LINKEDIN_DATA_DIR=/opt/linkedin-auto/data ./.venv/bin/python -c \
        "import sys; sys.path.insert(0,'src'); from linkedin.browser import LinkedInBrowser; b=LinkedInBrowser(profile_dir='/opt/linkedin-auto/data/linkedin_profile'); b.start(); print('logged_in =', b.is_logged_in()); b.stop()"

⚠️ 稳定性不如 VNC 登录（LinkedIn 可能因"新设备/IP"吊销会话）；失败则改用 VNC 登录。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright


def resolve_data_dir() -> Path:
    if os.environ.get("LINKEDIN_DATA_DIR"):
        return Path(os.environ["LINKEDIN_DATA_DIR"])
    legacy = Path("C:/freelance-auto/data")
    if legacy.exists():
        return legacy
    return Path(__file__).resolve().parents[1] / "data"


def launch(pw, profile: Path, headless: bool):
    channel = (os.environ.get("LINKEDIN_CHANNEL") or "chrome").strip() or "chrome"
    args = ["--disable-blink-features=AutomationControlled", "--no-first-run"]
    if os.environ.get("LINKEDIN_NO_SANDBOX") == "1":
        args.append("--no-sandbox")
    channels = [None] if channel == "chromium" else [channel, None]
    last = None
    for ch in channels:
        try:
            kw = {"user_data_dir": str(profile), "headless": headless, "args": args, "viewport": None}
            if ch:
                kw["channel"] = ch
            return pw.chromium.launch_persistent_context(**kw)
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"浏览器启动失败: {last}")


def main() -> int:
    ap = argparse.ArgumentParser(description="导入 storage_state JSON 到持久 profile")
    ap.add_argument("--state", required=True, help="export-login-windows.py 导出的 JSON")
    ap.add_argument("--profile", default="", help="持久 profile 目录（默认自动探测）")
    ap.add_argument("--headless", action="store_true", default=True)
    args = ap.parse_args()

    state_file = Path(args.state)
    if not state_file.exists():
        return sys.exit(f"找不到导入文件: {state_file}")
    state = json.loads(state_file.read_text(encoding="utf-8"))

    profile = Path(args.profile) if args.profile else resolve_data_dir() / "linkedin_profile"
    profile.mkdir(parents=True, exist_ok=True)
    print(f"profile: {profile}")

    pw = sync_playwright().start()
    ctx = launch(pw, profile, headless=args.headless)
    try:
        cookies = state.get("cookies", [])
        if cookies:
            ctx.add_cookies(cookies)
            print(f"✅ 已写入 cookie: {len(cookies)} 个")
        # 还原 localStorage（LinkedIn 部分设备指纹状态存在这里）
        origins = state.get("origins", [])
        if origins:
            page = ctx.new_page()
            ok = 0
            for o in origins:
                origin = o.get("origin") or ""
                items = o.get("localStorage") or []
                if not origin or not items:
                    continue
                try:
                    page.goto(origin, wait_until="domcontentloaded", timeout=25000)
                    page.evaluate(
                        "(items)=>{for(const it of items){try{localStorage.setItem(it.name,it.value)}catch(e){}}}",
                        items,
                    )
                    ok += 1
                except Exception as e:  # noqa: BLE001
                    print(f"   localStorage 还原失败 {origin[:50]}: {str(e)[:60]}")
            page.close()
            print(f"✅ localStorage 来源已还原: {ok}/{len(origins)}")

        verify = ctx.cookies("https://www.linkedin.com")
        names = {c.get("name") for c in verify}
        print(f"li_at: {'有 ✅' if 'li_at' in names else '无 ❌（导入可能失败，请改用 VNC 登录）'}")
        print("完成。建议立即跑一轮验证：sudo bash /usr/local/bin/linkedin-run.sh")
    finally:
        ctx.close()
        pw.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
