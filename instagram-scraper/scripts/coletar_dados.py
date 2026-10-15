"""Coleta os dados públicos de um perfil do Instagram e salva em dados/.

Uso: python scripts/coletar_dados.py <usuario>

O Instagram passou a exigir login na API web_profile_info (responde 401
"require_login" para quem não está logado). Por isso a coleta lê a página
pública do perfil, que continua acessível sem login, e só usa a API como
bônus quando ela responder (dá números exatos e fotos em resolução maior).
"""

import datetime
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
DADOS_DIR = RAIZ / "dados"
DADOS_FILE = DADOS_DIR / "dados.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
API = "https://www.instagram.com/api/v1/users/web_profile_info/?username={}"
INDISPONIVEL = "Dado indisponível"
REQUER_LOGIN = "Dado indisponível (o Instagram exige login)"

NUM = r"(\d[\d.,]*(?:\s*(?:mil|mi|k|m|b)\b)?)"


def to_number(text):
    """'790' -> 790, '1.234' -> 1234; abreviações ('1,2 mi', '12K') ficam como texto."""
    text = text.strip()
    if re.fullmatch(r"[\d.,]+", text):
        return int(re.sub(r"[.,]", "", text))
    return text


def parse_counts(text):
    """Lê seguidores/seguindo/posts de um texto da página (pt-BR ou inglês)."""
    d = text or ""
    patterns = {
        "followers": [NUM + r"\s+seguidores", NUM + r"\s+followers"],
        "following": [NUM + r"\s+seguindo", r"seguindo\s+" + NUM, NUM + r"\s+following"],
        "posts": [NUM + r"\s+(?:posts|publicações)"],
    }
    found = {}
    for field, regexes in patterns.items():
        for rx in regexes:
            m = re.search(rx, d, re.I)
            if m:
                found[field] = to_number(m.group(1))
                break
    return found


def close_signup_popup(page):
    """Fecha o popup "Cadastre-se" que o Instagram mostra para quem não está logado."""
    for selector in ('div[role="dialog"] svg[aria-label="Fechar"]',
                     'div[role="dialog"] svg[aria-label="Close"]'):
        btn = page.locator(selector).first
        if btn.count():
            try:
                btn.click(timeout=3000)
                page.wait_for_timeout(800)
                return
            except Exception:  # noqa: BLE001 - tenta o próximo jeito
                pass
    page.keyboard.press("Escape")
    page.wait_for_timeout(800)


def save_file(page, url, path):
    try:
        resp = page.request.get(url, timeout=30000)
        if resp.ok:
            path.write_bytes(resp.body())
            return True
    except Exception as e:  # noqa: BLE001 - uma foto que falha não deve parar a coleta
        print(f"Aviso: falha ao baixar {path.name}: {e}", file=sys.stderr)
    return False


def try_api(page, username):
    """API interna do Instagram; hoje quase sempre exige login, então é opcional."""
    res = page.evaluate(
        """async (url) => {
            const r = await fetch(url, {headers: {'x-ig-app-id': '936619743392459',
                                                  'x-requested-with': 'XMLHttpRequest'}});
            return {status: r.status, body: await r.text()};
        }""",
        API.format(username),
    )
    if res["status"] != 200:
        return None
    try:
        return json.loads(res["body"])["data"]["user"]
    except (ValueError, KeyError, TypeError):
        return None


def collect_data(username):
    pasta = DADOS_DIR / username
    pasta.mkdir(parents=True, exist_ok=True)
    perfil_url = f"https://www.instagram.com/{username}/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, locale="pt-BR",
                                  viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        try:
            resp = page.goto(perfil_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            if resp is None or resp.status == 404 or "/accounts/login" in page.url:
                print(f"Erro: o perfil @{username} não existe ou o Instagram pediu login "
                      f"(status {resp.status if resp else 'desconhecido'}).", file=sys.stderr)
                return 1

            def meta(prop):
                m = page.locator(f'meta[property="{prop}"]').first
                return m.get_attribute("content") if m.count() else None

            og_desc = meta("og:description")
            if not og_desc:
                print("Erro: a página do perfil não trouxe os dados. O perfil pode não existir, "
                      "ser privado, ou o Instagram bloqueou o acesso. Tente de novo em alguns minutos.",
                      file=sys.stderr)
                return 1

            dados = {
                "username": username,
                "nome": (meta("og:title") or "").split(" (@")[0] or INDISPONIVEL,
                "followers": INDISPONIVEL,
                "following": INDISPONIVEL,
                "posts": INDISPONIVEL,
                "lista_de_seguidores": REQUER_LOGIN,
                "stories": REQUER_LOGIN,
                "fonte": perfil_url,
                "metodo": "página pública do perfil",
                "data_coleta": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "arquivos": [],
            }
            # O og:description pode estar desatualizado (cache do Instagram): o cabeçalho
            # visível da página tem prioridade e o og só completa o que faltar.
            dados.update(parse_counts(og_desc))
            try:
                dados.update(parse_counts(page.locator("header").first.inner_text(timeout=5000)))
            except Exception:  # noqa: BLE001 - sem cabeçalho, fica o valor do og
                pass

            close_signup_popup(page)
            page.screenshot(path=str(pasta / "print_perfil.png"), full_page=True)
            dados["arquivos"].append("print_perfil.png")

            user = try_api(page, username)
            post_urls = []
            foto_perfil = meta("og:image")
            if user:
                dados["metodo"] = "API do Instagram (números exatos)"
                dados["followers"] = user.get("edge_followed_by", {}).get("count", dados["followers"])
                dados["following"] = user.get("edge_follow", {}).get("count", dados["following"])
                media = user.get("edge_owner_to_timeline_media", {})
                dados["posts"] = media.get("count", dados["posts"])
                foto_perfil = user.get("profile_pic_url_hd") or foto_perfil
                post_urls = [e["node"]["display_url"] for e in media.get("edges", [])
                             if e.get("node", {}).get("display_url")]
            else:
                # Sem a API: a foto de perfil e as miniaturas dos posts estão no HTML da página.
                imgs = page.eval_on_selector_all(
                    "img", "els => els.map(e => ({alt: e.alt || '', src: e.currentSrc || e.src, w: e.naturalWidth}))")
                perfil_imgs = [i for i in imgs if "perfil" in i["alt"].lower() or "profile" in i["alt"].lower()]
                if perfil_imgs:
                    foto_perfil = max(perfil_imgs, key=lambda i: i["w"])["src"]
                post_urls = page.eval_on_selector_all(
                    'a[href*="/p/"] img, a[href*="/reel/"] img', "els => els.map(e => e.currentSrc || e.src)")

            if foto_perfil and save_file(page, foto_perfil, pasta / "foto_perfil.jpg"):
                dados["arquivos"].append("foto_perfil.jpg")
            for n, url in enumerate(dict.fromkeys(post_urls), 1):
                nome = f"post_{n}.jpg"
                if save_file(page, url, pasta / nome):
                    dados["arquivos"].append(nome)

            dados["pasta"] = str(pasta)
            DADOS_FILE.write_text(json.dumps(dados, ensure_ascii=False, indent=4), encoding="utf-8")
            (pasta / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=4), encoding="utf-8")
            print(json.dumps(dados, ensure_ascii=False, indent=2))
            return 0
        except Exception as e:  # noqa: BLE001 - mensagem vai para a janela do usuário
            print(f"Erro durante a coleta: {e}", file=sys.stderr)
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Erro: Usuário não fornecido.", file=sys.stderr)
        sys.exit(1)
    if os.environ.get("MODO_TESTE") == "1":
        print("MODO_TESTE: coleta real com o perfil informado.")
    sys.exit(collect_data(sys.argv[1].lstrip("@").strip()))
