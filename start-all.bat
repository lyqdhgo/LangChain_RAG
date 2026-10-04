@echo off
chcp 65001 >nul
title 企业知识库问答系统 - 一键启动

REM ============================================================================
REM  企业知识库问答系统 一键启动脚本
REM
REM  会依次启动三个服务，每个服务各占一个窗口：
REM    1. MySQL      端口 3308
REM    2. Flask 后端 端口 5000
REM    3. Vue 前端   端口 5173（启动后自动打开浏览器）
REM
REM  使用前请确认：
REM    - 已执行过 sql/db_enterprise_qa.sql 初始化数据库
REM    - Ollama 已启动（Ollama 安装后会自动常驻，一般无需手动启动）
REM ============================================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   企业知识库问答系统 - 正在启动
echo ============================================================
echo.

REM ---------- 1. 启动 MySQL ----------
netstat -ano | findstr ":3308 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo [1/3] MySQL      已在运行，跳过
) else (
    echo [1/3] MySQL      正在启动...
    start "MySQL-3308" cmd /k "%~dp0start-mysql.bat"
    REM 等待数据库就绪，避免后端启动时连不上
    timeout /t 8 /nobreak >nul
)

REM ---------- 2. 启动 Flask 后端 ----------
echo [2/3] Flask 后端 正在启动...
start "Flask-5000" cmd /k "cd /d %~dp0server && python app.py"
timeout /t 6 /nobreak >nul

REM ---------- 3. 启动 Vue 前端 ----------
echo [3/3] Vue 前端   正在启动...
start "Vue-5173" cmd /k "cd /d %~dp0client && npm run dev"
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo   启动完成
echo.
echo   前端地址：http://localhost:5173
echo   后端地址：http://127.0.0.1:5000
echo   健康检查：http://127.0.0.1:5000/api/health
echo.
echo   测试账号：admin / 123456   （管理员）
echo             zhangsan / 123456（普通用户）
echo.
echo   停止服务：关闭对应的三个命令行窗口即可
echo ============================================================
echo.
pause
