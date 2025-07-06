@echo off
chcp 65001 > nul
echo ========================================
echo BirdNet-Colab Windows Setup
echo ========================================
echo.

REM Create Python virtual environment
echo [1/5] Creating Python virtual environment...
if exist "venv" (
    echo Virtual environment already exists. Skipping.
) else (
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment.
        echo Please make sure Python is installed.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install required packages
echo [3/5] Installing required packages...
echo This may take several minutes...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install packages.
    echo Please check your internet connection.
    pause
    exit /b 1
)

REM Create directory structure
echo [4/5] Creating directory structure...
if not exist "data" mkdir data
if not exist "data\audio" mkdir data\audio
if not exist "data\audio\raw" mkdir data\audio\raw
if not exist "data\audio\raw\Northern_Goshawk" mkdir data\audio\raw\Northern_Goshawk
if not exist "data\audio\raw\Gray-faced_Buzzard" mkdir data\audio\raw\Gray-faced_Buzzard
if not exist "data\audio\raw\Japanese_Night_Heron" mkdir data\audio\raw\Japanese_Night_Heron
if not exist "data\audio\raw\Ural_Owl" mkdir data\audio\raw\Ural_Owl
if not exist "data\audio\raw\Gray_Nightjar" mkdir data\audio\raw\Gray_Nightjar
if not exist "data\audio\extracted" mkdir data\audio\extracted
if not exist "data\audio\test" mkdir data\audio\test
if not exist "data\audio\train" mkdir data\audio\train
if not exist "data\audio\extracted_spectrogram" mkdir data\audio\extracted_spectrogram
if not exist "model" mkdir model

REM Create environment variable setup file
echo [5/5] Creating environment setup file...
echo @echo off > set_env.bat
echo set PROJECT_PATH=%CD% >> set_env.bat
echo set SPECIES_FILE=%CD%\lib\species1.json >> set_env.bat
echo set SPECIES_COLUMN=species1 >> set_env.bat
echo set PYTHONPATH=%CD%\lib;%%PYTHONPATH%% >> set_env.bat
echo echo Environment variables set. >> set_env.bat

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Place audio files in data\audio\test\
echo 2. Run: start_analysis.bat
echo.
echo For troubleshooting, see README.md
echo.
pause
