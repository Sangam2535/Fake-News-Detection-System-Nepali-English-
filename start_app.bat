@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting Flask backend...
start cmd /k "cd server && call ..\venv\Scripts\activate.bat && python l_app.py"

timeout /t 3 >nul

echo.
echo Starting frontend on http://localhost:8000 ...
start cmd /k "cd frontend && python -m http.server 8000"
update this as well 