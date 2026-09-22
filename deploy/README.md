# 云端部署指南（7×24 不间断投递）

把自动投递系统部署到云服务器后，**你电脑锁屏、休眠、关机都不影响投递**。

---

## 1. 服务器怎么选

| 项目 | 推荐 | 说明 |
|------|------|------|
| 厂商 | 腾讯云 / 阿里云 **轻量应用服务器** | 中文控制台、微信/支付宝付款 |
| 区域 | **香港**（首选）或新加坡 | 服务器需能直连 linkedin.com；香港延迟低 |
| 配置 | 2 核 2G 起（2 核 4G 更稳） | Chrome + xvfb 吃内存，2G 建议加 1G swap |
| 系统 | **Ubuntu 22.04 / 24.04** | 部署脚本按此编写 |
| 带宽 | 按量/1M 即可 | 流量很小（只有浏览器交互） |
| 费用 | 约 ¥30-50/月（24 元-40 元档轻量） | 新用户常有活动 |

**免费方案**：
- 🆓 **Oracle Cloud 永久免费**（4核24G ARM）：→ 完整攻略见 [oracle-free-tier.md](oracle-free-tier.md)
- 🆓 腾讯云/阿里云**新用户免费试用**（1-3 个月，到期再决定）
- ❌ 不推荐 GitHub Actions 等免费 CI：每次运行换机器换 IP → LinkedIn 会话必被吊销

> ⚠️ 大陆区域（北京/上海/广州）机器**访问不了 LinkedIn**，必须选**香港/海外**区域。

---

## 2. 一键部署

### 方式 A（推荐）：从 Windows 一条命令远程部署（密钥免密）

前置：把部署公钥粘贴到服务器（Oracle 建实例时可直接粘贴，见
[oracle-free-tier.md](oracle-free-tier.md) 第 3 步）。

```powershell
cd C:\linkedin-auto
powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1 -Server <服务器IP>
# 非 Oracle / root 用户的服务器：
powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1 -Server <IP> -User root
```

该脚本自动完成：连接测试 → 拉代码 → 安装（依赖/时区/Chrome/xvfb/systemd）→
上传简历 → 迁移投递历史（去重）→ 验证，并打印最后的 VNC 登录指引。

### 方式 B：手动在服务器上执行

```bash
# 1) SSH 登录服务器（Windows PowerShell 直接可用）
ssh root@<服务器IP>          # Oracle Ubuntu 默认用户是 ubuntu

# 2) 拉代码并安装（幂等，可重复执行）
git clone https://github.com/xiaolin-bot/linkedin-auto.git /opt/linkedin-auto
sudo bash /opt/linkedin-auto/deploy/install.sh
```

脚本会自动完成：系统依赖 → 时区(香港) → Chrome（失败自动回退 Chromium）→ 项目代码 →
Python 依赖 → xvfb/VNC → systemd 服务与定时器（每天 8/12/16/20 点，±5 分钟随机抖动）。

### 迁移 简历 + 投递历史（方式 B 使用）

```powershell
cd C:\linkedin-auto
powershell -ExecutionPolicy Bypass -File deploy\push-from-windows.ps1 -Server root@<服务器IP>
```

---

## 4. 一次性登录 LinkedIn（VNC 方式）

服务器没有桌面，用 VNC 远程操作浏览器完成登录：

```bash
# 在服务器 SSH 里执行：
bash /opt/linkedin-auto/deploy/login-vnc.sh
```

按屏幕提示：

1. **Windows 上开 SSH 隧道**（新的 PowerShell 窗口）：
   ```powershell
   # 一键脚本（用部署密钥，Oracle 默认用户 ubuntu）
   powershell -ExecutionPolicy Bypass -File deploy\open-vnc-tunnel.ps1 -Server <服务器IP>
   # 或手动（密码方式）
   ssh -N -L 5900:localhost:5900 root@<服务器IP>
   ```
2. **安装 VNC Viewer**（任选其一，免费）：
   - TightVNC Viewer: https://www.tightvnc.com/download.php
   - RealVNC Viewer: https://www.realvnc.com/download/viewer/
3. VNC Viewer 连接 `localhost:5900`（无密码）→ 看到 Chrome 窗口 → **手动登录 LinkedIn**
   （遇到验证码/邮箱验证按提示完成）
4. 登录成功后脚本自动保存会话（日志出现 `✅ 检测到 li_at 会话令牌`），SSH 终端按 `Ctrl+C` 退出。

> 登录态保存在服务器 `/opt/linkedin-auto/data/linkedin_profile/`，
> **不要删除该目录**；后续所有投递复用它，无需重复登录。

---

## 5. 启动定时投递

```bash
sudo systemctl start linkedin-auto.timer     # 启用
systemctl list-timers linkedin-auto.timer    # 查看下次运行时间

# 想立即手动跑一轮验证：
sudo bash /usr/local/bin/linkedin-run.sh
```

**验证成功的标志**（投递日志）：

```bash
cat /opt/linkedin-auto/data/linkedin_schedule/linkedin_$(date +%Y%m%d).log
# 出现 "投递成功: N" (N≥1) 即正常
ls /opt/linkedin-auto/data/linkedin_runs/     # 每轮生成 run_*.json
```

---

## 6. ⚠️ 重要：停用本机（Windows）计划任务

**两台机器同时跑会导致同一账号双端登录/重复投递 → 风控风险。**

服务器验证正常后，在你电脑上执行：

```powershell
schtasks /Delete /TN "linkedin-auto" /F
```

（freelance-auto 的接单任务不受影响，保持不动。）

---

## 7. 日常运维速查

| 操作 | 命令 |
|------|------|
| 查看下次运行 | `systemctl list-timers linkedin-auto.timer` |
| 查看最近日志 | `journalctl -u linkedin-auto.service -n 100 --no-pager` |
| 手动跑一轮 | `sudo bash /usr/local/bin/linkedin-run.sh` |
| 更新代码 | `cd /opt/linkedin-auto && git pull && sudo bash deploy/install.sh` |
| 暂停投递 | `sudo systemctl stop linkedin-auto.timer` |
| 恢复投递 | `sudo systemctl start linkedin-auto.timer` |
| 会话失效重登 | `bash /opt/linkedin-auto/deploy/login-vnc.sh`（同上第 4 步） |
| 换简历 | scp 覆盖 `/opt/linkedin-auto/resume/BendyLin_Resume0903.pdf` |

**改关键词/频率**：编辑 `/opt/linkedin-auto/run_linkedin_auto.py` 里的 `KEYWORDS` 和
`--max-jobs / --sleep-range / --break-range` 参数（改完无需重启，下轮生效）。

---

## 8. 风控须知

- **数据中心 IP 比家庭宽带更容易被判定自动化**：维持现有节奏（4 小时一轮、每轮 ≤10 岗、
  岗位间隔 30-90s、每 5 岗长休）不要再调快。
- 建议服务器上**只跑这一个账号**，不要多开。
- 若出现频繁验证码 / 登录态被吊销：暂停 1-2 天，降低频率（改 `--max-jobs 5`），
  或考虑给服务器挂住宅代理（`deploy/run.sh` 里加 `--proxy-server` 到 Chrome 参数）。
- 该账号已被 LinkedIn 风控过（历史会话吊销），云端首周请每天看一眼日志。

---

## 9. 备选：免 VNC 的 Cookie 迁移（不推荐首选）

先按第 4 节用 VNC 登录即可。如果有人实在无法使用 VNC，可改用「导出 Windows 端登录态
→ 服务器导入」的方案（需要专门的导出/导入脚本，联系我补上）。此方案触发 LinkedIn
"新设备"校验的概率更高，效果不如 VNC 登录稳定。

---

## 10. 备用：本机保活（暂不买服务器时用）

在云端就绪之前（或作为备份），可以用本机跑，但必须修掉 Windows 任务的两个隐藏坑：

| 坑 | 默认值 | 后果 |
|---|---|---|
| `DisallowStartIfOnBatteries` | True | 电池供电时**整轮跳过**（哪怕电脑醒着） |
| `StopIfGoingOnBatteries` | True | 跑到一半拔电 → 本轮被杀 |
| `StartWhenAvailable` | False | 睡眠期间错过的轮次**永久丢失** |
| `WakeToRun` | False | 睡眠中不会被执行 |

一键修复（**右键 → 以管理员身份运行**）：

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows-keep-awake.ps1
# 可选：插电时合盖不睡眠（部分游戏本由厂商电源管理接管，可能不生效）
powershell -ExecutionPolicy Bypass -File deploy\windows-keep-awake.ps1 -SetLidNoSleep
```

修好后的行为：**锁屏照跑**、拔电照跑、睡眠错过的轮次开机自动补跑、睡眠中到点可被唤醒执行。
唯一的硬限制：**关机时不跑**（要真正 7×24 还是得部署云服务器，见第 1-2 节）。
