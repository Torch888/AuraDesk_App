@echo off
REM AuraDesk 启动脚本 (Windows)

echo ================================
echo   AuraDesk - AI 桌面生活助手
echo ================================
echo.

REM 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未安装 Node.js
    echo 请访问 https://nodejs.org 下载安装
    pause
    exit /b 1
)

REM 检查依赖
if not exist "node_modules" (
    echo 首次运行，正在安装依赖...
    npm install
    echo.
)

echo 选择启动模式：
echo   1^) 仅桌面助手（推荐）
echo   2^) 桌面助手 + 云端后端
echo.
set /p choice="请输入选项 [1]: "

if "%choice%"=="2" (
    echo.
    echo 启动云端后端...
    start /b npm run cloud
    timeout /t 2 >nul
    
    echo 启动桌面助手...
    set AURADESK_CLOUD_URL=http://127.0.0.1:8787
    set AURADESK_CLOUD_TOKEN=***
    npm start
) else (
    echo.
    echo 启动桌面助手...
    npm start
)

pause
