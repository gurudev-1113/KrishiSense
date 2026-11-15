@echo off
title KrishiSense Server
echo ===================================================
echo Starting KrishiSense Agricultural DSS Server...
echo ===================================================
set "PATH=C:\Users\GURUDEV\AppData\Local\Programs\Python\Python314;C:\Users\GURUDEV\AppData\Local\Programs\Python\Python314\Scripts;%PATH%"
python app.py
if errorlevel 1 (
    echo.
    echo Fallback: trying direct python path...
    "C:\Users\GURUDEV\AppData\Local\Programs\Python\Python314\python.exe" app.py
)
pause
