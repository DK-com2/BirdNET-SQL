@echo off
chcp 65001 > nul
echo ========================================
echo BirdNet Database Viewer (Streamlit)
echo ========================================
echo.

REM Check if in project directory
if not exist "streamlit_viewer" (
    echo ERROR: streamlit_viewer directory not found.
    echo Please run this script from the BirdNet-win root directory.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install/Update dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM Change to streamlit_viewer directory
cd streamlit_viewer

REM Start Streamlit application
echo.
echo ========================================
echo Starting BirdNet Database Viewer...
echo ========================================
echo.
echo The application will open in your web browser.
echo URL: http://localhost:8501
echo.
echo To stop the application, press Ctrl+C
echo.

streamlit run app.py

pause
