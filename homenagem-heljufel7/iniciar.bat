@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================
echo   Iniciando Projeto: Homenagem Heljufel7
echo ===================================================

where node >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado!
    echo Por favor, instale o Node.js em: https://nodejs.org/
    pause
    exit /b 1
)

rem Checa o vite em vez da pasta: uma instalacao que falhou no meio deixa node_modules incompleto.
if not exist "node_modules\.bin\vite.cmd" (
    echo Instalando dependencias do projeto, aguarde...
    call npm install
    if errorlevel 1 goto erro_install
)

echo Iniciando o servidor web...
start "" http://localhost:5173
call npm run dev -- --port 5173 --host
pause
exit /b

:erro_install
echo [ERRO] Falha ao instalar dependencias.
echo Apague a pasta node_modules e tente novamente.
pause
exit /b 1
