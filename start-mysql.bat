@echo off
chcp 65001 >nul
title MySQL 8.4 (端口 3308)

REM ============================================================================
REM  启动 MySQL 8.4（端口 3308）
REM
REM  说明：安装 MySQL 时当前账户没有管理员权限，无法注册成 Windows 服务，
REM        因此需要每次开机后手动运行本脚本启动数据库。
REM        如需开机自启，请用管理员身份执行：
REM          "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" ^
REM              --install MySQL84 --defaults-file="C:\ProgramData\MySQL\my.ini"
REM ============================================================================

set MYSQL_HOME=C:\Program Files\MySQL\MySQL Server 8.4
set MYSQL_INI=C:\ProgramData\MySQL\my.ini

echo.
echo ============================================================
echo   正在启动 MySQL 8.4（端口 3308）
echo   数据目录：C:\ProgramData\MySQL\data
echo   关闭本窗口即停止数据库
echo ============================================================
echo.

REM 先检查端口是否已被占用，避免重复启动
netstat -ano | findstr ":3308 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo [提示] 3308 端口已在监听，MySQL 可能已经启动了。
    echo        无需重复启动，直接按任意键退出。
    pause >nul
    exit /b 0
)

REM 以前台控制台方式运行，日志直接打印在本窗口
"%MYSQL_HOME%\bin\mysqld.exe" --defaults-file="%MYSQL_INI%" --console

echo.
echo [提示] MySQL 已退出。
pause
