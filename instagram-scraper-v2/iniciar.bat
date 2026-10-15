@echo off
cd /d "%~dp0"
set "PY=py -3"
%PY% -c "import sys" >nul 2>nul
if not errorlevel 1 goto achou
set "PY=python"
%PY% -c "import sys" >nul 2>nul
if not errorlevel 1 goto achou
echo [ERRO] Python 3 nao encontrado. Instale em https://www.python.org/downloads/
echo Na instalacao, marque a opcao "Add python.exe to PATH".
start "" https://www.python.org/downloads/
pause
exit /b 1

:achou
%PY% scripts\iniciar.py
if errorlevel 1 pause
