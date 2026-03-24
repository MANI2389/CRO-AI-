@echo off
echo ════════════════════════════════════════
echo   CRO v2.0  —  .EXE BUILD SCRIPT
echo ════════════════════════════════════════

echo.
echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Installing PyInstaller...
pip install pyinstaller

echo.
echo [3/3] Building .exe ...
pyinstaller --onefile --windowed --name="CRO_Assistant" --icon=NONE cro.py

echo.
echo ════════════════════════════════════════
echo   BUILD COMPLETE!
echo   Check:  dist\CRO_Assistant.exe
echo ════════════════════════════════════════
pause
