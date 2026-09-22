#!/usr/bin/env python3
"""导出本机 LinkedIn 登录态 → storage_state JSON（免 VNC 备用方案的「导出」端）。

用途：在 Windows 本机执行，把当前持久 profile 的登录态（cookie + localStorage）
      导出成一个 JSON；再把它传到服务器，用 import-login-server.py 导入。
      这样服务器无需 VNC 手动登录（但稳定性不如 VNC 登录，见 deploy/README.md 第 9 节）。

用法（在有登录态的本机执行）：
    python -X utf8 deploy/export-login-windows.py
    python -X utf8 deploy/export-login-windows.py --out D:\\linkedin_state.json

⚠️ 安全：输出文件包含登录凭据（li_at），用完请删除，切勿提交到 git / 发给他人。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
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
    ap = argparse.ArgumentParser(description="导出 LinkedIn 登录态为 storage_state JSON")
    ap.add_argument("--profile", default="", help="持久 profile 目录（默认自动探测）")
    ap.add_argument("--out", default="linkedin_state.json", help="输出文件路径")
    args = ap.parse_args()

    profile = Path(args.profile) if args.profile else resolve_data_dir() / "linkedin_profile"
    if not profile.exists():
        return sys.exit(f"profile 不存在（先从本机登录过吗？）: {profile}")

    print(f"profile: {profile}")
    pw = sync_playwright().start()
    ctx = launch(pw, profile, headless=True)
    try:
        # 先真实访问一次 LinkedIn：storage_state 只会捕获本次会话访问过的 origin 的
        # localStorage，不访问会导出 0 条（设备指纹状态丢失）
        page = ctx.new_page()
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
        except Exception as e:  # noqa: BLE001
            print(f"提示: 访问 LinkedIn 失败({str(e)[:60]})，将只导出 cookie")
        finally:
            page.close()

        cookies = ctx.cookies("https://www.linkedin.com")
        names = {c.get("name") for c in cookies}
        if "li_at" not in names:
            print("⚠️ 未发现 li_at cookie —— 本机登录态可能已失效，请先重新登录再导出")
        state = ctx.storage_state()
        out = Path(args.out)
        out.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        origins = state.get("origins", [])
        print(f"✅ 已导出: {out}")
        print(f"   cookie 数: {len(state.get('cookies', []))}（li_at: {'有' if 'li_at' in names else '无'}）")
        print(f"   localStorage 来源数: {len(origins)}")
        print("   下一步: 把该文件传到服务器，然后运行 python -X utf8 deploy/import-login-server.py --state <文件>")
        print("   ⚠️ 用完请删除该文件（含登录凭据）")
    finally:
        ctx.close()
        pw.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
