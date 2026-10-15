"""Cria o .venv, instala as dependencias quando mudarem e inicia o projeto."""
import hashlib
import os
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PRINCIPAL = RAIZ / "scripts" / "app.py"
URL_APP = None

VENV = RAIZ / ".venv"
PY_VENV = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQ = RAIZ / "requirements.txt"
MARCA = VENV / ".requirements.sha256"


def preparar():
    if not PY_VENV.exists():
        print("Criando ambiente Python (so na primeira vez)...")
        venv.create(VENV, with_pip=True)
    if REQ.exists():
        atual = hashlib.sha256(REQ.read_bytes()).hexdigest()
        if not MARCA.exists() or MARCA.read_text() != atual:
            print("Instalando dependencias...")
            r = subprocess.run([str(PY_VENV), "-m", "pip", "install", "-r", str(REQ)])
            if r.returncode != 0:
                print("[ERRO] Falha ao instalar dependencias. Apague a pasta .venv e tente de novo.")
                return False

            subprocess.run([str(PY_VENV), "-m", "playwright", "install", "--with-deps", "chromium"])

            MARCA.write_text(atual)
    return True


def abrir_quando_pronto(url):
    for _ in range(120):
        try:
            urllib.request.urlopen(url, timeout=1)
            webbrowser.open(url)
            return
        except OSError:
            time.sleep(0.5)


def main():
    if not preparar():
        return 1
    proc = subprocess.Popen([str(PY_VENV), str(PRINCIPAL)], cwd=RAIZ)
    if URL_APP and not os.environ.get("SEM_NAVEGADOR"):
        abrir_quando_pronto(URL_APP)
    return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
