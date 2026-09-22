"""LinkedIn 定时投递调度：时间窗口 + 关键词轮换 + 日志。

由 setup_task.bat / 计划任务 linkedin-auto 调用。
直接运行：python -X utf8 run_linkedin_auto.py

数据目录解析顺序（保持原有部署可用）：
  1. 环境变量 LINKEDIN_DATA_DIR
  2. C:/freelance-auto/data（若存在，兼容旧部署的登录 profile）
  3. 本项目 ./data
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "src"))

_legacy = Path("C:/freelance-auto/data")
if os.environ.get("LINKEDIN_DATA_DIR"):
    DATA_DIR = Path(os.environ["LINKEDIN_DATA_DIR"])
elif _legacy.exists():
    DATA_DIR = _legacy
else:
    DATA_DIR = BASE / "data"

os.environ.setdefault("LINKEDIN_DATA_DIR", str(DATA_DIR))

from linkedin.runner import main as runner_main  # noqa: E402

LOG_DIR = DATA_DIR / "linkedin_schedule"
KEYWORDS = [
    "AI product", "AI solution consultant", "SaaS sales", "AI sales",
    "AI business development", "technical sales", "AI automation",
    "Education manager", "AI implementation", "Solution consultant",
]


def log(path: Path, msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / f"linkedin_{datetime.now().strftime('%Y%m%d')}.log"

    # 时间窗口
    hour = datetime.now().hour
    if hour < 8 or hour >= 22:
        log(logfile, f"非执行窗口（{hour}点），跳过")
        return 0

    # 日志轮转（14 天）
    now = time.time()
    for f in LOG_DIR.glob("linkedin_*.log"):
        try:
            if now - f.stat().st_mtime > 14 * 86400:
                f.unlink()
        except OSError:
            pass

    # 关键词轮换（按日期）
    day = int(datetime.now().strftime("%Y%m%d"))
    k1 = KEYWORDS[day % len(KEYWORDS)]
    k2 = KEYWORDS[(day + 3) % len(KEYWORDS)]
    kw = f"{k1},{k2}"
    log(logfile, f"关键词: {kw} | 每轮 10 岗 | 岗位间隔 30-90s | 每5个长休6-9min")

    # 调 runner（直接传 argv，不经过 subprocess 引号问题）
    argv = [
        "--keywords", kw,
        "--location", "Hong Kong",
        "--max-jobs", "10",
        "--sleep-range", "30,90",
        "--break-every", "5",
        "--break-range", "360,540",
        "--login-timeout", "240",
        "--no-login-prompt",
    ]
    try:
        rc = runner_main(argv)
    except Exception as e:  # noqa: BLE001
        log(logfile, f"异常: {e}")
        rc = 1
    log(logfile, f"本轮结束 rc={rc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
