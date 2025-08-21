@echo off
cd /d "%~dp0"

echo [%date% %time%] BirdNET解析開始

REM 仮想環境をアクティベート
if exist "venv\Scripts\activate.bat" (
    echo 仮想環境をアクティベート中...
    call venv\Scripts\activate.bat
)

REM 解析実行
python main.py --auto --action analyze --model custom_model_1

echo [%date% %time%] 解析完了 (終了コード: %ERRORLEVEL%)