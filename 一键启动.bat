@echo off
setlocal enabledelayedexpansion
title 智能旅行助手 - 一键启动
cd /d "%~dp0"

echo ============================================================
echo   智能旅行助手 - 一键启动
echo ============================================================
echo.

:: ---------- 环境检查 ----------

if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境 .venv，请先创建。
    echo        运行: python -m venv .venv
    pause
    exit /b 1
)

if not exist "backend\run.py" (
    echo [错误] 未找到 backend\run.py，请确认目录结构。
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [错误] 未找到 frontend\package.json，请确认目录结构。
    pause
    exit /b 1
)

if not exist "backend\.env" (
    echo [警告] 未找到 backend\.env，如果已配置环境变量可忽略。
    echo        若未配置，请复制 backend\.env.example 为 .env 并填写密钥。
    echo.
)

:: ---------- 前端依赖检查 ----------

if not exist "frontend\node_modules" (
    echo [提示] 前端依赖未安装，正在自动安装...
    pushd "frontend"
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        popd
        pause
        exit /b 1
    )
    popd
    echo.
)

:: ---------- 端口占用检测并自动清理 ----------

echo [1/4] 检查端口占用...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8200 " ^| findstr "LISTENING"') do (
    echo       端口 8200 被占用，正在终止 PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    echo       端口 5173 被占用，正在终止 PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)
echo       端口检查完成
echo.

:: ---------- 启动服务 ----------

echo [2/4] 启动后端 (端口 8200)...
start "后端 - FastAPI" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && cd backend && python run.py"

echo [3/4] 启动前端 (端口 5173)...
start "前端 - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [4/4] 等待服务启动...
echo       后端首次启动需要初始化 MCP，可能需要 10-30 秒
echo       前端 Vite 启动约需 3-5 秒
echo.

timeout /t 8 /nobreak >nul

echo ============================================================
echo   启动完成！
echo.
echo   前端地址:  http://localhost:5173/
echo   后端API:   http://localhost:8200/docs
echo.
echo   两个终端窗口已打开，请勿关闭。
echo   首次生成旅行计划需 1-3 分钟（MCP初始化 + 4次LLM调用）。
echo ============================================================
echo.

start http://localhost:5173/

:: ---------- 菜单循环 ----------
:menu
echo ------------------------------------------------------------
echo  输入 S  - 停止所有服务并释放端口
echo  输入 Q  - 仅关闭本窗口（服务继续运行）
echo ------------------------------------------------------------
set /p choice="请选择: "

if /i "!choice!"=="S" goto stop
if /i "!choice!"=="Q" exit /b 0

echo 无效输入，请重新选择。
goto menu

:: ---------- 停止服务 ----------
:stop
echo.
echo 正在停止服务...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8200 " ^| findstr "LISTENING"') do (
    echo   终止端口 8200 的进程 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    echo   终止端口 5173 的进程 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo 已停止所有服务并释放端口。
echo.
pause
exit /b 0