#!/usr/bin/env python3
"""
Servidor MCP da Ludopedia (Streamable HTTP).

Rotas e campos seguem a especificação oficial: https://ludopedia.com.br/api/openapi.yaml (LudoAPI 0.0.5).

Autenticação: cada cliente manda o próprio token da Ludopedia no header
    Authorization: Bearer <access_token>
Se o header não vier, usa a variável de ambiente LUDOPEDIA_TOKEN (uso pessoal, um usuário só).

Endpoints:
    POST/GET /mcp   -> MCP (Streamable HTTP)
    GET /health     -> verificação de saúde
"""
from __future__ import annotations

import datetime as dt
import json
import os
import unicodedata
from typing import Annotated, Any, Literal

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

API = os.getenv("LUDOPEDIA_API", "https://ludopedia.com.br/api/v1").rstrip("/")
SITE = "https://ludopedia.com.br"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

mcp = FastMCP(
    "ludopedia",
    instructions=(
        "Ferramentas da Ludopedia (portal brasileiro de jogos de tabuleiro): buscar jogos, ver fichas, "
        "consultar a coleção e as partidas do usuário e registrar partidas. Para registrar uma partida, "
        "chame registrar_partida primeiro com confirmar=false, leia o resumo para o usuário e só chame de "
        "novo com confirmar=true depois que ele disser que está certo."
    ),
    host=HOST,
    port=PORT,
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

_http = httpx.AsyncClient(timeout=20.0)


# =========================================================================== infraestrutura
class LudopediaErro(Exception):
    pass


def _token(ctx: Context | None) -> str:
    try:
        req: Request | None = ctx.request_context.request if ctx else None  # type: ignore[union-attr]
        auth = req.headers.get("authorization", "") if req is not None else ""
    except Exception:  # noqa: BLE001 - fora de uma requisição HTTP (ex.: testes)
        auth = ""
    if auth.lower().startswith("bearer ") and auth[7:].strip():
        return auth[7:].strip()
    tk = os.getenv("LUDOPEDIA_TOKEN", "").strip()
    if not tk:
        raise LudopediaErro("Token da Ludopedia ausente: envie 'Authorization: Bearer <token>' "
                            "ou configure LUDOPEDIA_TOKEN no servidor.")
    return tk


async def _api(ctx: Context | None, metodo: str, caminho: str, params: dict | None = None,
               corpo: dict | None = None) -> Any:
    headers = {"Authorization": f"Bearer {_token(ctx)}", "Accept": "application/json"}
    params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    try:
        r = await _http.request(metodo, f"{API}{caminho}", params=params, json=corpo, headers=headers)
    except httpx.HTTPError as e:
        raise LudopediaErro(f"Ludopedia indisponível: {e}") from e
    texto = r.text
    try:
        dado = json.loads(texto) if texto.strip() else None  # o content-type deles vem como "aplication-json"
    except json.JSONDecodeError:
        dado = None
    if r.status_code in (401, 403):
        raise LudopediaErro("A Ludopedia recusou o token (inválido, expirado ou sem permissão).")
    if r.status_code >= 400:
        msg = (dado or {}).get("error") if isinstance(dado, dict) else None
        raise LudopediaErro(f"Ludopedia respondeu {r.status_code}: {msg or texto[:200]}")
    if isinstance(dado, dict) and dado.get("error"):
        raise LudopediaErro(f"Ludopedia: {dado['error']}")
    return dado


def _link(link: str | None) -> str | None:
    if not link:
        return None
    if link.startswith("https:") and not link.startswith("https://"):
        link = "https://" + link[6:].lstrip("/")
    return link if link.startswith("http") else f"{SITE}/{link.lstrip('/')}"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def _jogo_curto(j: dict) -> dict:
    return {k: v for k, v in {
        "id_jogo": j.get("id_jogo"),
        "nome": j.get("nm_jogo"),
        "nome_original": j.get("nm_original"),
        "ano": j.get("ano_publicacao"),
        "link": _link(j.get("link")),
        "thumb": j.get("thumb"),
    }.items() if v not in (None, "")}


def _erro(e: Exception) -> dict:
    return {"erro": str(e)}


# =========================================================================== jogos
@mcp.tool()
async def buscar_jogo(
    termo: Annotated[str, Field(description="Nome do jogo (ou parte dele)")],
    tipo: Annotated[Literal["todos", "base", "expansao"], Field(description="Filtrar por tipo")] = "todos",
    limite: Annotated[int, Field(ge=1, le=50)] = 10,
    ctx: Context | None = None,
) -> dict:
    """Busca jogos na Ludopedia pelo nome. Retorna id_jogo, nome, nome original, ano e link."""
    try:
        d = await _api(ctx, "GET", "/jogos", {
            "search": termo, "rows": limite, "tp_jogo": {"base": "b", "expansao": "e"}.get(tipo, "")})
        return {"total": d.get("total", 0), "jogos": [_jogo_curto(j) for j in d.get("jogos") or []]}
    except LudopediaErro as e:
        return _erro(e)


@mcp.tool()
async def obter_jogo(id_jogo: Annotated[int, Field(description="id_jogo na Ludopedia")],
                     ctx: Context | None = None) -> dict:
    """Ficha completa de um jogo: jogadores, tempo, idade, mecânicas, temas, designers e números da comunidade."""
    try:
        j = await _api(ctx, "GET", f"/jogos/{id_jogo}")
    except LudopediaErro as e:
        return _erro(e)
    nomes = lambda lista, campo: [x.get(campo) for x in (lista or []) if x.get(campo)]  # noqa: E731
    link = _link(j.get("link"))
    return {k: v for k, v in {
        **_jogo_curto(j),
        "tipo": {"b": "base", "e": "expansao"}.get(j.get("tp_jogo")),
        "ano_nacional": j.get("ano_nacional"),
        "jogadores": f"{j.get('qt_jogadores_min')}–{j.get('qt_jogadores_max')}" if j.get("qt_jogadores_min") else None,
        "tempo_min": j.get("vl_tempo_jogo"),
        "idade_minima": j.get("idade_minima"),
        "mecanicas": nomes(j.get("mecanicas"), "nm_mecanica"),
        "categorias": nomes(j.get("categorias"), "nm_categoria"),
        "temas": nomes(j.get("temas"), "nm_tema"),
        "designers": nomes(j.get("designers"), "nm_profissional"),
        "artistas": nomes(j.get("artistas"), "nm_profissional"),
        "comunidade": {k2: v2 for k2, v2 in {"tem": j.get("qt_tem"), "quer": j.get("qt_quer"),
                                             "favorito": j.get("qt_favorito"), "jogou": j.get("qt_jogou")}.items()
                       if v2 is not None} or None,
        "complexidade": (j.get("comunidade") or {}).get("vl_complexidade"),
        "arquivos": f"{link}/arquivos" if link else None,
    }.items() if v not in (None, "", [])}


@mcp.tool()
async def listar_expansoes(id_jogo_base: int, limite: Annotated[int, Field(ge=1, le=100)] = 30,
                           ctx: Context | None = None) -> dict:
    """Lista as expansões de um jogo base."""
    try:
        d = await _api(ctx, "GET", "/jogos", {"id_jogo_base": id_jogo_base, "tp_jogo": "e", "rows": limite})
        return {"total": d.get("total", 0), "expansoes": [_jogo_curto(j) for j in d.get("jogos") or []]}
    except LudopediaErro as e:
        return _erro(e)


# =========================================================================== usuário e coleção
@mcp.tool()
async def meu_perfil(ctx: Context | None = None) -> dict:
    """Dados do usuário dono do token (id_usuario, nome de usuário)."""
    try:
        return await _api(ctx, "GET", "/me")
    except LudopediaErro as e:
        return _erro(e)


@mcp.tool()
async def minha_colecao(
    lista: Annotated[Literal["colecao", "lista_desejos", "favoritos", "teve", "jogados", "notas", "comentados"],
                     Field(description="Qual lista da coleção")] = "colecao",
    busca: Annotated[str, Field(description="Filtrar pelo nome do jogo")] = "",
    tipo: Literal["todos", "base", "expansao"] = "todos",
    qt_jogadores: Annotated[int | None, Field(description="Só jogos que aceitam essa quantidade de jogadores")] = None,
    ordem: Literal["nome", "rank", "nota", "partidas"] = "nome",
    pagina: Annotated[int, Field(ge=1)] = 1,
    limite: Annotated[int, Field(ge=1, le=200)] = 50,
    ctx: Context | None = None,
) -> dict:
    """Jogos da coleção do usuário (ou lista de desejos, favoritos etc.), com nota e quantidade de partidas."""
    try:
        d = await _api(ctx, "GET", "/colecao", {
            "lista": lista, "search": busca, "ordem": ordem, "qt_jogadores": qt_jogadores,
            "tp_jogo": {"base": "b", "expansao": "e"}.get(tipo, "t"), "page": pagina, "rows": limite})
    except LudopediaErro as e:
        return _erro(e)
    itens = []
    for j in d.get("colecao") or []:
        itens.append({k: v for k, v in {
            "id_jogo": j.get("id_jogo"), "nome": j.get("nm_jogo"), "link": _link(j.get("link")),
            "nota": j.get("vl_nota"), "partidas": j.get("qt_partidas"),
            "tags": [t.get("nm_tag") or t for t in j.get("tags") or []] or None,
        }.items() if v not in (None, "")})
    return {"total": d.get("total"), "jogos_base": d.get("qt_base"), "expansoes": d.get("qt_exp"), "jogos": itens}


# =========================================================================== partidas
def _partida_curta(p: dict) -> dict:
    jogo = p.get("jogo") or {}
    return {k: v for k, v in {
        "id_partida": p.get("id_partida"),
        "data": p.get("dt_partida"),
        "jogo": jogo.get("nm_jogo"),
        "id_jogo": jogo.get("id_jogo"),
        "expansoes": [e.get("nm_jogo") for e in p.get("expansoes") or [] if e.get("nm_jogo")] or None,
        "duracao_min": p.get("duracao"),
        "descricao": p.get("descricao"),
        "jogadores": [{k2: v2 for k2, v2 in {
            "nome": j.get("nome"), "id_usuario": j.get("id_usuario"), "pontos": j.get("vl_pontos"),
            "vencedor": bool(j.get("fl_vencedor")), "observacao": j.get("observacao")}.items()
            if v2 not in (None, "")} for j in p.get("jogadores") or []],
    }.items() if v not in (None, "", [])}


@mcp.tool()
async def minhas_partidas(
    id_jogo: Annotated[int | None, Field(description="Só partidas deste jogo")] = None,
    desde: Annotated[str | None, Field(description="Data inicial yyyy-mm-dd")] = None,
    ate: Annotated[str | None, Field(description="Data final (exclusiva) yyyy-mm-dd")] = None,
    jogador: Annotated[str | None, Field(description="Nome de jogador sem cadastro no site")] = None,
    pagina: Annotated[int, Field(ge=1)] = 1,
    limite: Annotated[int, Field(ge=1, le=200)] = 20,
    ctx: Context | None = None,
) -> dict:
    """Partidas registradas pelo usuário, da mais recente para a mais antiga."""
    try:
        d = await _api(ctx, "GET", "/partidas", {"id_jogo": id_jogo, "dt_ini": desde, "dt_fim": ate,
                                                  "jogador": jogador, "page": pagina, "rows": limite})
        return {"total": d.get("total"), "partidas": [_partida_curta(p) for p in d.get("partidas") or []]}
    except LudopediaErro as e:
        return _erro(e)


@mcp.tool()
async def resumo_partidas(
    desde: Annotated[str | None, Field(description="Data inicial yyyy-mm-dd")] = None,
    ate: Annotated[str | None, Field(description="Data final (exclusiva) yyyy-mm-dd")] = None,
    id_jogo: int | None = None,
    ctx: Context | None = None,
) -> dict:
    """Resumo estatístico das partidas do usuário no período."""
    try:
        return await _api(ctx, "GET", "/partidas/resumo", {"dt_ini": desde, "dt_fim": ate, "id_jogo": id_jogo})
    except LudopediaErro as e:
        return _erro(e)


@mcp.tool()
async def estatisticas_partidas(
    agrupar_por: Annotated[str, Field(description="Um ou mais de: jogos, jogadores, qt_jogadores, expansoes, "
                                                  "diasemana, grupos (separados por |)")] = "jogos",
    desde: str | None = None,
    ate: str | None = None,
    limite: Annotated[int, Field(ge=1, le=200)] = 20,
    ctx: Context | None = None,
) -> dict:
    """Partidas agrupadas (ex.: jogos mais jogados, com quem mais joga)."""
    try:
        return await _api(ctx, "GET", "/partidas/group", {"groupby": agrupar_por, "dt_ini": desde, "dt_fim": ate,
                                                         "rows": limite})
    except LudopediaErro as e:
        return _erro(e)


class JogadorPartida(BaseModel):
    nome: str = Field(description="Nome do jogador. Use 'eu' para o próprio usuário do token.")
    pontos: int | None = Field(default=None, ge=-999, le=999)
    vencedor: bool = False
    observacao: str | None = Field(default=None, max_length=100, description="Cor, facção, personagem etc.")
    id_usuario: int | None = Field(default=None, description="Se o jogador for usuário da Ludopedia")


EU = {"eu", "eu mesmo", "me", "mim", "eu mesma"}


async def _resolver_jogo(ctx, jogo: str | int, tipo: str = "") -> dict:
    if isinstance(jogo, int) or str(jogo).strip().isdigit():
        j = await _api(ctx, "GET", f"/jogos/{int(jogo)}")
        return {"id_jogo": j["id_jogo"], "nm_jogo": j.get("nm_jogo")}
    d = await _api(ctx, "GET", "/jogos", {"search": str(jogo), "rows": 10, "tp_jogo": tipo})
    jogos = d.get("jogos") or []
    if not jogos:
        raise LudopediaErro(f"Não encontrei o jogo '{jogo}' na Ludopedia.")
    alvo = _norm(str(jogo))
    exato = [j for j in jogos if _norm(j.get("nm_jogo", "")) == alvo or _norm(j.get("nm_original", "")) == alvo]
    j = (exato or jogos)[0]
    return {"id_jogo": j["id_jogo"], "nm_jogo": j.get("nm_jogo")}


@mcp.tool()
async def registrar_partida(
    jogo: Annotated[str, Field(description="Nome do jogo ou id_jogo")],
    jogadores: Annotated[list[JogadorPartida], Field(description="Quem jogou. Inclua o usuário como nome 'eu'.")],
    data: Annotated[str | None, Field(description="yyyy-mm-dd; padrão: hoje")] = None,
    duracao_min: Annotated[int | None, Field(ge=1, le=1435)] = None,
    expansoes: Annotated[list[str] | None, Field(description="Nomes ou ids das expansões usadas")] = None,
    descricao: Annotated[str | None, Field(description="Observações sobre a partida")] = None,
    digital: bool = False,
    confirmar: Annotated[bool, Field(description="false = só mostra o resumo; true = grava na Ludopedia")] = False,
    ctx: Context | None = None,
) -> dict:
    """Registra uma partida na conta do usuário na Ludopedia.

    SEMPRE chame primeiro com confirmar=false: a ferramenta devolve o resumo do que será gravado (jogo
    encontrado, jogadores, vencedor). Leia o resumo para o usuário e só chame de novo com confirmar=true,
    com os mesmos dados, depois que ele confirmar.
    """
    try:
        me = await _api(ctx, "GET", "/me")
        j = await _resolver_jogo(ctx, jogo, "b")
        exps = [await _resolver_jogo(ctx, e, "e") for e in (expansoes or [])]
        lista, tem_eu = [], False
        for p in jogadores:
            eh_eu = _norm(p.nome) in EU or p.id_usuario == me.get("id_usuario")
            tem_eu = tem_eu or eh_eu
            lista.append({
                "id_partida_jogador": 0,
                "id_usuario": me["id_usuario"] if eh_eu else p.id_usuario,
                "nome": me.get("usuario") if eh_eu else p.nome,
                "fl_vencedor": 1 if p.vencedor else 0,
                "vl_pontos": p.pontos,
                "observacao": p.observacao,
            })
        aviso = None
        if not tem_eu:  # a API exige que o usuário do token esteja entre os jogadores
            lista.insert(0, {"id_partida_jogador": 0, "id_usuario": me["id_usuario"], "nome": me.get("usuario"),
                             "fl_vencedor": 0, "vl_pontos": None, "observacao": None})
            aviso = f"Você ({me.get('usuario')}) foi incluído como jogador, porque a Ludopedia exige isso."
        data = data or dt.date.today().isoformat()
        dt.date.fromisoformat(data)
        partida = {
            "id_partida": 0, "qt_partidas": 1, "fl_digital": 1 if digital else 0,
            "duracao": duracao_min, "dt_partida": data, "descricao": descricao,
            "jogo": {"id_jogo": j["id_jogo"]}, "expansoes": [{"id_jogo": e["id_jogo"]} for e in exps],
            "jogadores": lista,
        }
        resumo = {
            "jogo": j["nm_jogo"], "id_jogo": j["id_jogo"], "data": data, "duracao_min": duracao_min,
            "expansoes": [e["nm_jogo"] for e in exps] or None,
            "jogadores": [{"nome": x["nome"], "pontos": x["vl_pontos"], "vencedor": bool(x["fl_vencedor"]),
                           "observacao": x["observacao"]} for x in lista],
            "aviso": aviso,
        }
        if not confirmar:
            return {"status": "aguardando_confirmacao",
                    "mensagem": "Nada foi gravado ainda. Confirme com o usuário e chame de novo com confirmar=true.",
                    "resumo": {k: v for k, v in resumo.items() if v not in (None, [])}}
        r = await _api(ctx, "POST", "/partidas", corpo=partida)
        id_partida = (r[0] if isinstance(r, list) and r else r or {}).get("id_partida") if r else None
        return {"status": "registrada", "id_partida": id_partida,
                "resumo": {k: v for k, v in resumo.items() if v not in (None, [])}}
    except (LudopediaErro, ValueError, KeyError) as e:
        return _erro(e)


# =========================================================================== saúde
@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "ludopedia-mcp-server", "transport": "streamable-http"})


def app():
    """App ASGI (útil para rodar com uvicorn diretamente)."""
    return mcp.streamable_http_app()


if __name__ == "__main__":
    print(f"🎲 Ludopedia MCP Server em http://{HOST}:{PORT}/mcp  (saúde: /health)")
    mcp.run(transport="streamable-http")
