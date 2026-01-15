@echo off
REM 安装项目依赖的批处理脚本
echo 正在安装项目依赖...
echo.

REM 尝试使用python命令
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 使用python命令失败，尝试使用完整路径...
    REM 尝试使用完整路径（Windows Store Python）
    C:\Users\zhenx\AppData\Local\Microsoft\WindowsApps\python.exe -m pip install -r requirements.txt
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo 依赖安装完成！
    echo ========================================
) else (
    echo.
    echo ========================================
    echo 安装失败，请检查：
    echo 1. Python是否正确安装
    echo 2. pip是否可用
    echo 3. 网络连接是否正常
    echo ========================================
    pause
)
