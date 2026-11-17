@echo off
setlocal
cd /d "%~dp0"

set "OLNEY_PYTHON="
for %%P in (
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python314\python.exe"
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
) do (
    if not defined OLNEY_PYTHON if exist "%%~P" set "OLNEY_PYTHON=%%~P"
)

if defined OLNEY_PYTHON goto run_python

py -3 -c "import tkinter" >nul 2>&1
if not errorlevel 1 goto run_launcher

echo Python avec Tcl/Tk est introuvable.
echo Installe la version complete depuis https://www.python.org/downloads/windows/
echo en cochant l'ajout de Python au PATH et le composant Tcl/Tk.
pause
exit /b 1

:run_python
"%OLNEY_PYTHON%" app.py
goto finished

:run_launcher
py -3 app.py

:finished
if errorlevel 1 pause
endlocal
