@echo off
setlocal

set CITY=richland-wa
set JSON_DIR=input_json
set PROFILE_DIR=browser_profile

if "%1"=="" (
  set /p START=Start date YYYY-MM-DD: 
) else (
  set START=%1
)

if "%2"=="" (
  set /p END=End date YYYY-MM-DD: 
) else (
  set END=%2
)

python -m cargo_harvester.cli --city %CITY% --start %START% --end %END% --output output --browser-json %JSON_DIR% --visible --debug --profile-dir %PROFILE_DIR%
pause
