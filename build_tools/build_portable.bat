@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".buildenv\Scripts\python.exe" (
    echo Environnement de construction introuvable.
    echo Cree-le avec Python 3.12 puis installe PyInstaller.
    pause
    exit /b 1
)

echo Construction de la version autonome d'Olney Engine...
".buildenv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "build_tools\OlneyEngine.spec"
if errorlevel 1 (
    echo La construction a echoue.
    pause
    exit /b 1
)

echo.
echo Version autonome disponible dans : dist\Olney Engine
endlocal
