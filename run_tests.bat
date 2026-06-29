@echo off
setlocal

python -m unittest discover -s tests -p "test_*.py"
pause
