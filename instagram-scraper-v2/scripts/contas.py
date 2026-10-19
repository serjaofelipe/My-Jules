"""Registro de várias contas do Instagram (uma sessão de login por conta).

- dados/contas.json: lista das contas e qual é a ativa.
- dados/contas/<id>.json: a sessão (storage_state) de cada conta.
- dados/estado_login.json: espelho da sessão da conta ATIVA (o coletar_dados
  usa esse arquivo; assim o resto do fluxo continua igual).

A sessão antiga solta (estado_login.json sem registro) é migrada para a
conta "Principal" na primeira vez que o registro é consultado.
"""

import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
PASTA_CONTAS = PASTA_DADOS / "contas"
REGISTRO = PASTA_DADOS / "contas.json"
ATIVA = PASTA_DADOS / "estado_login.json"  # sessão da conta ativa (compatibilidade)


def _ler(caminho, padrao):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def _salvar(caminho, dados):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def _slug(nome):
    base = "".join(c.lower() if c.isalnum() else "-" for c in (nome or "")).strip("-")
    return base or "conta"


def _id_unico(base, reg):
    usados = {c["id"] for c in reg["contas"]}
    if base not in usados:
        return base
    n = 2
    while f"{base}-{n}" in usados:
        n += 1
    return f"{base}-{n}"


def caminho(cid):
    return PASTA_CONTAS / f"{cid}.json"


def _usuario_da_sessao(storage):
    """Tenta achar o ds_user_id nos cookies (é um id, serve de referência)."""
    for c in (storage or {}).get("cookies", []):
        if c.get("name") == "ds_user_id":
            return c.get("value") or ""
    return ""


def _migrar(reg):
    # Sessão antiga solta vira a conta "Principal".
    if not reg["contas"] and ATIVA.exists():
        PASTA_CONTAS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ATIVA, caminho("principal"))
        reg["contas"].append({"id": "principal", "nome": "Principal",
                              "usuario": _usuario_da_sessao(_ler(ATIVA, {}))})
        reg["ativa"] = "principal"
        _salvar(REGISTRO, reg)
    return reg


def carregar():
    reg = _ler(REGISTRO, {})
    reg.setdefault("contas", [])
    reg.setdefault("ativa", None)
    return _migrar(reg)


def listar():
    return carregar()["contas"]


def ativa_id():
    return carregar().get("ativa")


def usar(cid):
    """Torna a conta ativa: espelha a sessão dela em estado_login.json."""
    reg = carregar()
    if cid not in {c["id"] for c in reg["contas"]}:
        raise ValueError(f"conta '{cid}' nao existe.")
    if caminho(cid).exists():
        shutil.copy2(caminho(cid), ATIVA)
    reg["ativa"] = cid
    _salvar(REGISTRO, reg)


def registrar(nome, storage_state):
    """Cria uma conta a partir de uma sessão recém-logada e a torna ativa."""
    reg = carregar()
    cid = _id_unico(_slug(nome), reg)
    _salvar(caminho(cid), storage_state)
    reg["contas"].append({"id": cid, "nome": nome or cid,
                          "usuario": _usuario_da_sessao(storage_state)})
    reg["ativa"] = cid
    _salvar(REGISTRO, reg)
    shutil.copy2(caminho(cid), ATIVA)
    return cid


def renomear(cid, nome):
    reg = carregar()
    for c in reg["contas"]:
        if c["id"] == cid:
            c["nome"] = nome or c["nome"]
            _salvar(REGISTRO, reg)
            return
    raise ValueError(f"conta '{cid}' nao existe.")


def remover(cid):
    reg = carregar()
    reg["contas"] = [c for c in reg["contas"] if c["id"] != cid]
    caminho(cid).unlink(missing_ok=True)
    if reg.get("ativa") == cid:
        reg["ativa"] = reg["contas"][0]["id"] if reg["contas"] else None
        if reg["ativa"] and caminho(reg["ativa"]).exists():
            shutil.copy2(caminho(reg["ativa"]), ATIVA)
        else:
            ATIVA.unlink(missing_ok=True)
    _salvar(REGISTRO, reg)


def sessoes_pool(excluir_ativa=True):
    """[(nome, caminho da sessão)] para juntar contas; a ativa primeiro.

    `excluir_ativa=True` tira a ativa (que já é usada pela página aberta),
    devolvendo só as contas extras que têm arquivo de sessão.
    """
    reg = carregar()
    ativa = reg.get("ativa")
    ordenadas = sorted(reg["contas"], key=lambda c: c["id"] != ativa)  # ativa primeiro
    saida = []
    for c in ordenadas:
        if excluir_ativa and c["id"] == ativa:
            continue
        if caminho(c["id"]).exists():
            saida.append((c["nome"], caminho(c["id"])))
    return saida
