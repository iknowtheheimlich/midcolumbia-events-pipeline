@echo off
setlocal

set CITY=richland-wa
set PROFILE_DIR=browser_profile
set START_URL=https://allevents.in/richland-wa/all

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

python -m cargo_harvester.interactive --city %CITY% --start %START% --end %END% --output output --profile-dir %PROFILE_DIR% --url %START_URL%
pause
