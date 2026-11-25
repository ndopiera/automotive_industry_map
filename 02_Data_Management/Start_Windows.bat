@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto end
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto end
.venv\Scripts\python -m streamlit run app.py --server.address localhost
:end
pause
