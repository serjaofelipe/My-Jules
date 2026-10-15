import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import subprocess
import json
import sys
import os

RAIZ = Path(__file__).resolve().parent
SCRIPTS_DIR = RAIZ / "scripts"
DADOS_FILE = RAIZ / "dados" / "dados.json"

def run_scraper(username):
    # Determine the python executable being used (from the virtual env)
    python_exe = sys.executable

    # Run the playwright scraper process
    script_path = SCRIPTS_DIR / "coletar_dados.py"

    try:
        # Run it and capture output or wait for completion
        result = subprocess.run([python_exe, str(script_path), username], capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Erro ao coletar dados:\n{result.stderr}"
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)

def on_submit():
    username = entry.get().strip()
    if not username:
        messagebox.showwarning("Aviso", "Por favor, insira um perfil válido.")
        return

    # Remove @ if the user typed it
    if username.startswith('@'):
        username = username[1:]

    btn_submit.config(state=tk.DISABLED, text="Coletando...")
    root.update()

    success, msg = run_scraper(username)

    btn_submit.config(state=tk.NORMAL, text="Buscar")

    if not success:
        messagebox.showerror("Erro", msg)

        # If in test mode, we might just exit
        if os.environ.get("MODO_TESTE") == "1":
            print(f"Erro em modo teste: {msg}")
            sys.exit(1)

        return

    # Read the data back from dados/dados.json
    try:
        with open(DADOS_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)

        # Display the results
        info_text.config(state=tk.NORMAL)
        info_text.delete(1.0, tk.END)

        info = (
            f"Perfil: {dados.get('nome', '')} (@{dados.get('username', username)})\n"
            f"Seguidores: {dados.get('followers', 'Dado indisponível')}\n"
            f"Seguindo: {dados.get('following', 'Dado indisponível')}\n"
            f"Publicações: {dados.get('posts', 'Dado indisponível')}\n"
            f"Lista de seguidores / stories: exige login no Instagram\n"
            f"\n{len(dados.get('arquivos', []))} arquivos (print, foto de perfil e posts) em:\n"
            f"{dados.get('pasta', RAIZ / 'dados')}\n"
            f"Fonte: {dados.get('metodo', '')}, em {dados.get('data_coleta', '')}"
        )
        info_text.insert(tk.END, info)
        info_text.config(state=tk.DISABLED)

        if os.environ.get("MODO_TESTE") == "1":
            print("Teste finalizado com sucesso.")
            sys.exit(0)

    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao ler os dados coletados: {e}")
        if os.environ.get("MODO_TESTE") == "1":
            sys.exit(1)

root = tk.Tk()
root.title("Instagram Scraper")
root.geometry("480x420")
root.resizable(False, False)

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

lbl_title = tk.Label(frame, text="Insira o perfil do Instagram", font=("Arial", 12, "bold"))
lbl_title.pack(pady=(0, 10))

entry = tk.Entry(frame, width=30, font=("Arial", 12))
entry.pack(pady=5)
entry.bind("<Return>", lambda e: on_submit())

btn_submit = tk.Button(frame, text="Buscar", width=15, font=("Arial", 10), command=on_submit)
btn_submit.pack(pady=10)

lbl_warning = tk.Label(
    frame,
    text="Nota: Apenas contas públicas são suportadas.\nA coleta de todos os seguidores requer login e pode causar banimentos.",
    font=("Arial", 8),
    fg="gray",
    justify=tk.CENTER
)
lbl_warning.pack(pady=5)

info_text = tk.Text(frame, height=11, width=55, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 10), bg="#f0f0f0", relief=tk.FLAT)
info_text.pack(pady=10)

if __name__ == "__main__":
    if os.environ.get("MODO_TESTE") == "1":
        entry.insert(0, "cristiano")
        # Run after 500ms so Tkinter has time to render
        root.after(500, on_submit)
        # Fallback to exit after 60s
        root.after(60000, sys.exit, 0)
    root.mainloop()
