import json
import time
import os
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
ARQUIVO_DADOS = PASTA_DADOS / "dados.json"

def tentar_coleta(username):
    # Vamos tentar Picuki, que é um visualizador anônimo
    urls = [
        (f"https://www.picuki.com/profile/{username}", "picuki")
    ]

    info = {
        "usuario": username,
        "seguidores": "Dado indisponível",
        "seguindo": "Dado indisponível",
        "posts": "Dado indisponível",
        "fonte": "Dado indisponível",
        "data_coleta": datetime.now().isoformat()
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="pt-BR",
            viewport={"width": 1366, "height": 768}
        )

        sucesso = False
        for url, site_type in urls:
            try:
                print(f"Tentando extrair de {url}...")
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(4000)

                # Tirar print
                nome_print = PASTA_DADOS / f"print_{username}_{int(time.time())}.png"
                page.screenshot(path=str(nome_print))

                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                text = soup.get_text(separator="\n", strip=True)

                if site_type == "picuki":
                    # Tentar achar a quantidade
                    # Exemplo de texto:
                    # 7,576 Followers
                    # 7.5k
                    # followers
                    lines = text.split("\n")
                    for i, line in enumerate(lines):
                        if "Followers" in line and i > 0:
                            # A linha anterior pode ter o número exato, ou a própria linha
                            val = line.replace("Followers", "").strip()
                            if val:
                                info["seguidores"] = val
                            else:
                                info["seguidores"] = lines[i-1].strip()
                        elif "Following" in line and i > 0:
                            val = line.replace("Following", "").strip()
                            if val:
                                info["seguindo"] = val
                            else:
                                info["seguindo"] = lines[i-1].strip()
                        elif "Posts" in line and i > 0:
                            val = line.replace("Posts", "").strip()
                            if val:
                                info["posts"] = val
                            else:
                                info["posts"] = lines[i-1].strip()

                    # se nao tiver encontrado nada, é possivel que foi bloqueado
                    if info["seguidores"] != "Dado indisponível":
                        info["fonte"] = url
                        sucesso = True
                        break

            except Exception as e:
                print(f"Erro ao acessar {url}: {e}")

        # Se picuki falhou, vamos tentar instagram direto para pelo menos tirar screenshot e tentar
        if not sucesso:
            url_ig = f"https://www.instagram.com/{username}/"
            print(f"Tentando instagram oficial (pode pedir login): {url_ig}...")
            try:
                page.goto(url_ig, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(4000)
                nome_print_ig = PASTA_DADOS / f"print_ig_{username}_{int(time.time())}.png"
                page.screenshot(path=str(nome_print_ig))

                # Tentar extrair do meta description "X Followers, Y Following, Z Posts"
                meta = page.locator("meta[name='description']").get_attribute("content", timeout=2000)
                if meta:
                    # Ex: 639M Followers, 592 Following, 3,745 Posts - See Instagram photos and videos from Cristiano Ronaldo (@cristiano)
                    match_fol = re.search(r"([\d.,Mkm]+)\s*Followers", meta, re.IGNORECASE)
                    match_flw = re.search(r"([\d.,Mkm]+)\s*Following", meta, re.IGNORECASE)
                    match_pst = re.search(r"([\d.,Mkm]+)\s*Posts", meta, re.IGNORECASE)

                    if match_fol: info["seguidores"] = match_fol.group(1)
                    if match_flw: info["seguindo"] = match_flw.group(1)
                    if match_pst: info["posts"] = match_pst.group(1)

                    info["fonte"] = url_ig
            except Exception as e:
                print(f"Erro no instagram oficial: {e}")

        browser.close()

    return info

def salvar_dados(info):
    PASTA_DADOS.mkdir(exist_ok=True)
    dados_existentes = {}
    if ARQUIVO_DADOS.exists():
        try:
            dados_existentes = json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
        except:
            pass

    dados_existentes[info["usuario"]] = info
    ARQUIVO_DADOS.write_text(json.dumps(dados_existentes, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = "cristiano"

    dados = tentar_coleta(username)
    salvar_dados(dados)
