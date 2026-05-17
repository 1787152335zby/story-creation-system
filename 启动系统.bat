@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ================================================
echo       🎬 多智能体故事创作系统 - 一键启动
echo ================================================
echo.

:: 检测 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python！
    echo 请从 https://www.python.org/downloads/ 安装 Python 3.10+
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "delims=" %%i in ('python --version 2^>^&1') do echo %%i

:: 运行环境检测与自动安装（已有则跳过）
echo.
echo 🔧 正在检测运行环境（已有则跳过）...
python setup_env.py

:: 启动 Web 服务
echo.
echo 🚀 正在启动 Web 服务...
echo.
echo    Web 界面: http://localhost:8000
echo    CLI 模式: python main.py
echo.
start "" http://localhost:8000
python run_web.py

pause
