#!/bin/bash
cd "$(dirname "$0")"

echo "==================================================="
echo "  Iniciando Projeto: Homenagem Heljufel7"
echo "==================================================="

if ! command -v node &> /dev/null; then
    echo "[ERRO] Node.js nao encontrado!"
    echo "Por favor, instale o Node.js em: https://nodejs.org/"
    read -p "Pressione Enter para fechar..."
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "Instalando dependencias do projeto, aguarde..."
    npm install
    if [ $? -ne 0 ]; then
        echo "[ERRO] Falha ao instalar dependencias."
        read -p "Pressione Enter para fechar..."
        exit 1
    fi
fi

echo "Iniciando o servidor web..."
open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || true
npm run dev -- --port 5173 --host

read -p "Pressione Enter para fechar..."
