@echo off
chcp 65001 >nul
title LinkedIn Auto Apply

set PROJECT_DIR=%~dp0
set VENV_DIR=%PROJECT_DIR%.venv
set PYTHON=%VENV_DIR%\Scripts\python.exe

if not exist "%PYTHON%" (
    echo 创建虚拟环境...
    python -m venv .venv
    "%PYTHON%" -m pip install --upgrade pip
    "%PYTHON%" -m pip install -e .
    if errorlevel 1 (
        echo 依赖安装失败
        pause
        exit /b 1
    )
)

echo 启动投递...
"%PYTHON%" -X utf8 run_linkedin_auto.py --keywords "AI sales,SaaS sales,technical sales" --max-jobs 10 --sleep-range 30,90 --no-login-prompt

if errorlevel 1 (
    echo 投递异常退出
    pause
    exit /b 1
)

echo 投递完成