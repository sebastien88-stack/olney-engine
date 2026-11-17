@echo off
setlocal
cd /d "%~dp0\.."

call "build_tools\build_portable.bat"
if errorlevel 1 exit /b 1

set "ISCC="
for %%P in (
    "%UserProfile%\AppData\Local\Programs\Inno Setup 7\ISCC.exe"
    "%UserProfile%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
    "%LocalAppData%\Programs\Inno Setup 7\ISCC.exe"
    "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 7\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) do (
    if not defined ISCC if exist "%%~P" set "ISCC=%%~P"
)

if not defined ISCC (
    echo Inno Setup est introuvable.
    echo Installe-le depuis https://jrsoftware.org/inno-setup
    pause
    exit /b 1
)

"%ISCC%" "build_tools\OlneyEngine.iss"
if errorlevel 1 (
    echo La creation de l'installateur a echoue.
    pause
    exit /b 1
)

echo.
echo Installateur disponible dans le dossier release.
endlocal
