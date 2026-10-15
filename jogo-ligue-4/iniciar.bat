@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 goto sem_node
node scripts\iniciar.mjs
if errorlevel 1 pause
exit /b

:sem_node
echo [ERRO] Node.js nao encontrado. Instale a versao LTS em https://nodejs.org/
echo Depois de instalar, feche esta janela e de duplo clique de novo.
start "" https://nodejs.org/
pause
exit /b 1
