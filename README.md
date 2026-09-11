# LinkedIn Auto Apply - 自动发简历系统

> **纯规则引擎，0 LLM 依赖**，基于 Playwright 的 LinkedIn Easy Apply 全自动投递系统。

## ✨ 特性

- **纯规则引擎** - 无需 LLM，答案引擎自动填写表单（年限/薪资/语言/签证/学历/是否授权工作等）
- **持久化 Chrome Profile** - 登录一次，会话+指纹+localStorage 全部持久化，彻底解决会话被吊销问题
- **智能限速** - 岗位间随机间隔 30-90s，每 5 个岗位强制长休 5-10 分钟，模拟人类节奏
- **每日上限检测** - 自动识别"今日申请上限"弹窗并优雅停止
- **网络容错** - 搜索/导航失败自动重试，单岗位异常不终止整批
- **去重机制** - 基于 Job ID + 历史记录，避免重复投递
- **Windows 计划任务** - 每 4 小时自动运行，时间窗口 8:00-22:00
- **0 LLM 成本** - 无需 API Key，本地纯规则运行

## 🚀 快速开始

### 1. 环境准备
```bash
# Windows 10/11，Python 3.11+
git clone https://github.com/xiaolin-bot/linkedin-auto.git
cd linkedin-auto

# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -e .
playwright install chromium
```

### 2. 配置
```bash
# 复制配置模板
copy .env.example .env
copy config.yaml.example config.yaml  # 如有

# 编辑 .env 填入必要信息（如需通知推送）
# 编辑 config.yaml：
#   - resume.path: 你的简历 PDF 路径
#   - answers.*: 你的个人信息（年限/薪资/语言/签证/学历等）
```

### 3. 首次登录（必须）
```bash
# 启动浏览器手动登录 LinkedIn 个人账号
python -X utf8 login_linkedin.py

# 浏览器会弹出，完成登录后脚本自动保存会话到 data/linkedin_profile/
# 后续所有运行复用同一 profile，无需重复登录
```

### 4. 测试投递
```bash
# 手动跑一轮（最多 2 个岗位，间隔 30-45s）
python -X utf8 run_linkedin_auto.py --max-jobs 2 --sleep-range 30,45 --no-login-prompt

# 或直接运行 CLI
python -m linkedin.cli run --keywords "AI sales,SaaS sales" --max-jobs 5
```

### 5. 设置自动运行（可选）
```bash
# 注册 Windows 计划任务（每 4 小时，8:00-22:00）
setup_task.bat

# 或手动运行
python -X utf8 run_linkedin_auto.py
```

## 📁 项目结构

```
linkedin-auto/
├── src/
│   └── linkedin/
│       ├── __init__.py
│       ├── models.py       # 数据模型
│       ├── browser.py      # 浏览器封装（持久 profile）
│       ├── answers.py      # 答案引擎（0 LLM）
│       ├── apply.py        # 投递状态机
│       ├── runner.py       # 批量跑逻辑
│       ├── filter.py       # 过滤规则
│       └── cli.py          # 命令行入口
├── login_linkedin.py       # 登录脚本
├── run_linkedin_auto.py    # 调度脚本
├── fix_linkedin_session.py # 会话修复工具
├── config.yaml             # 配置文件
├── .env.example            # 环境变量模板
├── pyproject.toml
├── README.md
└── setup_task.bat          # 注册计划任务
```

## ⚙️ 核心配置说明

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| `limits.max_jobs_per_run` | 每轮投递上限 | 10 |
| `limits.max_jobs_per_day` | 每日投递上限 | 40 |
| `limits.min/max_interval_seconds` | 岗位间隔 | 30-90s |
| `limits.break_every` | 长休频率 | 每 5 个 |
| `browser.profile_dir` | 持久 profile 目录 | `data/linkedin_profile` |
| `answers.years_experience` | 工作年限 | 你的实际年限 |
| `answers.expected_salary_year` | 期望年薪 | 你的预期 |
| `answers.visa_status` | 签证状态 | `permanent_resident`/`citizen`/etc |

## 🔧 常用命令

```bash
# 手动跑一轮
python -X utf8 run_linkedin_auto.py

# 指定关键词和数量
python -m linkedin.cli run --keywords "AI sales,pre-sales" --max-jobs 5

# 仅登录
python -X utf8 login_linkedin.py

# 修复会话 cookie 域
python -X utf8 fix_linkedin_session.py

# 查看投递历史
python -m linkedin.cli history
```

## ⚠️ 注意事项

1. **LinkedIn 用户协议** - 自动化访问可能违反协议，存在封号风险，**请自行评估并承担后果**
2. **建议使用小号测试** - 先用非主力账号验证流程
3. **薪资单位** - 根据职位货币自动判断（港币/人民币/美元），建议填写年薪
4. **简历格式** - 必须为 PDF，建议单页，文件名无中文
5. **网络环境** - 需直连 LinkedIn，代理/VPN 可能导致验证码频发
6. **Profile 目录** - `data/linkedin_profile` 包含登录态，**切勿删除**，迁移时需整体复制

## 📊 监控与日志

- 投递记录：`data/linkedin_runs/run_YYYYMMDD_HHMMSS.json`
- 调度日志：`data/linkedin_schedule/linkedin_YYYYMMDD.log`
- 运行日志：控制台输出 + `config.yaml` 中配置的日志文件

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

**免责声明**：本项目仅供学习研究使用，使用者需自行承担因自动化操作导致的账号封禁、法律风险等后果。请遵守 LinkedIn 用户协议及当地法律法规。