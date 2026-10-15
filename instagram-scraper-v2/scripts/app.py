import os
import json
from pathlib import Path

MODO_TESTE = os.environ.get("MODO_TESTE") == "1"
RAIZ = Path(__file__).resolve().parent.parent

def pedir_perfil():
    if MODO_TESTE:
        return "nike"

    print("========================================")
    print("      INSTAGRAM SCRAPER V2 (LOGIN)")
    print("========================================")
    print("Na primeira vez o navegador abrira para voce logar.")
    perfil = input("Digite o perfil alvo (sem @): ").strip()
    return perfil

def main():
    perfil = pedir_perfil()
    if not perfil:
        print("Perfil não informado. Encerrando.")
        return

    print(f"\nIniciando coleta avancada para o perfil: {perfil}")

    import subprocess
    import sys
    script_coleta = RAIZ / "scripts" / "coletar_dados.py"

    try:
        subprocess.run([sys.executable, str(script_coleta), perfil], check=True)
        print("\nProcesso finalizado com sucesso!")
        print(f"Verifique a pasta 'dados/{perfil}'")
    except Exception as e:
        print(f"Erro durante a execução: {e}")

if __name__ == "__main__":
    main()
