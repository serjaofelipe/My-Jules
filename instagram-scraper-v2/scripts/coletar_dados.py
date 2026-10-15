"""Coleta um perfil do Instagram usando a sua sessão logada.

Mídia (fotos e vídeos de posts, reels, stories e destaques) é baixada nos
arquivos originais (.jpg / .mp4). Os .json guardam só dados de texto:
histórico do perfil, seguidores, seguindo, legendas/datas/curtidas e o
de-para unfollowers_followed.json (quem o perfil segue e não segue de volta).

Como funciona: o script navega pelo perfil como uma pessoa faria e lê os
dados que o próprio site do Instagram carrega (respostas GraphQL e o JSON
embutido no HTML). Os endereços antigos da API (/api/v1/feed/...) passaram
a devolver só a página HTML, por isso não são mais usados para mídia.

Limites (para não chamar atenção do Instagram) podem ser mudados por
variável de ambiente: LIMITE_POSTS, LIMITE_REELS e LIMITE_LISTA.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
ARQUIVO_ESTADO = PASTA_DADOS / "estado_login.json"
MODO_TESTE = os.environ.get("MODO_TESTE") == "1"

LIMITE_POSTS = int(os.environ.get("LIMITE_POSTS", "30"))
LIMITE_REELS = int(os.environ.get("LIMITE_REELS", "30"))
# Seguidores/seguindo vêm completos para o de-para (unfollowers_followed.json) ser confiável.
LIMITE_LISTA = int(os.environ.get("LIMITE_LISTA", "5000"))
PAUSA = 1.2  # segundos entre chamadas à API
INDISPONIVEL = "Dado indisponivel"


def novo_contexto(browser, **kwargs):
    """Contexto que se apresenta como Chrome comum.

    O modo invisível se identifica como "HeadlessChrome", e o Instagram
    bloqueia (429) a sessão logada quando vê isso.
    """
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          f"(KHTML, like Gecko) Chrome/{browser.version} Safari/537.36")
    return browser.new_context(user_agent=ua, locale="pt-BR",
                               viewport={"width": 1366, "height": 900}, **kwargs)


def autenticar(p):
    browser = None
    context = None
    page = None

    if ARQUIVO_ESTADO.exists() and not MODO_TESTE:
        print("Sessao encontrada. Tentando usar o cache de login...")
        browser = p.chromium.launch(headless=True)
        context = novo_contexto(browser, storage_state=str(ARQUIVO_ESTADO))
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
        context = novo_contexto(browser)
        page = context.new_page()
        return browser, context, page

    print("=======================================")
    print("Aguardando voce fazer login no navegador...")
    print("O navegador fechara sozinho quando o feed do Instagram carregar.")
    print("=======================================")

    browser = p.chromium.launch(headless=False)
    context = novo_contexto(browser)
    page = context.new_page()
    page.goto("https://www.instagram.com/accounts/login/")

    try:
        page.wait_for_url(lambda url: "login" not in url, timeout=300000)
        page.wait_for_timeout(3000)
        context.storage_state(path=str(ARQUIVO_ESTADO))
        print("Login detectado e sessao salva com sucesso!")
    except Exception:
        print("Tempo esgotado ou janela fechada antes do login.")

    return browser, context, page


# ---------------------------------------------------------------- leitura do que o site carrega


def ler_json_do_site(texto):
    """Respostas GraphQL vêm como text/javascript, às vezes várias linhas JSON."""
    texto = (texto or "").lstrip()
    if texto.startswith("for (;;);"):
        texto = texto[9:]
    docs = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if linha.startswith("{"):
            try:
                docs.append(json.loads(linha))
            except ValueError:
                pass
    if not docs:
        try:
            docs.append(json.loads(texto))
        except ValueError:
            pass
    return docs


class Captura:
    """Guarda as respostas GraphQL que a página recebe: [(nome da consulta, json)]."""

    def __init__(self, page):
        self.docs = []
        page.on("response", self._on_response)

    def _on_response(self, resp):
        if "graphql" not in resp.url:
            return
        try:
            nome = resp.request.headers.get("x-fb-friendly-name", "")
            for doc in ler_json_do_site(resp.text()):
                self.docs.append((nome, doc))
        except Exception:
            pass  # resposta de redirecionamento ou já descartada pelo navegador

    def limpar(self):
        self.docs.clear()

    def de(self, *trechos):
        return [d for nome, d in self.docs if any(t in nome for t in trechos)]


def json_embutido(page):
    docs = []
    for script in page.locator('script[type="application/json"]').all():
        try:
            docs.append(json.loads(script.text_content()))
        except Exception:
            pass
    return docs


def e_midia(d):
    return isinstance(d, dict) and "taken_at" in d and ("video_versions" in d or "image_versions2" in d)


def achar_midias(obj, saida=None):
    """Todas as mídias (posts/stories) dentro de um JSON, sem descer nos filhos de carrossel."""
    saida = [] if saida is None else saida
    if isinstance(obj, dict):
        if e_midia(obj):
            saida.append(obj)
            return saida
        for v in obj.values():
            achar_midias(v, saida)
    elif isinstance(obj, list):
        for v in obj:
            achar_midias(v, saida)
    return saida


def achar_reels_de_story(obj, saida=None):
    """{id do reel: objeto com 'items' e 'title'}; o id é o do usuário (stories) ou 'highlight:...'."""
    saida = {} if saida is None else saida
    if isinstance(obj, dict):
        itens = obj.get("items")
        if obj.get("id") and isinstance(itens, list) and itens and e_midia(itens[0]):
            saida.setdefault(str(obj["id"]), obj)
        for v in obj.values():
            achar_reels_de_story(v, saida)
    elif isinstance(obj, list):
        for v in obj:
            achar_reels_de_story(v, saida)
    return saida


def achar_chave(obj, chave):
    if isinstance(obj, dict):
        if chave in obj:
            return obj[chave]
        for v in obj.values():
            r = achar_chave(v, chave)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = achar_chave(v, chave)
            if r is not None:
                return r
    return None


def unicos(midias):
    vistos = {}
    for m in midias:
        vistos.setdefault(str(m.get("pk") or m.get("id")), m)
    return sorted(vistos.values(), key=lambda m: m.get("taken_at") or 0, reverse=True)


def rolar_e_coletar(page, captura, consultas, limite):
    """Rola a página até ter `limite` mídias das consultas indicadas (ou parar de vir novas)."""
    midias, parado = [], 0
    while parado < 3:
        midias = unicos(m for d in captura.de(*consultas) for m in achar_midias(d))
        if len(midias) >= limite:
            break
        antes = len(midias)
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(2500)
        depois = len(unicos(m for d in captura.de(*consultas) for m in achar_midias(d)))
        parado = parado + 1 if depois == antes else 0
    return midias[:limite]


# ---------------------------------------------------------------- API (só para listas e plano B)


def ig_api(page, path, form=None, tentativas=3):
    """Chama a API do Instagram de dentro da página (usa os cookies da sessão logada).

    Em 429 (muitas requisições) espera e tenta de novo: 20s, 40s, 80s.
    """
    for n in range(tentativas + 1):
        res = _chamar(page, path, form)
        if res["status"] != 429 or n == tentativas:
            break
        espera = 20 * 2 ** n
        print(f"  Instagram pediu para ir mais devagar (429). Esperando {espera}s...")
        time.sleep(espera)
    if res["status"] != 200 or not isinstance(res["body"], dict):
        msg = (res["body"] or {}).get("message", "") if isinstance(res["body"], dict) else ""
        tipo = "" if isinstance(res["body"], dict) else " (veio pagina HTML em vez de dados)"
        raise RuntimeError(f"API {path.split('?')[0]} respondeu {res['status']} {msg}{tipo}".strip())
    return res["body"]


def _chamar(page, path, form):
    res = page.evaluate(
        """async ({path, form}) => {
            const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
            const opts = {method: form ? 'POST' : 'GET', credentials: 'include',
                          headers: {'x-ig-app-id': '936619743392459', 'x-csrftoken': csrf,
                                    'x-requested-with': 'XMLHttpRequest'}};
            if (form) {
                opts.body = new URLSearchParams(form).toString();
                opts.headers['content-type'] = 'application/x-www-form-urlencoded';
            }
            const r = await fetch(path, opts);
            let body = null;
            try { body = await r.json(); } catch (e) {}
            return {status: r.status, body};
        }""",
        {"path": path, "form": form},
    )
    time.sleep(PAUSA)
    return res


def buscar_lista(page, uid, qual):
    """Lista de seguidores/seguindo, página por página. Devolve (usuarios, completa?)."""
    usuarios, vistos, max_id = [], set(), ""
    # Sem "order" a lista vem ranqueada e embaralha entre as páginas: contas repetem,
    # outras nunca aparecem e o servidor encerra cedo (ex.: 102 de 260 em "seguindo").
    # Por data de follow a ordem é fixa e a lista vem inteira.
    ordem = "&order=date_followed_latest" if qual == "following" else ""
    while len(usuarios) < LIMITE_LISTA:
        corpo = ig_api(page, f"/api/v1/friendships/{uid}/{qual}/?count=50{ordem}"
                       + (f"&max_id={max_id}" if max_id else ""), tentativas=2)
        for u in corpo.get("users", []):
            if u.get("username") and u["username"] not in vistos:
                vistos.add(u["username"])
                usuarios.append({"usuario": u["username"], "nome": u.get("full_name"),
                                 "privado": u.get("is_private"), "verificado": u.get("is_verified")})
        max_id = corpo.get("next_max_id")
        if not max_id:
            return usuarios, True
        print(f"  {len(usuarios)}...")
    return usuarios[:LIMITE_LISTA], False


def gerar_depara(pasta, username, seguidores, seguindo, seguidores_antes, contagem_perfil=None):
    """unfollowers_followed.json: quem o perfil segue e não segue de volta (e o contrário)."""
    (lista_seguidores, seguidores_completa), (lista_seguindo, seguindo_completa) = seguidores, seguindo
    nomes_seguidores = {u["usuario"] for u in lista_seguidores}
    nomes_seguindo = {u["usuario"] for u in lista_seguindo}
    completo = seguidores_completa and seguindo_completa
    resultado = {
        "perfil": username,
        "data_coleta": datetime.now().isoformat(timespec="seconds"),
        "listas_completas": completo,
        "total_seguidores": len(nomes_seguidores),
        "total_seguindo": len(nomes_seguindo),
        "nao_seguem_de_volta": sorted((u for u in lista_seguindo if u["usuario"] not in nomes_seguidores),
                                      key=lambda u: u["usuario"].lower()),
        "voce_nao_segue_de_volta": sorted((u for u in lista_seguidores if u["usuario"] not in nomes_seguindo),
                                          key=lambda u: u["usuario"].lower()),
    }
    # Quem deixou de seguir desde a coleta anterior (só dá para saber com as duas listas completas).
    if seguidores_completa and seguidores_antes.get("completa"):
        resultado["deixaram_de_seguir_desde_ultima_coleta"] = sorted(
            set(seguidores_antes["usuarios"]) - nomes_seguidores, key=str.lower)
        resultado["novos_seguidores_desde_ultima_coleta"] = sorted(
            nomes_seguidores - set(seguidores_antes["usuarios"]), key=str.lower)
    avisos = []
    if not completo:
        avisos.append("Listas incompletas (limite LIMITE_LISTA ou o Instagram parou de responder): "
                      "o de-para pode ter falsos positivos.")
    # O número do perfil conta contas desativadas/restritas que o Instagram não lista.
    for chave, total in (("seguidores", len(nomes_seguidores)), ("seguindo", len(nomes_seguindo))):
        no_perfil = (contagem_perfil or {}).get(chave)
        if isinstance(no_perfil, int):
            resultado[f"{chave}_no_perfil"] = no_perfil
            if no_perfil - total > max(5, no_perfil * 0.05):
                avisos.append(f"O perfil mostra {no_perfil} em '{chave}', mas o Instagram so lista {total}. "
                              "Os que faltam (contas desativadas/restritas) ficam fora do de-para.")
    if avisos:
        resultado["avisos"] = avisos
    resultado["quantidade_nao_seguem_de_volta"] = len(resultado["nao_seguem_de_volta"])
    resultado["quantidade_voce_nao_segue_de_volta"] = len(resultado["voce_nao_segue_de_volta"])
    salvar_json(resultado, pasta / "unfollowers_followed.json")
    print(f"De-para: {resultado['quantidade_nao_seguem_de_volta']} que {username} segue e nao seguem de volta"
          + ("" if completo else " (listas incompletas!)"))
    for aviso in avisos:
        print(f"  [aviso] {aviso}")


# ---------------------------------------------------------------- download


def arquivos_da_midia(item):
    """[(url, extensão)] do arquivo original de cada mídia (carrossel vira vários)."""
    partes = item.get("carousel_media") or [item]
    saida = []
    for m in partes:
        videos = m.get("video_versions") or []
        if videos:
            melhor = max(videos, key=lambda v: (v.get("width") or 0) * (v.get("height") or 0))
            saida.append((melhor["url"], "mp4"))
            continue
        fotos = (m.get("image_versions2") or {}).get("candidates") or []
        if fotos:
            melhor = max(fotos, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0))
            saida.append((melhor["url"], "jpg"))
    return saida


def baixar(context, url, destino):
    if destino.exists() and destino.stat().st_size > 0:
        return True  # já baixado numa coleta anterior
    try:
        r = context.request.get(url, timeout=120000)
        if r.ok:
            destino.write_bytes(r.body())
            return True
        print(f"  falha ao baixar {destino.name}: HTTP {r.status}")
    except Exception as e:
        print(f"  falha ao baixar {destino.name}: {e}")
    return False


def data_de(item):
    ts = item.get("taken_at") or item.get("device_timestamp") or 0
    if ts > 10**11:  # alguns vêm em microssegundos
        ts //= 10**6
    return datetime.fromtimestamp(ts) if ts else datetime.now()


def salvar_midias(context, itens, pasta, tipo, detalhado=True):
    """Baixa a mídia de cada item e devolve os metadados (texto) para o JSON."""
    registros = []
    for item in itens:
        quando = data_de(item)
        codigo = item.get("code") or str(item.get("pk") or item.get("id", "")).split("_")[0]
        arquivos = []
        for n, (url, ext) in enumerate(arquivos_da_midia(item), 1):
            sufixo = f"_{n}" if len(item.get("carousel_media") or []) > 1 else ""
            destino = pasta / f"{quando:%Y-%m-%d_%H%M%S}_{codigo}{sufixo}.{ext}"
            if baixar(context, url, destino):
                arquivos.append(destino.name)
        legenda = (item.get("caption") or {}).get("text", "") if isinstance(item.get("caption"), dict) else ""
        dono = (item.get("user") or item.get("owner") or {}).get("username")
        registros.append({
            "codigo": codigo,
            "link": f"https://www.instagram.com/{'reel' if tipo == 'reel' else 'p'}/{codigo}/" if item.get("code") else None,
            "tipo": "carrossel" if item.get("carousel_media") else ("video" if item.get("video_versions") else "foto"),
            "data": quando.isoformat(timespec="seconds"),
            "autor": dono,
            "legenda": legenda,
            "curtidas": item.get("like_count"),
            "comentarios": item.get("comment_count"),
            "visualizacoes": item.get("play_count") or item.get("view_count"),
            "arquivos": arquivos,
        })
        if detalhado:
            print(f"  {tipo} {codigo}: {len(arquivos)} arquivo(s)")
    return registros


# ---------------------------------------------------------------- coleta


def salvar_json(dados, arquivo):
    arquivo.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def ler_json(arquivo, padrao):
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def etapa(nome, funcao, erros):
    """Roda uma parte da coleta; se falhar, registra e segue com as outras."""
    try:
        return funcao()
    except Exception as e:
        print(f"[aviso] {nome}: {e}")
        erros[nome] = str(e)
        return None


def dados_do_cabecalho(page, dados):
    """Plano B: números do cabeçalho visível da página."""
    try:
        lis = page.locator("header ul li").all()
        if len(lis) >= 3:
            dados["posts_count"] = lis[0].text_content().split()[0].strip()
            dados["seguidores"] = (lis[1].locator("a, span").first.get_attribute("title")
                                   or lis[1].text_content().split()[0].strip())
            dados["seguindo"] = lis[2].text_content().split()[0].strip()
    except Exception:
        pass


def ler_perfil(captura, page, username, dados):
    """Preenche os dados do perfil a partir do que a página do perfil carregou."""
    usuario = None
    for doc in captura.de("ProfilePageContent") + json_embutido(page):
        u = achar_chave(doc, "user")
        if isinstance(u, dict) and u.get("username") == username and ("follower_count" in u or "pk" in u):
            usuario = u
            break
    if usuario:
        dados.update({
            "id": str(usuario.get("pk") or usuario.get("id") or "") or None,
            "nome": usuario.get("full_name") or INDISPONIVEL,
            "biografia": usuario.get("biography", ""),
            "seguidores": usuario.get("follower_count", INDISPONIVEL),
            "seguindo": usuario.get("following_count", INDISPONIVEL),
            "posts_count": usuario.get("media_count", INDISPONIVEL),
            "privado": usuario.get("is_private"),
            "verificado": usuario.get("is_verified"),
            "link_externo": usuario.get("external_url"),
            "foto_perfil_url": (usuario.get("hd_profile_pic_url_info") or {}).get("url")
                               or usuario.get("profile_pic_url"),
            "voce_segue": (usuario.get("friendship_status") or {}).get("following"),
        })
    else:
        dados_do_cabecalho(page, dados)
    if not dados.get("id"):
        m = re.search(r'"profilePage_(\d+)"|"profile_id":"(\d+)"', page.content())
        if m:
            dados["id"] = next(g for g in m.groups() if g)
    return usuario is not None


def coletar_alvo(username):
    PASTA_PERFIL = PASTA_DADOS / username
    pastas = {nome: PASTA_PERFIL / nome for nome in ("posts", "reels", "stories", "destaques")}
    for pasta in [PASTA_PERFIL, *pastas.values()]:
        pasta.mkdir(parents=True, exist_ok=True)

    dados_gerais = {
        "usuario": username,
        "nome": INDISPONIVEL,
        "biografia": "",
        "seguidores": INDISPONIVEL,
        "seguindo": INDISPONIVEL,
        "posts_count": INDISPONIVEL,
        "privado": None,
        "data_coleta": datetime.now().isoformat(timespec="seconds"),
    }
    erros = {}

    with sync_playwright() as p:
        browser, context, page = autenticar(p)
        logado = any(c["name"] == "sessionid" for c in context.cookies())
        captura = Captura(page)

        url_alvo = f"https://www.instagram.com/{username}/"
        print(f"Acessando o perfil {url_alvo}...")
        try:
            page.goto(url_alvo, wait_until="load", timeout=60000)
            page.wait_for_timeout(7000)
            ler_perfil(captura, page, username, dados_gerais)
            foto = dados_gerais.pop("foto_perfil_url", None)
            if foto and baixar(context, foto, PASTA_PERFIL / "foto_perfil.jpg"):
                print("Foto de perfil salva!")

            uid = dados_gerais.get("id")
            if not logado:
                print("Sem login: baixando so os dados publicos do perfil.")
            elif dados_gerais.get("privado") and not dados_gerais.get("voce_segue"):
                print("Perfil privado que voce nao segue: so os dados publicos estao disponiveis.")
            else:
                # Destaques: a lista vem junto com a página do perfil.
                bandeja = []
                for doc in captura.de("Highlights"):
                    for edge in (achar_chave(doc, "edges") or []):
                        node = edge.get("node") or {}
                        if str(node.get("id", "")).startswith("highlight:"):
                            bandeja.append({"id": node["id"], "titulo": node.get("title") or ""})
                if not bandeja:  # formato mudou: pega pelo menos os ids
                    texto = json.dumps([d for _, d in captura.docs]) + page.content()
                    bandeja = [{"id": h, "titulo": ""} for h in dict.fromkeys(re.findall(r"highlight:\d+", texto))]

                print(f"Baixando posts (ate {LIMITE_POSTS})...")
                posts = etapa("posts", lambda: rolar_e_coletar(page, captura, ("ProfilePosts",), LIMITE_POSTS),
                              erros) or []
                salvar_json(salvar_midias(context, posts, pastas["posts"], "post"), pastas["posts"] / "posts.json")

                print(f"Baixando reels (ate {LIMITE_REELS})...")
                captura.limpar()
                page.goto(f"{url_alvo}reels/", wait_until="load", timeout=60000)
                page.wait_for_timeout(6000)
                reels = etapa("reels", lambda: rolar_e_coletar(page, captura, ("Reels", "Clips"), LIMITE_REELS),
                              erros) or []
                salvar_json(salvar_midias(context, reels, pastas["reels"], "reel"), pastas["reels"] / "reels.json")
                if not reels:
                    print("  nenhum reel encontrado.")

                print("Baixando stories ativos...")
                stories = []
                if uid:
                    captura.limpar()
                    page.goto(f"https://www.instagram.com/stories/{username}/", wait_until="load", timeout=60000)
                    page.wait_for_timeout(5000)
                    if "/stories/" in page.url:
                        reels_story = {}
                        for doc in json_embutido(page) + [d for _, d in captura.docs]:
                            achar_reels_de_story(doc, reels_story)
                        stories = (reels_story.get(uid) or {}).get("items", [])
                salvar_json(salvar_midias(context, stories, pastas["stories"], "story"),
                            pastas["stories"] / "stories.json")
                if not stories:
                    print("  nenhum story ativo agora.")

                print(f"Baixando destaques ({len(bandeja)})...")
                resumo_destaques = []
                for d in bandeja:
                    numero = d["id"].split(":")[-1]
                    captura.limpar()
                    page.goto(f"https://www.instagram.com/stories/highlights/{numero}/", wait_until="load", timeout=60000)
                    page.wait_for_timeout(5000)
                    reels_story = {}
                    for doc in json_embutido(page) + [x for _, x in captura.docs]:
                        achar_reels_de_story(doc, reels_story)
                    reel = reels_story.get(d["id"]) or {}
                    nome = d["titulo"] or reel.get("title") or ""
                    pasta_nome = "".join(ch for ch in nome if ch.isalnum() or ch in " -_").strip()
                    pasta_d = pastas["destaques"] / (f"{pasta_nome}_{numero[-4:]}" if pasta_nome else numero)
                    pasta_d.mkdir(exist_ok=True)
                    registros = salvar_midias(context, reel.get("items", []), pasta_d, "destaque", detalhado=False)
                    salvar_json(registros, pasta_d / "destaque.json")
                    print(f"  destaque '{nome or numero}': {sum(len(r['arquivos']) for r in registros)} arquivo(s)")
                    resumo_destaques.append({"titulo": nome, "itens": len(registros)})
                dados_gerais["destaques"] = resumo_destaques

                if uid:
                    page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3000)
                    # Lista da coleta anterior, para saber quem deixou de seguir.
                    anterior = ler_json(PASTA_PERFIL / "seguidores.json", [])
                    seguidores_antes = {
                        "usuarios": [u["usuario"] for u in anterior if isinstance(u, dict) and u.get("usuario")],
                        "completa": ler_json(PASTA_PERFIL / "unfollowers_followed.json", {}).get("listas_completas"),
                    }
                    print("Extraindo seguidores (lista completa)...")
                    seguidores = etapa("seguidores", lambda: buscar_lista(page, uid, "followers"), erros)
                    if seguidores is not None:
                        salvar_json(seguidores[0], PASTA_PERFIL / "seguidores.json")
                    print("Extraindo seguindo (lista completa)...")
                    seguindo = etapa("seguindo", lambda: buscar_lista(page, uid, "following"), erros)
                    if seguindo is not None:
                        salvar_json(seguindo[0], PASTA_PERFIL / "seguindo.json")
                    if seguidores is not None and seguindo is not None:
                        gerar_depara(PASTA_PERFIL, username, seguidores, seguindo, seguidores_antes,
                                     {"seguidores": dados_gerais.get("seguidores"),
                                      "seguindo": dados_gerais.get("seguindo")})

                dados_gerais["baixados"] = {
                    "posts": len(posts), "reels": len(reels), "stories": len(stories),
                    "destaques": sum(d["itens"] for d in resumo_destaques),
                }
        except Exception as e:
            print(f"Erro durante o acesso ao perfil: {e}")
            erros["acesso"] = str(e)

        browser.close()

    dados_gerais.pop("voce_segue", None)
    if erros:
        dados_gerais["avisos"] = erros

    # Histórico: os números de cada coleta ficam guardados para comparar com o tempo.
    ARQUIVO_JSON = PASTA_PERFIL / "historico_perfil.json"
    anterior = ler_json(ARQUIVO_JSON, {})
    historico = anterior.get("historico", []) if isinstance(anterior, dict) else []
    historico.append({k: dados_gerais.get(k) for k in ("data_coleta", "seguidores", "seguindo", "posts_count")})
    dados_gerais["historico"] = historico
    salvar_json(dados_gerais, ARQUIVO_JSON)
    print(f"Dados gerais salvos em {ARQUIVO_JSON}")


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "cristiano"
    coletar_alvo(alvo.lstrip("@").strip())
