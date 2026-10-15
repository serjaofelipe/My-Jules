import os
import json
from pathlib import Path
from datetime import datetime

# Usa MODO_TESTE do ambiente para pular inputs se estiver testando
MODO_TESTE = os.environ.get("MODO_TESTE") == "1"

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
ARQUIVO_DADOS = PASTA_DADOS / "dados.json"

def pedir_perfil():
    if MODO_TESTE:
        return "cristiano"

    print("========================================")
    print("         INSTAGRAM SCRAPER")
    print("========================================")
    perfil = input("Digite o perfil do Instagram (sem @): ").strip()
    return perfil

def carregar_dados():
    if ARQUIVO_DADOS.exists():
        try:
            return json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def salvar_dados(dados):
    PASTA_DADOS.mkdir(exist_ok=True)
    ARQUIVO_DADOS.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    perfil = pedir_perfil()
    if not perfil:
        print("Perfil não informado. Encerrando.")
        return

    print(f"Iniciando coleta para o perfil: {perfil}")

    # Executa o script de coleta passando o perfil
    import subprocess
    script_coleta = RAIZ / "scripts" / "coletar_dados.py"

    try:
        subprocess.run([sys.executable, str(script_coleta), perfil], check=True)
        print("Processo finalizado!")

        # Exibe os dados coletados
        dados = carregar_dados()
        if perfil in dados:
            info = dados[perfil]
            print("\nResultados encontrados:")
            print(f"Seguidores: {info.get('seguidores', 'Dado indisponível')}")
            print(f"Seguindo: {info.get('seguindo', 'Dado indisponível')}")
            print(f"Posts: {info.get('posts', 'Dado indisponível')}")
            print(f"Fonte: {info.get('fonte', 'Dado indisponível')}")
            print(f"Data da coleta: {info.get('data_coleta', 'Dado indisponível')}")
            print(f"\nA screenshot foi salva na pasta 'dados' se a pagina carregou.")
    except Exception as e:
        print(f"Erro durante a execução: {e}")

if __name__ == "__main__":
    import sys
    main()
