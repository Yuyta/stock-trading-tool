@echo off
echo === Stock Analyzer Backend Setup ===
echo.
echo [1/3] Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo [3/3] Starting backend server...
uvicorn main:app --reload --port 8000

pause
