import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
ARQUIVO_ESTADO = PASTA_DADOS / "estado_login.json"
MODO_TESTE = os.environ.get("MODO_TESTE") == "1"

def autenticar(p):
    browser = None
    context = None
    page = None

    if ARQUIVO_ESTADO.exists() and not MODO_TESTE:
        print("Sessao encontrada. Tentando usar o cache de login...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(ARQUIVO_ESTADO))
        page = context.new_page()
        page.goto("https://www.instagram.com/", wait_until="networkidle", timeout=60000)

        if "login" not in page.url:
            print("Autenticacao com cache bem-sucedida.")
            return browser, context, page
        else:
            print("Cache expirado ou invalido. Faremos login novamente.")
            browser.close()
            ARQUIVO_ESTADO.unlink()

    if MODO_TESTE:
        print("Modo teste ativado: pulando login visual. Usaremos modo headless.")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        return browser, context, page

    print("=======================================")
    print("Aguardando voce fazer login no navegador...")
    print("O navegador fechara sozinho quando o feed do Instagram carregar.")
    print("=======================================")

    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.instagram.com/accounts/login/")

    try:
        page.wait_for_url(lambda url: "login" not in url, timeout=300000)
        page.wait_for_timeout(3000)
        context.storage_state(path=str(ARQUIVO_ESTADO))
        print("Login detectado e sessao salva com sucesso!")
    except Exception as e:
        print("Tempo esgotado ou janela fechada antes do login.")

    return browser, context, page

def salvar_lista(lista, arquivo):
    arquivo.write_text(json.dumps(lista, indent=2, ensure_ascii=False), encoding="utf-8")

def extrair_modal_lista(page, link_texto, max_items=20):
    usuarios = []
    try:
        links = page.locator(f"a:has-text('{link_texto}')")
        if links.count() == 0:
            return usuarios

        links.first.click()
        page.wait_for_timeout(2000)

        dialog = page.locator("div[role='dialog']")
        if dialog.count() == 0:
            return usuarios

        for _ in range(3):
            page.evaluate("() => { const el = document.querySelector('div[role=\"dialog\"] div[style*=\"overflow-y: auto\"]') || document.querySelector('div[role=\"dialog\"] div[style*=\"overflow-y: scroll\"]'); if(el) el.scrollTop = el.scrollHeight; }")
            page.wait_for_timeout(1500)

            items = dialog.locator("span.x1lliihq").all()
            for item in items:
                nome = item.text_content()
                if nome and nome not in usuarios and len(nome) > 2:
                    usuarios.append(nome)

            if len(usuarios) >= max_items:
                break

        close_btn = dialog.locator("svg[aria-label='Close']").locator("..")
        if close_btn.count() > 0:
            close_btn.first.click()
            page.wait_for_timeout(1000)

    except Exception as e:
        print(f"Erro ao extrair modal {link_texto}: {e}")

    return list(set(usuarios))

def coletar_alvo(username):
    PASTA_PERFIL = PASTA_DADOS / username
    PASTA_PERFIL.mkdir(parents=True, exist_ok=True)
    PASTA_POSTS = PASTA_PERFIL / "posts"
    PASTA_POSTS.mkdir(exist_ok=True)
    PASTA_REELS = PASTA_PERFIL / "reels"
    PASTA_REELS.mkdir(exist_ok=True)
    PASTA_STORIES = PASTA_PERFIL / "stories"
    PASTA_STORIES.mkdir(exist_ok=True)

    dados_gerais = {
        "usuario": username,
        "seguidores": "Dado indisponivel",
        "seguindo": "Dado indisponivel",
        "posts_count": "Dado indisponivel",
        "nome": "Dado indisponivel",
        "data_coleta": datetime.now().isoformat()
    }

    with sync_playwright() as p:
        browser, context, page = autenticar(p)

        url_alvo = f"https://www.instagram.com/{username}/"
        print(f"Acessando o perfil {url_alvo}...")
        try:
            page.goto(url_alvo, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            if "Page Not Found" in page.title() or "nao encontrada" in page.title().lower():
                print("Perfil nao encontrado.")
                dados_gerais["erro"] = "Perfil nao encontrado ou bloqueado"
            else:
                # HEADER NUMBERS
                try:
                    header_ul = page.locator("header ul").first
                    if header_ul.count() > 0:
                        lis = header_ul.locator("li").all()
                        if len(lis) >= 3:
                            dados_gerais["posts_count"] = lis[0].text_content().split()[0].strip()
                            dados_gerais["seguidores"] = lis[1].locator("a, span").first.get_attribute("title") or lis[1].text_content().split()[0].strip()
                            dados_gerais["seguindo"] = lis[2].text_content().split()[0].strip()
                except Exception:
                    pass

                # NOME
                try:
                    nome_loc = page.locator("header section > div").nth(2).locator("span").first
                    if nome_loc.count() > 0:
                        dados_gerais["nome"] = nome_loc.text_content().strip()
                except:
                    pass

                # FOTO PERFIL
                try:
                    print("Buscando foto de perfil...")
                    img_loc = page.locator("header img").first
                    if img_loc.count() > 0:
                        src = img_loc.get_attribute("src")
                        if src:
                            dados_gerais["foto_perfil_url"] = src
                            response = context.request.get(src)
                            if response.ok:
                                img_path = PASTA_PERFIL / "foto_perfil.jpg"
                                img_path.write_bytes(response.body())
                                print("Foto de perfil salva!")
                except Exception as e:
                    print(f"Erro na foto de perfil: {e}")

                if not MODO_TESTE:
                    # EXTRAIR LISTAS
                    print("Extraindo seguidores visiveis...")
                    seguidores = extrair_modal_lista(page, "followers", 30)
                    salvar_lista(seguidores, PASTA_PERFIL / "seguidores.json")

                    print("Extraindo seguindo visiveis...")
                    seguindo = extrair_modal_lista(page, "following", 30)
                    salvar_lista(seguindo, PASTA_PERFIL / "seguindo.json")

                    # POSTS LINKS E THUMBNAILS
                    print("Extraindo thumbnails dos posts mais recentes...")
                    posts = page.locator("article a").all()
                    urls_posts = []
                    for i, post in enumerate(posts[:12]):
                        try:
                            href = post.get_attribute("href")
                            img = post.locator("img").first
                            if img.count() > 0:
                                src = img.get_attribute("src")
                                if src:
                                    res = context.request.get(src)
                                    if res.ok:
                                        p_path = PASTA_POSTS / f"post_{i}.jpg"
                                        p_path.write_bytes(res.body())
                                    urls_posts.append(href)
                        except:
                            pass
                    salvar_lista(urls_posts, PASTA_POSTS / "links_posts.json")

                    # EXTRAIR REELS
                    print("Extraindo thumbnails dos reels (se houver guia)...")
                    try:
                        reels_tab = page.locator("a:has-text('Reels')").first
                        if reels_tab.count() > 0:
                            reels_tab.click()
                            page.wait_for_timeout(3000)
                            reels = page.locator("article a").all()
                            urls_reels = []
                            for i, reel in enumerate(reels[:12]):
                                try:
                                    href = reel.get_attribute("href")
                                    img = reel.locator("img").first
                                    if img.count() > 0:
                                        src = img.get_attribute("src")
                                        if src:
                                            res = context.request.get(src)
                                            if res.ok:
                                                r_path = PASTA_REELS / f"reel_{i}.jpg"
                                                r_path.write_bytes(res.body())
                                            urls_reels.append(href)
                                except:
                                    pass
                            salvar_lista(urls_reels, PASTA_REELS / "links_reels.json")

                            # Voltar a Posts originais
                            page.go_back()
                    except Exception as e:
                        print("Erro extraindo reels:", e)

                    # EXTRAIR STORIES
                    print("Extraindo historico/stories visiveis...")
                    try:
                        story_avatar = page.locator("canvas[aria-label='Story']").first
                        if story_avatar.count() > 0:
                            print("Tem story! Tirando screenshot e salvando link/src.")
                            story_avatar.click()
                            page.wait_for_timeout(3000)

                            for i in range(5):
                                st_path = PASTA_STORIES / f"story_{i}.png"
                                page.screenshot(path=str(st_path))

                                next_btn = page.locator("button[aria-label='Next']").first
                                if next_btn.count() > 0:
                                    next_btn.click()
                                    page.wait_for_timeout(1500)
                                else:
                                    break

                            close_st = page.locator("svg[aria-label='Close']").first
                            if close_st.count() > 0:
                                close_st.click()
                    except Exception as e:
                        print("Erro extraindo stories:", e)

        except Exception as e:
            print(f"Erro durante o acesso ao perfil: {e}")

        browser.close()

    ARQUIVO_JSON = PASTA_PERFIL / "historico_perfil.json"
    ARQUIVO_JSON.write_text(json.dumps(dados_gerais, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Dados gerais salvos em {ARQUIVO_JSON}")

if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "cristiano"
    coletar_alvo(alvo)
