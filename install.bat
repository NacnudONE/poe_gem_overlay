@echo off
echo ================================================
echo   PoE Gem Overlay - Install dependencies
echo ================================================
echo.

python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Installing libraries...
pip install -r requirements.txt

echo.
echo Checking setup...
python setup_check.py

echo.
pause
