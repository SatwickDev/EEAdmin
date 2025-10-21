@echo off
echo Starting ChromaDB server...
start "ChromaDB" cmd /k "chroma run --host 0.0.0.0 --port 8000"

echo Waiting for ChromaDB to start...
timeout /t 5 /nobreak >nul

echo Starting Flask application on port 80...
start "Flask App" cmd /k "cd /d %~dp0 && py run.py"

echo Both services are starting...
echo ChromaDB: http://localhost:8000
echo Flask App: http://localhost:80
pause