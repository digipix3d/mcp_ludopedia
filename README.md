# 🎲 Ludopedia MCP Server

Servidor MCP (Model Context Protocol) para a [API oficial da Ludopedia](https://ludopedia.com.br/api/documentacao.html). Com ele, assistentes de IA (Open WebUI, Claude e outros clientes MCP) consultam jogos, a sua coleção e as suas partidas, e registram partidas novas.

- **Transporte:** Streamable HTTP, endpoint `/mcp` (sem estado: funciona atrás de load balancer e com várias réplicas)
- **Autenticação:** cada cliente manda o próprio token no header `Authorization: Bearer <token>`. Para uso pessoal, também pode usar a variável `LUDOPEDIA_TOKEN`.
- **Saúde:** `GET /health`

## Ferramentas

| Ferramenta | O que faz | Rota da API |
|---|---|---|
| `buscar_jogo` | Busca jogos pelo nome (filtro base/expansão) | `GET /jogos` |
| `obter_jogo` | Ficha completa: jogadores, tempo, mecânicas, designers, link dos arquivos | `GET /jogos/{id}` |
| `listar_expansoes` | Expansões de um jogo base | `GET /jogos?id_jogo_base=` |
| `meu_perfil` | Usuário dono do token | `GET /me` |
| `minha_colecao` | Coleção, lista de desejos, favoritos, jogados etc. | `GET /colecao` |
| `minhas_partidas` | Partidas registradas (filtros por jogo, período, jogador) | `GET /partidas` |
| `resumo_partidas` | Resumo estatístico das partidas | `GET /partidas/resumo` |
| `estatisticas_partidas` | Partidas agrupadas por jogo, jogadores, dia da semana… | `GET /partidas/group` |
| `registrar_partida` | Registra uma partida (com confirmação em duas etapas) | `POST /partidas` |

### Registrar partida com segurança

`registrar_partida` grava dados na conta do usuário, por isso funciona em duas etapas:

1. Com `confirmar=false` (padrão), a ferramenta só devolve o resumo: o jogo encontrado, os jogadores e o vencedor. Nada é gravado.
2. Com `confirmar=true`, ela grava. O assistente só deve fazer essa chamada depois que o usuário confirmar o resumo.

Use o nome `"eu"` para o próprio usuário. A API exige que o dono do token esteja entre os jogadores, então o servidor o inclui automaticamente se ele faltar, e avisa no resumo.

## Rodando

### Docker (recomendado)

```bash
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8000/health
```

### Python

```bash
pip install -r src/requirements.txt
python src/ludopedia_mcp_server.py        # http://0.0.0.0:8000/mcp
```

Variáveis: `PORT` (8000), `HOST` (0.0.0.0), `LUDOPEDIA_TOKEN` (opcional, token padrão) e `LUDOPEDIA_API` (para testes).

### Kubernetes

Veja [docs/KUBERNETES.md](docs/KUBERNETES.md) (`make deploy`).

## Pegando o token

Em [ludopedia.com.br/aplicativos](https://ludopedia.com.br/aplicativos), crie um aplicativo. A página do app mostra o **access_token**, que dá acesso aos dados do dono do aplicativo.

## Conectando

### Open WebUI

**Painel de Administração → Configurações → Integrações (ou "Ferramentas externas") → Gerenciar servidores de ferramentas → +**

- Tipo: **MCP (Streamable HTTP)**
- URL: `http://host.docker.internal:8000/mcp` (ou o IP da máquina)
- Autenticação: **Bearer**, com o token da Ludopedia

Depois, ative as ferramentas no modelo desejado (Workspace → Modelos → Ferramentas) ou no botão de ferramentas do chat.

### Claude Code / outros clientes MCP

```bash
claude mcp add --transport http ludopedia http://localhost:8000/mcp --header "Authorization: Bearer SEU_TOKEN"
```

### Teste rápido sem cliente MCP

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'Authorization: Bearer SEU_TOKEN' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"meu_perfil","arguments":{}}}'
```

## Estrutura

```
src/ludopedia_mcp_server.py   servidor MCP
src/requirements.txt
docker/                       Dockerfile e docker-compose
deploy/                       manifests Kubernetes
scripts/                      build, deploy e testes
docs/                         guias
```

## Observações

- A API da Ludopedia está em estágio **ALPHA**. Os campos seguem o `openapi.yaml` oficial (versão 0.0.5).
- A API não dá acesso aos arquivos (manuais) dos jogos. `obter_jogo` devolve o link da aba **Arquivos**.
