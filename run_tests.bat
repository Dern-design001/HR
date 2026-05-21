@echo off
echo Running HR Interview Simulator Tests...
echo.
cd /d "%~dp0"
python -m pytest tests/ -v --tb=short
pause
