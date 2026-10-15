@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================
echo   Iniciando Projeto: Homenagem Heljufel7
echo ===================================================

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Node.js nao encontrado!
    echo Por favor, instale o Node.js em: https://nodejs.org/
    pause
    exit /b
)

if not exist "node_modules\" (
    echo Instalando dependencias do projeto, aguarde...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b
    )
)

echo Iniciando o servidor web...
start "" http://localhost:5173
call npm run dev -- --port 5173 --host

pause
