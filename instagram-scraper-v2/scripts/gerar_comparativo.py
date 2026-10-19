"""Compara os seguidores/seguindo de vários perfis já coletados.

Lê dados/<perfil>/Logs_json/{seguidores,seguindo}.json de cada perfil escolhido
e monta dados/Merge-<p1>-<p2>-.../comparativo.xlsx:

- Resumo: totais e tamanho das interseções.
- Seguidores (matriz) e Seguindo (matriz): cada usuário numa linha, uma coluna
  por perfil (marcada quando aquele perfil o tem), e "em quantos" — filtre por
  "em quantos = N" para o que é comum, "= 1" para o exclusivo.
- Com exatamente 2 perfis: abas de cruzamento (em comum, só de um, um segue e o
  outro não), já separadas.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from gerar_planilha import (BORDA, BRANCO, LARANJA, ROSA, ROSA_CLARO, ROXO,
                            _banner, _cabecalho, _fonte, _preencher, _sim_nao)

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"


def _ler_lista(caminho):
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except (OSError, ValueError):
        return []


def carregar_perfil(perfil):
    """Devolve {seguidores: {user: dados}, seguindo: {user: dados}} do perfil."""
    base = PASTA_DADOS / perfil / "Logs_json"
    saida = {}
    for qual, arq in (("seguidores", "seguidores.json"), ("seguindo", "seguindo.json")):
        saida[qual] = {u["usuario"]: u for u in _ler_lista(base / arq)
                       if isinstance(u, dict) and u.get("usuario")}
    return saida


def _nome_de(perfis_dados, user):
    for d in perfis_dados.values():
        for qual in ("seguidores", "seguindo"):
            reg = d[qual].get(user)
            if reg and reg.get("nome"):
                return reg["nome"]
    return ""


def _escrever_pessoas(ws, linha, pessoas, nomes):
    """Tabela #/usuario/nome a partir de `linha` (que já é o cabeçalho). Devolve próxima linha."""
    _cabecalho(ws, ["#", "Usuario", "Nome"], linha=linha)
    for n, user in enumerate(pessoas):
        r = linha + 1 + n
        fundo = _preencher(ROSA_CLARO if n % 2 else BRANCO)
        for c, valor in enumerate([n + 1, "@" + user, nomes.get(user, "")], 1):
            cel = ws.cell(row=r, column=c, value=valor)
            cel.font = _fonte(10)
            cel.fill = fundo
            cel.border = BORDA
            cel.alignment = Alignment(horizontal="center" if c == 1 else "left", vertical="center",
                                      indent=0 if c == 1 else 1)
    return linha + 1 + len(pessoas) + 2


def _aba_matriz(wb, titulo, qual, perfis, perfis_dados, nomes):
    ws = wb.create_sheet(titulo)
    ws.sheet_properties.tabColor = ROSA if qual == "seguidores" else LARANJA
    ncols = 3 + len(perfis)
    _banner(ws, titulo, "marque a coluna 'em quantos' para filtrar comum (=N) ou exclusivo (=1)", ncols)
    _cabecalho(ws, ["#", "Usuario", "Nome"] + perfis + ["em quantos"])

    todos = sorted({u for p in perfis for u in perfis_dados[p][qual]})
    linhas = []
    for user in todos:
        presenca = [("X" if user in perfis_dados[p][qual] else "") for p in perfis]
        linhas.append((user, presenca, sum(1 for x in presenca if x)))
    linhas.sort(key=lambda t: (-t[2], t[0].lower()))  # mais comuns primeiro

    for n, (user, presenca, quantos) in enumerate(linhas):
        r = 4 + n
        fundo = _preencher(ROSA_CLARO if n % 2 else BRANCO)
        valores = [n + 1, "@" + user, nomes.get(user, "")] + presenca + [quantos]
        for c, valor in enumerate(valores, 1):
            cel = ws.cell(row=r, column=c, value=valor)
            cel.font = _fonte(10, negrito=(c > 3 and c <= 3 + len(perfis) and valor == "X"))
            cel.fill = fundo
            cel.border = BORDA
            centro = c == 1 or c > 3
            cel.alignment = Alignment(horizontal="center" if centro else "left", vertical="center",
                                      indent=0 if centro else 1)
    larguras = [6, 26, 30] + [max(10, len(p) + 2) for p in perfis] + [12]
    for i, larg in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(i)].width = larg
    fim = 3 + len(linhas)
    ws.auto_filter.ref = f"A3:{get_column_letter(ncols)}{max(fim, 3)}"
    ws.freeze_panes = "D4"
    ws.sheet_view.showGridLines = False


def _aba_cruzamento(wb, titulo, qual, a, b, perfis_dados, nomes):
    """Só para 2 perfis: em comum, só de um, e (para seguindo) um segue e o outro não."""
    ws = wb.create_sheet(titulo)
    ws.sheet_properties.tabColor = ROXO
    _banner(ws, titulo, f"@{a}  ×  @{b}", 3)
    ca, cb = set(perfis_dados[a][qual]), set(perfis_dados[b][qual])
    if qual == "seguidores":
        secoes = [("Seguem os dois", sorted(ca & cb)),
                  (f"Só seguem @{a}", sorted(ca - cb)),
                  (f"Só seguem @{b}", sorted(cb - ca))]
    else:
        secoes = [("Os dois seguem", sorted(ca & cb)),
                  (f"@{a} segue e @{b} não", sorted(ca - cb)),
                  (f"@{b} segue e @{a} não", sorted(cb - ca))]
    r = 4
    for rotulo, pessoas in secoes:
        tit = ws.cell(row=r, column=1, value=f"{rotulo}  ({len(pessoas)})")
        tit.font = _fonte(13, ROXO, negrito=True)
        r = _escrever_pessoas(ws, r + 1, pessoas, nomes)
    for i, larg in enumerate([6, 28, 34], 1):
        ws.column_dimensions[get_column_letter(i)].width = larg
    ws.sheet_view.showGridLines = False


def _aba_resumo(wb, perfis, perfis_dados):
    ws = wb.create_sheet("Resumo", 0)
    ws.sheet_properties.tabColor = ROXO
    _banner(ws, "Comparativo de contas", " × ".join("@" + p for p in perfis)
            + f" · {datetime.now():%d/%m/%Y %H:%M}", 3)
    _cabecalho(ws, ["Perfil", "Seguidores", "Seguindo"])
    r = 4
    for n, p in enumerate(perfis):
        fundo = _preencher(ROSA_CLARO if n % 2 else BRANCO)
        for c, valor in enumerate(["@" + p, len(perfis_dados[p]["seguidores"]),
                                   len(perfis_dados[p]["seguindo"])], 1):
            cel = ws.cell(row=r, column=c, value=valor)
            cel.font = _fonte(10)
            cel.fill = fundo
            cel.border = BORDA
            cel.alignment = Alignment(horizontal="left" if c == 1 else "center", vertical="center",
                                      indent=1 if c == 1 else 0)
        r += 1

    inter_seg = set.intersection(*[set(perfis_dados[p]["seguidores"]) for p in perfis]) if perfis else set()
    inter_sgd = set.intersection(*[set(perfis_dados[p]["seguindo"]) for p in perfis]) if perfis else set()
    r += 1
    for rotulo, valor in [("Seguidores em comum (todos)", len(inter_seg)),
                          ("Seguindo em comum (todos)", len(inter_sgd))]:
        a = ws.cell(row=r, column=1, value=rotulo)
        a.font = _fonte(10, BRANCO, negrito=True)
        a.fill = _preencher(ROSA)
        a.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        a.border = BORDA
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        b = ws.cell(row=r, column=2, value=valor)
        b.font = _fonte(11, ROXO, negrito=True)
        b.alignment = Alignment(horizontal="center", vertical="center")
        b.border = BORDA
        ws.cell(row=r, column=3).border = BORDA
        r += 1
    for col, larg in (("A", 32), ("B", 16), ("C", 16)):
        ws.column_dimensions[col].width = larg
    ws.sheet_view.showGridLines = False


def gerar_comparativo(perfis, pasta_dados=PASTA_DADOS):
    """Monta a planilha comparativa. Devolve o caminho, ou (None, motivo) se faltar dado."""
    perfis = [p.lstrip("@").strip() for p in perfis if p.strip()]
    if len(perfis) < 2:
        return None, "escolha pelo menos 2 perfis."
    perfis_dados = {p: carregar_perfil(p) for p in perfis}
    vazios = [p for p in perfis if not perfis_dados[p]["seguidores"] and not perfis_dados[p]["seguindo"]]
    if vazios:
        return None, "sem listas coletadas para: " + ", ".join(vazios)

    nomes = {}
    for p in perfis:
        for qual in ("seguidores", "seguindo"):
            for user, reg in perfis_dados[p][qual].items():
                if reg.get("nome") and user not in nomes:
                    nomes[user] = reg["nome"]

    wb = Workbook()
    wb.remove(wb.active)
    _aba_resumo(wb, perfis, perfis_dados)
    _aba_matriz(wb, "Seguidores (matriz)", "seguidores", perfis, perfis_dados, nomes)
    _aba_matriz(wb, "Seguindo (matriz)", "seguindo", perfis, perfis_dados, nomes)
    if len(perfis) == 2:
        a, b = perfis
        _aba_cruzamento(wb, "Seguidores ×", "seguidores", a, b, perfis_dados, nomes)
        _aba_cruzamento(wb, "Seguindo ×", "seguindo", a, b, perfis_dados, nomes)

    pasta = Path(pasta_dados) / ("Merge-" + "-".join(perfis))
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "comparativo.xlsx"
    wb.save(destino)
    return destino, None


def perfis_coletados(pasta_dados=PASTA_DADOS):
    """Perfis que têm alguma lista salva (para o AJAXGRAM listar)."""
    saida = []
    for d in sorted(Path(pasta_dados).glob("*")):
        if not d.is_dir() or d.name.startswith(("Merge-", "contas")):
            continue
        logs = d / "Logs_json"
        if (logs / "seguidores.json").exists() or (logs / "seguindo.json").exists():
            saida.append(d.name)
    return saida


if __name__ == "__main__":
    alvos = [a for a in sys.argv[1:] if a.strip()]
    if not alvos:
        print("perfis com listas:", ", ".join(perfis_coletados()) or "(nenhum)")
        sys.exit(0)
    destino, erro = gerar_comparativo(alvos)
    print(f"Comparativo gerado em {destino}" if destino else f"Nao gerado: {erro}")
    sys.exit(0 if destino else 1)
