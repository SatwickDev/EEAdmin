@echo off
echo ========================================
echo   FinStack HTTPS Setup
echo ========================================
echo.

echo Step 1: Installing pyOpenSSL...
pip install pyOpenSSL

echo.
echo Step 2: Generating SSL certificate...
python generate_cert.py

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To start the HTTPS server, run:
echo   python run.py
echo.
echo Then access at: https://localhost:5000
echo.
pause
