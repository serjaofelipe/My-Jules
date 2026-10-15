#!/bin/bash
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERRO] Python 3 nao encontrado. Instale em https://www.python.org/downloads/"
  open https://www.python.org/downloads/
  read -r -p "Pressione Enter para fechar..."
  exit 1
fi
python3 scripts/iniciar.py || read -r -p "Pressione Enter para fechar..."
