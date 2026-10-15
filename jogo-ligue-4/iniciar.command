#!/bin/bash
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v node >/dev/null 2>&1; then
  echo "[ERRO] Node.js nao encontrado. Instale a versao LTS em https://nodejs.org/"
  open https://nodejs.org/
  read -r -p "Pressione Enter para fechar..."
  exit 1
fi
node scripts/iniciar.mjs || read -r -p "Pressione Enter para fechar..."
