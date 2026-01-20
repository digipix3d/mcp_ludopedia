#!/usr/bin/env python3
"""
MCP Server para Ludopedia com suporte SSE (Server-Sent Events)
Suporta múltiplos usuários com tokens individuais
"""
import asyncio
import os
import json
from typing import Any
import httpx
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.sse

# Configurações
LUDOPEDIA_API_BASE = "https://ludopedia.com.br/api/v1"
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# FastAPI app
app = FastAPI(title="Ludopedia MCP Server", version="1.0.0")

# MCP Server
mcp_server = Server("ludopedia-mcp-server")

# Armazenar clientes HTTP por usuário (cache de sessões)
http_clients: dict[str, httpx.AsyncClient] = {}


def get_auth_header(token: str) -> dict[str, str]:
    """Retorna o header de autenticação com o token OAuth"""
    return {"Authorization": f"Bearer {token}"}


def validate_token(token: str) -> bool:
    """Valida se o token está presente e não vazio"""
    return bool(token and token.strip())


async def get_http_client(user_token: str) -> httpx.AsyncClient:
    """Retorna ou cria um cliente HTTP para o usuário"""
    if user_token not in http_clients:
        http_clients[user_token] = httpx.AsyncClient(timeout=30.0)
    return http_clients[user_token]


async def make_api_request(
    user_token: str,
    endpoint: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Faz uma requisição para a API da Ludopedia"""
    client = await get_http_client(user_token)
    url = f"{LUDOPEDIA_API_BASE}{endpoint}"
    headers = get_auth_header(user_token)
    
    try:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {
            "error": f"Erro HTTP {e.response.status_code}",
            "detail": e.response.text
        }
    except Exception as e:
        return {"error": str(e)}


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Lista todas as ferramentas disponíveis"""
    return [
        types.Tool(
            name="buscar_jogo",
            description="Busca jogos na Ludopedia por nome ou termo de pesquisa",
            inputSchema={
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Termo de pesquisa (nome do jogo, designer, editora, etc.)"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de resultados (padrão: 10)",
                        "default": 10
                    }
                },
                "required": ["termo"]
            }
        ),
        types.Tool(
            name="obter_jogo",
            description="Obtém detalhes completos de um jogo específico pelo ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id_jogo": {
                        "type": "string",
                        "description": "ID do jogo na Ludopedia"
                    }
                },
                "required": ["id_jogo"]
            }
        ),
        types.Tool(
            name="minha_colecao",
            description="Obtém a lista de jogos da sua coleção",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filtrar por status (TENHO, QUERO, TIVE, JOGUEI, etc.)",
                        "enum": ["TENHO", "QUERO", "TIVE", "JOGUEI", "TODOS"]
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="minhas_partidas",
            description="Lista suas partidas registradas",
            inputSchema={
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de partidas (padrão: 20)",
                        "default": 20
                    },
                    "id_jogo": {
                        "type": "string",
                        "description": "Filtrar partidas de um jogo específico (opcional)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="registrar_partida",
            description="Registra uma nova partida jogada",
            inputSchema={
                "type": "object",
                "properties": {
                    "id_jogo": {
                        "type": "string",
                        "description": "ID do jogo na Ludopedia"
                    },
                    "data": {
                        "type": "string",
                        "description": "Data da partida (formato: YYYY-MM-DD)"
                    },
                    "duracao": {
                        "type": "integer",
                        "description": "Duração em minutos (opcional)"
                    },
                    "jogadores": {
                        "type": "array",
                        "description": "Lista de jogadores com pontuações",
                        "items": {
                            "type": "object",
                            "properties": {
                                "nome": {"type": "string"},
                                "pontuacao": {"type": "number"},
                                "vencedor": {"type": "boolean"}
                            }
                        }
                    }
                },
                "required": ["id_jogo", "data"]
            }
        ),
        types.Tool(
            name="meu_perfil",
            description="Obtém informações do seu perfil na Ludopedia",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="ranking_jogos",
            description="Obtém o ranking de jogos da Ludopedia",
            inputSchema={
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Categoria do ranking (geral, familia, estrategia, etc.)"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número de jogos (padrão: 50)",
                        "default": 50
                    }
                },
                "required": []
            }
        )
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Executa a ferramenta solicitada"""
    
    if arguments is None:
        arguments = {}
    
    # Extrair token do contexto (será injetado via SSE request)
    user_token = arguments.pop("_user_token", None)
    if not user_token:
        return [types.TextContent(
            type="text",
            text="Erro: Token de autenticação não fornecido"
        )]
    
    try:
        if name == "buscar_jogo":
            termo = arguments.get("termo", "")
            limite = arguments.get("limite", 10)
            
            result = await make_api_request(
                user_token,
                "/jogos",
                params={"search": termo, "limit": limite}
            )
            
            return [types.TextContent(
                type="text",
                text=f"Resultados da busca por '{termo}':\n\n{format_game_list(result)}"
            )]
        
        elif name == "obter_jogo":
            id_jogo = arguments.get("id_jogo")
            result = await make_api_request(user_token, f"/jogos/{id_jogo}")
            
            return [types.TextContent(
                type="text",
                text=format_game_details(result)
            )]
        
        elif name == "minha_colecao":
            status = arguments.get("status", "TODOS")
            params = {} if status == "TODOS" else {"status": status}
            
            result = await make_api_request(user_token, "/colecao", params=params)
            
            return [types.TextContent(
                type="text",
                text=f"Sua coleção (status: {status}):\n\n{format_collection(result)}"
            )]
        
        elif name == "minhas_partidas":
            limite = arguments.get("limite", 20)
            id_jogo = arguments.get("id_jogo")
            
            params = {"limit": limite}
            if id_jogo:
                params["id_jogo"] = id_jogo
            
            result = await make_api_request(user_token, "/partidas", params=params)
            
            return [types.TextContent(
                type="text",
                text=format_matches(result)
            )]
        
        elif name == "registrar_partida":
            result = await make_api_request(
                user_token,
                "/partidas",
                method="POST",
                json_data=arguments
            )
            
            return [types.TextContent(
                type="text",
                text=f"Partida registrada com sucesso!\n\n{result}"
            )]
        
        elif name == "meu_perfil":
            result = await make_api_request(user_token, "/me")
            
            return [types.TextContent(
                type="text",
                text=format_profile(result)
            )]
        
        elif name == "ranking_jogos":
            categoria = arguments.get("categoria", "geral")
            limite = arguments.get("limite", 50)
            
            result = await make_api_request(
                user_token,
                "/ranking",
                params={"categoria": categoria, "limit": limite}
            )
            
            return [types.TextContent(
                type="text",
                text=f"Ranking ({categoria}):\n\n{format_ranking(result)}"
            )]
        
        else:
            raise ValueError(f"Ferramenta desconhecida: {name}")
    
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Erro ao executar {name}: {str(e)}"
        )]


# Funções de formatação (mesmas do servidor stdio)
def format_game_list(data: dict) -> str:
    if "error" in data:
        return f"Erro: {data['error']}"
    if not data.get("jogos"):
        return "Nenhum jogo encontrado."
    games = []
    for jogo in data.get("jogos", []):
        games.append(
            f"• {jogo.get('nome', 'N/A')} "
            f"(ID: {jogo.get('id_jogo', 'N/A')}) - "
            f"Nota: {jogo.get('nota_media', 'N/A')}"
        )
    return "\n".join(games)


def format_game_details(data: dict) -> str:
    if "error" in data:
        return f"Erro: {data['error']}"
    details = [
        f"Nome: {data.get('nome', 'N/A')}",
        f"Ano: {data.get('ano', 'N/A')}",
        f"Designers: {', '.join(data.get('designers', []))}",
        f"Editoras: {', '.join(data.get('editoras', []))}",
        f"Jogadores: {data.get('num_jogadores', 'N/A')}",
        f"Duração: {data.get('tempo_jogo', 'N/A')} min",
        f"Idade mínima: {data.get('idade_minima', 'N/A')}",
        f"Nota média: {data.get('nota_media', 'N/A')}",
        f"Descrição: {data.get('descricao', 'N/A')}"
    ]
    return "\n".join(details)


def format_collection(data: dict) -> str:
    if "error" in data:
        return f"Erro: {data['error']}"
    if not data.get("jogos"):
        return "Sua coleção está vazia."
    games = []
    for jogo in data.get("jogos", []):
        games.append(
            f"• {jogo.get('nome', 'N/A')} - "
            f"Status: {jogo.get('status', 'N/A')}"
        )
    return "\n".join(games)


def format_matches(data: dict) -> str:
    if "error" in data:
        return f"Erro: {data['error']}"
    if not data.get("partidas"):
        return "Nenhuma partida encontrada."
    matches = []
    for partida in data.get("partidas", []):
        matches.append(
            f"• {partida.get('nome_jogo', 'N/A')} - "
            f"Data: {partida.get('data', 'N/A')} - "
            f"Duração: {partida.get('duracao', 'N/A')} min"
        )
    return "\n".join(matches)


def format_profile(data: dict) -> str:
    if "error" in data:
        return f"Erro: {data['error']}"
    profile = [
        f"Nome: {data.get('nome', 'N/A')}",
        f"Usuário: {data.get('usuario', 'N/A')}",
        f"Jogos na coleção: {data.get('num_jogos', 'N/A')}",
        f"Partidas registradas: {data.get('num_partidas', 'N/A')}"
    ]
    return "\n".join(profile)


def format_ranking(data: dict) -> str:
    if "error" in data:
        return f"Erro: {data['error']}"
    if not data.get("jogos"):
        return "Ranking não disponível."
    ranking = []
    for i, jogo in enumerate(data.get("jogos", []), 1):
        ranking.append(
            f"{i}. {jogo.get('nome', 'N/A')} - "
            f"Nota: {jogo.get('nota_media', 'N/A')}"
        )
    return "\n".join(ranking)


@app.get("/health")
async def health_check():
    """Health check endpoint para Kubernetes"""
    return {"status": "healthy", "service": "ludopedia-mcp-server"}


@app.get("/sse")
async def handle_sse(
    request: Request,
    authorization: str = Header(None)
):
    """
    Endpoint SSE para MCP
    O token deve ser passado no header Authorization: Bearer <token>
    """
    # Validar token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido. Use: Authorization: Bearer <seu_token>"
        )
    
    user_token = authorization.replace("Bearer ", "").strip()
    
    if not validate_token(user_token):
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação vazio ou inválido"
        )
    
    # Criar SSE transport com contexto do usuário
    async def sse_handler():
        async with mcp.server.sse.sse_server(
            read_stream=request.stream(),
            write_stream=None,  # SSE usa EventSourceResponse
        ) as streams:
            read_stream, write_stream = streams
            
            # Injetar token em todas as chamadas de ferramentas
            original_call_tool = mcp_server._request_handlers.get("tools/call")
            
            async def wrapped_call_tool(request_params):
                if "arguments" in request_params:
                    if request_params["arguments"] is None:
                        request_params["arguments"] = {}
                    request_params["arguments"]["_user_token"] = user_token
                return await original_call_tool(request_params)
            
            mcp_server._request_handlers["tools/call"] = wrapped_call_tool
            
            try:
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="ludopedia-mcp-server",
                        server_version="1.0.0",
                        capabilities=mcp_server.get_capabilities(
                            notification_options=None,
                            experimental_capabilities={},
                        ),
                    ),
                )
            finally:
                # Restaurar handler original
                mcp_server._request_handlers["tools/call"] = original_call_tool
    
    return EventSourceResponse(sse_handler())


@app.on_event("shutdown")
async def shutdown_event():
    """Limpar recursos ao desligar"""
    for client in http_clients.values():
        await client.aclose()
    http_clients.clear()


if __name__ == "__main__":
    import uvicorn
    
    print(f"🚀 Iniciando Ludopedia MCP Server (SSE)")
    print(f"   Host: {HOST}")
    print(f"   Port: {PORT}")
    print(f"   Endpoint SSE: http://{HOST}:{PORT}/sse")
    print(f"   Health Check: http://{HOST}:{PORT}/health")
    print()
    print("📡 Para conectar, use:")
    print(f"   URL: http://{HOST}:{PORT}/sse")
    print(f"   Header: Authorization: Bearer <seu_token_ludopedia>")
    print()
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
