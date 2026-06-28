@echo off
setlocal

set PYTHONPATH=src
python -m unittest discover -s tests -p "test_*.py"
pause
