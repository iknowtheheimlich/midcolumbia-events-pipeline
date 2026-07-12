@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo Usage: run_publish_reddit_live.bat YYYY-MM-DD
  exit /b 2
)

python -m tools.publish_reddit_live --week-start %1
endlocal
