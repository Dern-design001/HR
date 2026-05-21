@echo off
echo Starting HR Interview Simulator Streamlit Frontend...
echo.
cd /d "%~dp0"
python -m streamlit run frontend/streamlit_app.py --server.port 8501
pause
