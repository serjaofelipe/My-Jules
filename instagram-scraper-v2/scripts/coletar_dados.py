"""Coleta um perfil do Instagram usando a sua sessão logada.

Mídia (fotos e vídeos de posts, reels, stories e destaques) é baixada nos
arquivos originais (.jpg / .mp4). Os .json guardam só dados de texto:
histórico do perfil, seguidores, seguindo, legendas/datas/curtidas e o
de-para unfollowers_followed.json (quem o perfil segue e não segue de volta).

Como funciona: o script navega pelo perfil como uma pessoa faria e lê os
dados que o próprio site do Instagram carrega (respostas GraphQL e o JSON
embutido no HTML). Os endereços antigos da API (/api/v1/feed/...) passaram
a devolver só a página HTML, por isso não são mais usados para mídia.

Por padrão posts, reels, stories e destaques vêm todos. Dá para pôr um teto
em posts/reels por variável de ambiente (LIMITE_POSTS, LIMITE_REELS); 0 = tudo.
"""

import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
ARQUIVO_ESTADO = PASTA_DADOS / "estado_login.json"
MODO_TESTE = os.environ.get("MODO_TESTE") == "1"

SEM_LIMITE = 10 ** 9  # "baixar tudo": rola até o Instagram parar de mandar mídia nova
# 0 (padrão) = sem limite; pode-se pôr um teto por variável de ambiente.
LIMITE_POSTS = int(os.environ.get("LIMITE_POSTS", "0")) or SEM_LIMITE
LIMITE_REELS = int(os.environ.get("LIMITE_REELS", "0")) or SEM_LIMITE
# Seguidores/seguindo vêm completos para o de-para (unfollowers_followed.json) ser confiável.
LIMITE_LISTA = int(os.environ.get("LIMITE_LISTA", "5000"))
PAUSA = 1.2  # segundos entre chamadas à API
DOWNLOADS_SIMULTANEOS = 6  # arquivos de mídia baixados ao mesmo tempo (CDN, não a API)
INDISPONIVEL = "Dado indisponivel"
UA_PADRAO = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# O que dá para escolher no AJAXGRAM (ou com --so na linha de comando).
OPCOES = ("posts", "reels", "stories", "destaques", "seguidores", "seguindo", "depara")


def novo_contexto(browser, **kwargs):
    """Contexto que se apresenta como Chrome comum.

    O modo invisível se identifica como "HeadlessChrome", e o Instagram
    bloqueia (429) a sessão logada quando vê isso.
    """
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          f"(KHTML, like Gecko) Chrome/{browser.version} Safari/537.36")
    return browser.new_context(user_agent=ua, locale="pt-BR",
                               viewport={"width": 1366, "height": 900}, **kwargs)


def abrir_navegador(p, headless):
    """Abre o Chrome instalado sem as marcas de automação.

    Com elas o reCAPTCHA do login reprova qualquer resposta, em loop.
    Sem Chrome instalado, cai no Chromium do Playwright.
    """
    opcoes = dict(headless=headless,
                  ignore_default_args=["--enable-automation"],
                  args=["--disable-blink-features=AutomationControlled"])
    try:
        return p.chromium.launch(channel="chrome", **opcoes)
    except Exception:
        return p.chromium.launch(**opcoes)


def tem_sessao(context):
    return any(c["name"] == "sessionid" for c in context.cookies())


# ---------------------------------------------------------------- login vindo do Chrome do usuário

PASTA_CHROME = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"


def perfis_do_chrome():
    """[(pasta do perfil, nome, e-mail)] dos perfis do Chrome instalado."""
    try:
        estado = json.loads((PASTA_CHROME / "Local State").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    cache = (estado.get("profile") or {}).get("info_cache") or {}
    return [(pasta, info.get("name") or pasta, info.get("user_name") or "") for pasta, info in cache.items()]


def importar_do_chrome(perfil):
    """Copia a sessão do Instagram de um perfil do Chrome para o estado_login.json.

    `perfil` é a pasta do perfil ("Profile 4") ou o e-mail da conta Google dele.
    O Chrome precisa estar fechado: aberto, ele trava o arquivo de cookies.
    Só os cookies do instagram.com são guardados; o resto do perfil não sai da cópia temporária.
    """
    import shutil
    import tempfile

    pasta = next((p for p, _, email in perfis_do_chrome() if perfil in (p, email)), None)
    if not pasta:
        raise RuntimeError(f"perfil do Chrome '{perfil}' nao encontrado.")
    origem = PASTA_CHROME / pasta
    temp = Path(tempfile.mkdtemp(prefix="ajaxgram_chrome_"))
    try:
        (temp / pasta / "Network").mkdir(parents=True)
        shutil.copy2(PASTA_CHROME / "Local State", temp / "Local State")
        try:
            shutil.copy2(origem / "Network" / "Cookies", temp / pasta / "Network" / "Cookies")
        except PermissionError:
            raise RuntimeError("feche o Chrome (todas as janelas) e tente de novo: "
                               "aberto, ele trava o arquivo de cookies.") from None
        shutil.copy2(origem / "Preferences", temp / pasta / "Preferences")

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(temp), channel="chrome", headless=True,
                args=[f"--profile-directory={pasta}"], ignore_default_args=["--enable-automation"])
            try:
                cookies = ctx.cookies("https://www.instagram.com")
            finally:
                ctx.close()
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    if not any(c["name"] == "sessionid" for c in cookies):
        raise RuntimeError(f"o perfil '{pasta}' do Chrome nao esta logado no Instagram.")
    PASTA_DADOS.mkdir(exist_ok=True)
    salvar_json({"cookies": cookies, "origins": []}, ARQUIVO_ESTADO)
    return pasta


def autenticar(p):
    browser = None
    context = None
    page = None

    if ARQUIVO_ESTADO.exists() and not MODO_TESTE:
        print("Sessao encontrada. Tentando usar o cache de login...")
        browser = abrir_navegador(p, headless=True)
        context = novo_contexto(browser, storage_state=str(ARQUIVO_ESTADO))
        page = context.new_page()
        page.goto("https://www.instagram.com/", wait_until="networkidle", timeout=60000)

        # A URL não serve de prova: deslogado, a home mostra o formulário sem redirecionar.
        if tem_sessao(context):
            print("Autenticacao com cache bem-sucedida.")
            return browser, context, page
        else:
            print("Cache expirado ou invalido. Faremos login novamente.")
            browser.close()
            ARQUIVO_ESTADO.unlink()

    if MODO_TESTE:
        print("Modo teste ativado: pulando login visual. Usaremos modo headless.")
        browser = abrir_navegador(p, headless=True)
        context = novo_contexto(browser)
        page = context.new_page()
        return browser, context, page

    print("=======================================")
    print("Aguardando voce fazer login no navegador...")
    print("O navegador fechara sozinho quando o feed do Instagram carregar.")
    print("=======================================")

    browser = abrir_navegador(p, headless=False)
    context = novo_contexto(browser)
    page = context.new_page()
    page.goto("https://www.instagram.com/accounts/login/")

    try:
        # Espera o cookie de sessão; a URL muda antes do login terminar (2FA, "salvar info"...).
        fim = time.time() + 300
        while not tem_sessao(context):
            if time.time() > fim:
                raise TimeoutError
            page.wait_for_timeout(1000)
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
    """Rola a página até ter `limite` mídias (ou até o fim, se limite for muito alto).

    Para após algumas rolagens seguidas sem mídia nova. A tolerância é maior
    quando se quer tudo, para um perfil grande não parar cedo numa carga lenta.
    """
    tolerancia = 5 if limite >= SEM_LIMITE else 3
    midias, parado = [], 0
    while parado < tolerancia:
        midias = unicos(m for d in captura.de(*consultas) for m in achar_midias(d))
        if len(midias) >= limite:
            break
        antes = len(midias)
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(3000)
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
    if res.get("redirecionado") and not isinstance(res["body"], dict):
        # Acontece até no próprio site: o Instagram desvia a lista para a página inicial.
        raise RuntimeError("o Instagram bloqueou esta lista para a sua sessao agora (ate o proprio site "
                           "recebe erro). Costuma ser temporario: tente de novo mais tarde.")
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
            return {status: r.status, body, redirecionado: r.redirected};
        }""",
        {"path": path, "form": form},
    )
    time.sleep(PAUSA)
    return res


# Cada passada pede a lista numa ordem/tamanho de página diferente. O Instagram manda
# a quantidade certa, mas as páginas se sobrepõem: umas contas vêm repetidas e outras
# nunca vêm, e cada ordem perde contas diferentes. Juntando as passadas a lista fecha
# (no teste: 783 de 790 seguidores e 258 de 259 seguindo; uma passada só dava ~650 e ~235).
PASSADAS_LISTA = [
    "count=50&order=date_followed_latest",
    "count=50&order=date_followed_earliest",
    "count=50",
    "count=12&search_surface=follow_list_page",
]


def buscar_lista(page, uid, qual, alvo=None):
    """Lista de seguidores/seguindo. Devolve (usuarios, completa?).

    `alvo` é o número que o perfil mostra: as passadas param ao alcançá-lo
    (ou quando uma passada não traz ninguém novo).
    """
    usuarios = {}
    completa = False
    for n, parametros in enumerate(PASSADAS_LISTA, 1):
        antes, max_id = len(usuarios), ""
        while len(usuarios) < LIMITE_LISTA:
            try:
                corpo = ig_api(page, f"/api/v1/friendships/{uid}/{qual}/?{parametros}"
                               + (f"&max_id={max_id}" if max_id else ""), tentativas=2)
            except RuntimeError as e:
                if not usuarios:
                    raise
                # Bloqueio no meio de uma passada extra: fica com o que as anteriores trouxeram.
                print(f"  [aviso] passada {n} interrompida ({e}). Ficando com {len(usuarios)}.")
                return list(usuarios.values())[:LIMITE_LISTA], False
            for u in corpo.get("users", []):
                if u.get("username") and u["username"] not in usuarios:
                    usuarios[u["username"]] = {"usuario": u["username"], "nome": u.get("full_name"),
                                               "privado": u.get("is_private"), "verificado": u.get("is_verified")}
            max_id = corpo.get("next_max_id")
            if not max_id:
                completa = True
                break
        novos = len(usuarios) - antes
        print(f"  passada {n}: {len(usuarios)}" + (f" de {alvo}" if isinstance(alvo, int) else "")
              + f" (+{novos})")
        if len(usuarios) >= LIMITE_LISTA or (isinstance(alvo, int) and len(usuarios) >= alvo):
            break
        if n > 1 and novos == 0:
            break  # o resto não aparece em nenhuma ordem (contas desativadas/restritas)
    return list(usuarios.values())[:LIMITE_LISTA], completa


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


def baixar_direto(url, destino):
    """Download sem passar pelo navegador; os links de mídia do CDN já vêm assinados."""
    if destino.exists() and destino.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA_PADRAO})
        with urllib.request.urlopen(req, timeout=120) as r:
            dados = r.read()
        if dados:
            destino.write_bytes(dados)
            return True
    except Exception:
        pass
    return False


def baixar_varios(context, tarefas):
    """Baixa [(url, destino)] em paralelo; o que falhar tenta de novo pelo navegador."""
    with ThreadPoolExecutor(DOWNLOADS_SIMULTANEOS) as ex:
        ok = list(ex.map(lambda t: baixar_direto(*t), tarefas))
    return [sim or baixar(context, url, destino) for sim, (url, destino) in zip(ok, tarefas)]


def data_de(item):
    ts = item.get("taken_at") or item.get("device_timestamp") or 0
    if ts > 10**11:  # alguns vêm em microssegundos
        ts //= 10**6
    return datetime.fromtimestamp(ts) if ts else datetime.now()


def salvar_midias(context, itens, pasta, tipo, detalhado=True):
    """Baixa a mídia de cada item e devolve os metadados (texto) para o JSON."""
    planos = []  # (item, quando, codigo, [(url, destino)])
    for item in itens:
        quando = data_de(item)
        codigo = item.get("code") or str(item.get("pk") or item.get("id", "")).split("_")[0]
        sufixos = len(item.get("carousel_media") or []) > 1
        tarefas = [(url, pasta / f"{quando:%Y-%m-%d_%H%M%S}_{codigo}{f'_{n}' if sufixos else ''}.{ext}")
                   for n, (url, ext) in enumerate(arquivos_da_midia(item), 1)]
        planos.append((item, quando, codigo, tarefas))
    todas = [t for *_, tarefas in planos for t in tarefas]
    baixou = dict(zip((d for _, d in todas), baixar_varios(context, todas)))

    registros = []
    for item, quando, codigo, tarefas in planos:
        arquivos = [d.name for _, d in tarefas if baixou[d]]
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


def lista_de_destaques(captura, page):
    """Destaques do perfil: a lista vem junto com a página do perfil."""
    bandeja = []
    for doc in captura.de("Highlights"):
        for edge in (achar_chave(doc, "edges") or []):
            node = edge.get("node") or {}
            if str(node.get("id", "")).startswith("highlight:"):
                bandeja.append({"id": node["id"], "titulo": node.get("title") or ""})
    if not bandeja:  # formato mudou: pega pelo menos os ids
        texto = json.dumps([d for _, d in captura.docs]) + page.content()
        bandeja = [{"id": h, "titulo": ""} for h in dict.fromkeys(re.findall(r"highlight:\d+", texto))]
    return bandeja


def esperar_reel_de_story(page, captura, reel_id, maximo=10):
    """Espera os dados do story/destaque chegarem (em vez de uma pausa fixa)."""
    fim = time.time() + maximo
    while True:
        reels_story = {}
        for _, doc in captura.docs:
            achar_reels_de_story(doc, reels_story)
        if reel_id not in reels_story:
            for doc in json_embutido(page):
                achar_reels_de_story(doc, reels_story)
        if reel_id in reels_story or time.time() > fim:
            return reels_story.get(reel_id) or {}
        page.wait_for_timeout(500)


def coletar_alvo(username, opcoes=OPCOES):
    opcoes = set(opcoes)
    if "depara" in opcoes:  # o de-para precisa das duas listas
        opcoes |= {"seguidores", "seguindo"}
    PASTA_PERFIL = PASTA_DADOS / username
    PASTA_LOGS = PASTA_PERFIL / "Logs_json"  # os JSONs de texto ficam juntos aqui
    pastas = {nome: PASTA_PERFIL / nome for nome in ("posts", "reels", "stories", "destaques")}
    PASTA_PERFIL.mkdir(parents=True, exist_ok=True)
    PASTA_LOGS.mkdir(exist_ok=True)
    for nome, pasta in pastas.items():
        if nome in opcoes:
            pasta.mkdir(exist_ok=True)

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
    baixados = {}

    with sync_playwright() as p:
        browser, context, page = autenticar(p)
        logado = tem_sessao(context)
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
            if not opcoes:
                print("Nada marcado para baixar: so os dados do perfil.")
            elif not logado:
                print("Sem login: baixando so os dados publicos do perfil.")
            elif dados_gerais.get("privado") and not dados_gerais.get("voce_segue"):
                print("Perfil privado que voce nao segue: so os dados publicos estao disponiveis.")
            else:
                bandeja = lista_de_destaques(captura, page) if "destaques" in opcoes else []

                if "posts" in opcoes:
                    print(f"Baixando posts ({'todos' if LIMITE_POSTS >= SEM_LIMITE else f'ate {LIMITE_POSTS}'})...")
                    posts = etapa("posts", lambda: rolar_e_coletar(page, captura, ("ProfilePosts",), LIMITE_POSTS),
                                  erros) or []
                    salvar_json(salvar_midias(context, posts, pastas["posts"], "post"), pastas["posts"] / "posts.json")
                    baixados["posts"] = len(posts)

                if "reels" in opcoes:
                    print(f"Baixando reels ({'todos' if LIMITE_REELS >= SEM_LIMITE else f'ate {LIMITE_REELS}'})...")
                    captura.limpar()
                    page.goto(f"{url_alvo}reels/", wait_until="load", timeout=60000)
                    page.wait_for_timeout(6000)
                    reels = etapa("reels", lambda: rolar_e_coletar(page, captura, ("Reels", "Clips"), LIMITE_REELS),
                                  erros) or []
                    salvar_json(salvar_midias(context, reels, pastas["reels"], "reel"), pastas["reels"] / "reels.json")
                    if not reels:
                        print("  nenhum reel encontrado.")
                    baixados["reels"] = len(reels)

                if "stories" in opcoes:
                    print("Baixando stories ativos...")
                    stories = []
                    if uid:
                        captura.limpar()
                        page.goto(f"https://www.instagram.com/stories/{username}/", wait_until="load", timeout=60000)
                        if "/stories/" in page.url:
                            stories = esperar_reel_de_story(page, captura, uid, maximo=8).get("items", [])
                    salvar_json(salvar_midias(context, stories, pastas["stories"], "story"),
                                pastas["stories"] / "stories.json")
                    if not stories:
                        print("  nenhum story ativo agora.")
                    baixados["stories"] = len(stories)

                if "destaques" in opcoes:
                    print(f"Baixando destaques ({len(bandeja)})...")
                    resumo_destaques = []
                    for i, d in enumerate(bandeja, 1):
                        numero = d["id"].split(":")[-1]
                        captura.limpar()
                        page.goto(f"https://www.instagram.com/stories/highlights/{numero}/", wait_until="load",
                                  timeout=60000)
                        reel = esperar_reel_de_story(page, captura, d["id"])
                        nome = d["titulo"] or reel.get("title") or ""
                        pasta_nome = "".join(ch for ch in nome if ch.isalnum() or ch in " -_").strip()
                        pasta_d = pastas["destaques"] / (f"{pasta_nome}_{numero[-4:]}" if pasta_nome else numero)
                        pasta_d.mkdir(exist_ok=True)
                        registros = salvar_midias(context, reel.get("items", []), pasta_d, "destaque",
                                                  detalhado=False)
                        salvar_json(registros, pasta_d / "destaque.json")
                        print(f"  [{i}/{len(bandeja)}] destaque '{nome or numero}': "
                              f"{sum(len(r['arquivos']) for r in registros)} arquivo(s)")
                        resumo_destaques.append({"titulo": nome, "itens": len(registros)})
                    dados_gerais["destaques"] = resumo_destaques
                    baixados["destaques"] = sum(d["itens"] for d in resumo_destaques)

                if uid and opcoes & {"seguidores", "seguindo"}:
                    page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3000)
                    # Lista da coleta anterior, para saber quem deixou de seguir.
                    anterior = ler_json(PASTA_LOGS / "seguidores.json", [])
                    seguidores_antes = {
                        "usuarios": [u["usuario"] for u in anterior if isinstance(u, dict) and u.get("usuario")],
                        "completa": ler_json(PASTA_LOGS / "unfollowers_followed.json", {}).get("listas_completas"),
                    }
                    seguidores = seguindo = None
                    if "seguidores" in opcoes:
                        print("Extraindo seguidores (lista completa)...")
                        seguidores = etapa("seguidores", lambda: buscar_lista(
                            page, uid, "followers", dados_gerais.get("seguidores")), erros)
                        if seguidores is not None:
                            salvar_json(seguidores[0], PASTA_LOGS / "seguidores.json")
                            print(f"  {len(seguidores[0])} seguidores salvos.")
                    if "seguindo" in opcoes:
                        print("Extraindo seguindo (lista completa)...")
                        seguindo = etapa("seguindo", lambda: buscar_lista(
                            page, uid, "following", dados_gerais.get("seguindo")), erros)
                        if seguindo is not None:
                            salvar_json(seguindo[0], PASTA_LOGS / "seguindo.json")
                            print(f"  {len(seguindo[0])} perfis em seguindo salvos.")
                    if "depara" in opcoes:
                        if seguidores is not None and seguindo is not None:
                            gerar_depara(PASTA_LOGS, username, seguidores, seguindo, seguidores_antes,
                                         {"seguidores": dados_gerais.get("seguidores"),
                                          "seguindo": dados_gerais.get("seguindo")})
                        else:
                            print("[aviso] de-para nao gerado: uma das listas falhou.")

                if baixados:
                    dados_gerais["baixados"] = baixados
        except Exception as e:
            print(f"Erro durante o acesso ao perfil: {e}")
            erros["acesso"] = str(e)

        browser.close()

    dados_gerais.pop("voce_segue", None)
    if erros:
        dados_gerais["avisos"] = erros

    # Histórico: os números de cada coleta ficam guardados para comparar com o tempo.
    ARQUIVO_JSON = PASTA_LOGS / "historico_perfil.json"
    anterior = ler_json(ARQUIVO_JSON, {})
    historico = anterior.get("historico", []) if isinstance(anterior, dict) else []
    # Coleta que não conseguiu ler os números não entra no histórico.
    if isinstance(dados_gerais.get("seguidores"), int):
        historico.append({k: dados_gerais.get(k) for k in ("data_coleta", "seguidores", "seguindo", "posts_count")})
    dados_gerais["historico"] = historico
    salvar_json(dados_gerais, ARQUIVO_JSON)
    print(f"Dados gerais salvos em {ARQUIVO_JSON}")

    # Planilha estilizada a partir dos 4 JSONs.
    try:
        from gerar_planilha import gerar_planilha
        destino = gerar_planilha(PASTA_LOGS, PASTA_PERFIL / "Followers_Docs", username)
        if destino:
            print(f"Planilha gerada em {destino}")
    except Exception as e:
        print(f"[aviso] nao consegui gerar a planilha: {e}")

    if erros:
        print(f"Terminou com {len(erros)} aviso(s): {', '.join(erros)}")
    return not erros


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Coleta um perfil do Instagram.")
    ap.add_argument("perfil", nargs="?", default="cristiano")
    ap.add_argument("--so", default=",".join(OPCOES),
                    help=f"o que baixar, separado por virgula: {','.join(OPCOES)}")
    ap.add_argument("--importar-chrome", metavar="PERFIL",
                    help='so importa o login do Instagram de um perfil do Chrome ("Profile 4" ou o e-mail)')
    args = ap.parse_args()
    if args.importar_chrome:
        try:
            pasta = importar_do_chrome(args.importar_chrome)
        except Exception as e:
            print(f"Erro ao importar o login do Chrome: {e}")
            sys.exit(1)
        print(f"Login do Instagram importado do Chrome ({pasta}) e salvo com sucesso!")
        sys.exit(0)
    escolhidas = [o.strip() for o in args.so.split(",") if o.strip()]
    invalidas = [o for o in escolhidas if o not in OPCOES]
    if invalidas:
        ap.error(f"opcao desconhecida: {', '.join(invalidas)}")
    sys.exit(0 if coletar_alvo(args.perfil.lstrip("@").strip(), escolhidas) else 1)
