@echo off
setlocal

echo Cargo Harvester Foundation Validation
echo -------------------------------------
echo.

echo [1/3] Running setup...
call setup_windows.bat
IF ERRORLEVEL 1 (
  echo Setup failed.
  pause
  exit /b 1
)

echo.
echo [2/3] Running tests...
call run_tests.bat
IF ERRORLEVEL 1 (
  echo Tests failed.
  pause
  exit /b 1
)

echo.
echo [3/3] Running visible persistent-profile harvest...
call run_harvester_visible_profile.bat
IF ERRORLEVEL 1 (
  echo Harvest failed.
  pause
  exit /b 1
)

echo.
echo Validation complete.
echo Check output\unified_events.csv and output\reddit_weekly_draft.md.
pause
