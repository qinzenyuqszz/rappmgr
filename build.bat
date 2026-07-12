@echo off
REM RAPPS Build Script
REM Usage: build.bat [onefile|onedir|all]

set BUILD_TYPE=%1
if "%BUILD_TYPE%"=="" set BUILD_TYPE=all

echo ============================================
echo   RAPPS Build Script
echo ============================================
echo.

REM Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo.

if "%BUILD_TYPE%"=="onefile" goto onefile
if "%BUILD_TYPE%"=="onedir" goto onedir

:onefile
echo [2/3] Building onefile (single exe)...
pyinstaller --name RAPPS --onefile --windowed --noconfirm --clean --add-data "rapps;rapps" rapps/main.py
echo Done: dist\RAPPS.exe
echo.
goto end

:onedir
echo [2/3] Building onedir (folder)...
pyinstaller --name RAPPS --onedir --windowed --noconfirm --clean --add-data "rapps;rapps" rapps/main.py
echo Done: dist\RAPPS\
echo.
goto end

:end
echo [3/3] Build complete!
echo.
pause
