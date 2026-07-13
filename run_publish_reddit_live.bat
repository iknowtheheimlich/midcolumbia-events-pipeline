@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo Usage: run_publish_reddit_live.bat YYYY-MM-DD [publisher options]
  exit /b 2
)

python -m tools.publish_reddit_live --week-start %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%
