@echo off
REM 1. 切换CMD编码为UTF-8（隐藏切换提示）
chcp 65001 > nul

REM 2. 强制切换到脚本所在目录（解决路径问题）
cd /d %~dp0

REM 3. 检查Python是否可用（避免因环境变量报错）
where python > nul 2>&1
if %errorlevel% neq 0 (
    echo [91m错误：未找到Python环境！[0m
    echo 请确保：
    echo  1. 已安装Python 3.8+
    echo  2. 已勾选"Add Python to PATH"
    pause
    exit /b 1
)

REM 4. 友好提示（确保UTF-8下中文正常）
echo [96m正在使用命令行环境运行脚本...[0m

REM 5. 执行Python脚本（若有虚拟环境，可替换为虚拟环境路径）
python mod_comparator.py

REM 6. 防止闪退
pause