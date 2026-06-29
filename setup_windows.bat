@echo off
setlocal

echo Mid-Columbia Events Pipeline - Windows Setup
echo -------------------------------------------

python --version
IF ERRORLEVEL 1 (
  echo Python was not found. Install Python 3.13 if possible.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python -m playwright install chromium

echo.
echo Setup complete.
echo Run: run_harvester.bat 2026-07-01 2026-07-07
pause
