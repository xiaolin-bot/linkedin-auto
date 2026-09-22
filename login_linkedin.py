"""LinkedIn 登录 - 持久 Chrome profile（会话+指纹全保留）

用 launch_persistent_context(profile_dir) 登录一次，之后所有运行复用
同一 profile：cookie、localStorage、指纹全部持久化，
避免每次冷启动被 LinkedIn 判定"新设备"而吊销 li_at。

运行（本机/服务器通用）：python login_linkedin.py
服务器无桌面时：先跑 deploy/login-vnc.sh 再通过 VNC 操作（见 deploy/README.md）

数据目录解析顺序（可用环境变量 LINKEDIN_DATA_DIR 覆盖）：
  1. LINKEDIN_DATA_DIR
  2. C:/freelance-auto/data（若存在，兼容旧部署）
  3. 本项目 ./data
"""
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = Path(__file__).resolve().parent
if os.environ.get("LINKEDIN_DATA_DIR"):
    DATA_DIR = Path(os.environ["LINKEDIN_DATA_DIR"])
elif Path("C:/freelance-auto/data").exists():
    DATA_DIR = Path("C:/freelance-auto/data")
else:
    DATA_DIR = BASE / "data"
os.environ.setdefault("LINKEDIN_DATA_DIR", str(DATA_DIR))
PROFILE_DIR = DATA_DIR / "linkedin_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

_CHANNEL = (os.environ.get("LINKEDIN_CHANNEL") or "chrome").strip() or "chrome"
_LAUNCH_ARGS = [
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
]
if os.environ.get("LINKEDIN_NO_SANDBOX") == "1":
    _LAUNCH_ARGS.append("--no-sandbox")  # 云服务器 root 环境必需


def _launch(p):
    """channel 回退：chrome → 自带 chromium（服务器没装 Chrome 也能用）。"""
    channels = [None] if _CHANNEL == "chromium" else [_CHANNEL, None]
    last_err = None
    for ch in channels:
        try:
            kwargs = {
                "user_data_dir": str(PROFILE_DIR),
                "headless": False,
                "args": _LAUNCH_ARGS,
                "viewport": None,
            }
            if ch:
                kwargs["channel"] = ch
            ctx = p.chromium.launch_persistent_context(**kwargs)
            print(f"浏览器启动 (channel={ch or 'bundled-chromium'})")
            return ctx
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"channel={ch or 'bundled-chromium'} 启动失败: {str(e)[:100]}")
    raise RuntimeError(f"浏览器启动失败: {last_err}")


p = sync_playwright().start()
ctx = _launch(p)
page = ctx.new_page()

page.add_init_script("""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;
window.chrome = {runtime: {}};
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
""")

print("打开 LinkedIn 个人版登录页...")
page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
time.sleep(3)
# 若被重定向到企业/非登录页，强制回个人登录页
if "/login" not in page.url:
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
print(f"页面: {page.title()}  URL: {page.url}")
print("请在浏览器中手动登录 LinkedIn【个人账号】")
print("登录完成后脚本会自动检测并保存会话（最多等5分钟）")

for i in range(180):
    time.sleep(2)
    try:
        t = page.title()
        u = page.url
        # 成功条件：URL 不含 authwall/checkpoint/challenge 且标题不是登录页
        login_page = any(k in t for k in ("登录", "Sign in", "Log in", "登录或注册", "Join now"))
        blocked = any(k in u for k in ("authwall", "checkpoint", "challenge", "security", "login"))
        if not login_page and not blocked:
            print(f"\n✅ 检测到登录完成 ({i*2}秒)，跳转 /feed/ 验证...")
            try:
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
            except Exception:  # noqa: BLE001
                pass
            t = page.title()
            u = page.url
            if "/feed/" in u and not any(k in t for k in ("登录", "Sign in")):
                print(f"标题: {t}")
                print(f"URL: {u}")
                break
            # 未进 feed 则继续等
            print(f"验证未通过，仍在: {u[:80]}，继续等待...")
    except Exception:  # noqa: BLE001
        pass
else:
    print("等待超时")
    print(f"最终标题: {page.title()}")
    print(f"最终URL: {page.url}")

# 校验 li_at cookie（个人版登录核心令牌）是否真的存在
for check in range(30):
    try:
        cookies = ctx.cookies()
        names = [c.get("name") for c in cookies if "linkedin" in (c.get("domain") or "")]
        if "li_at" in names:
            print(f"✅ 检测到 li_at 会话令牌 (第{check+1}次轮询)")
            break
    except Exception:  # noqa: BLE001
        pass
    time.sleep(2)
else:
    print("⚠️ 未检测到 li_at cookie，可能仍在挑战页")

print(f"登录态已持久化于 profile: {PROFILE_DIR}")
time.sleep(3)
ctx.close()
p.stop()
print("完成")
