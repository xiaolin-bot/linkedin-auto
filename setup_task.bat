@echo off
chcp 65001 >nul
title 注册 LinkedIn Auto 计划任务

:: 需管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

set PROJECT_DIR=%~dp0
set PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe
set SCRIPT=%PROJECT_DIR%run_linkedin_auto.py

if not exist "%PYTHON%" (
    echo 未找到虚拟环境: %PYTHON%
    echo 请先运行: python -m venv .venv && .venv\Scripts\pip install -e .
    pause
    exit /b 1
)

:: 删除旧任务
schtasks /Delete /TN "linkedin-auto" /F >nul 2>&1

:: 创建新任务：每 4 小时，8:00-22:00
schtasks /Create ^
    /TN "linkedin-auto" ^
    /TR "cmd /c cd /d \"%PROJECT_DIR%\" && \"%PYTHON%\" -X utf8 \"%SCRIPT%\"" ^
    /SC HOURLY /MO 4 ^
    /ST 08:00 ^
    /F

echo.
echo ✅ 计划任务已注册：linkedin-auto
echo    运行间隔：每 4 小时
echo    时间窗口：8:00 - 22:00
echo    工作目录：%PROJECT_DIR%
echo    Python：%PYTHON%
echo    脚本：%SCRIPT%
echo.
echo 下次运行时间：
schtasks /Query /TN "linkedin-auto" /FO LIST | findstr "下次运行"
echo.
pause