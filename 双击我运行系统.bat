@echo off
title 盲水印版权保护系统 - 启动程序

echo ==========================================
echo       盲水印版权保护系统 - 环境初始化
echo ==========================================

:: 1. 检测并创建虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [1/4] 未检测到虚拟环境，正在创建 venv...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请确保已安装 Python 3。
        pause
        exit /b
    )
) else (
    echo [1/4] 虚拟环境已存在，跳过创建。
)

:: 2. 激活虚拟环境
echo [2/4] 正在激活虚拟环境...
call venv\Scripts\activate.bat

:: 3. 安装依赖 (使用清华源)
echo [3/4] 正在检查并安装依赖包 (使用清华源加速)...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接。
    pause
    exit /b
)

:: 4. 启动 Streamlit
echo [4/4] 正在启动 Web 前端...
echo 请不要关闭此黑框窗口！
streamlit run app.py

pause
