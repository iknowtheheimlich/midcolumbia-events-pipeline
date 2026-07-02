@echo off
setlocal

set CARGO_CHROME_PROFILE=%USERPROFILE%\CargoChromeProfile
set CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe

if not exist "%CHROME_EXE%" (
  set CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
)

if not exist "%CHROME_EXE%" (
  echo Could not find Chrome.exe in the usual locations.
  echo Open Chrome manually with --remote-debugging-port=9222 if needed.
  pause
  exit /b 1
)

echo Starting Chrome for Cargo Harvester...
echo Profile: %CARGO_CHROME_PROFILE%
start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%CARGO_CHROME_PROFILE%" https://allevents.in/
