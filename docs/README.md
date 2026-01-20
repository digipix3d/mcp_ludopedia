# 🎲 Ludopedia MCP Server

Servidor MCP (Model Context Protocol) completo para integração com a API da Ludopedia, disponível em duas versões:

1. **Versão Local (stdio)** - Para uso individual no Claude Desktop
2. **Versão Remota (SSE)** - Para deploy em Kubernetes/Rancher Desktop com suporte a múltiplos usuários

## 📦 O que há neste pacote?

```
.
├── README.md                          # Este arquivo
├── KUBERNETES.md                      # Guia completo para Kubernetes
│
├── ludopedia_mcp_server.py           # 🖥️  Versão LOCAL (stdio)
├── ludopedia_mcp_server_sse.py       # ☁️  Versão REMOTA (SSE/HTTPS)
├── get_token.py                       # Script para obter token OAuth
│
├── Dockerfile                         # Container para Kubernetes
├── docker-compose.yml                 # Teste local com Docker
├── Makefile                           # Comandos úteis
│
├── requirements.txt                   # Dependências versão local
├── requirements-sse.txt               # Dependências versão remota
├── pyproject.toml                     # Configuração Python
│
├── k8s/                               # 📁 Manifestos Kubernetes
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   └── cert-issuer.yaml
│
└── scripts/                           # 🛠️  Scripts utilitários
    ├── build.sh                       # Build Docker
    ├── deploy.sh                      # Deploy K8s
    ├── test.sh                        # Testes
    ├── generate-tls-cert.sh           # Gerar certificado
    └── setup-rancher.sh               # Setup automático
```

## 🚀 Quick Start

### Opção 1: Uso Local (Mais Simples)

Para usar apenas no seu Claude Desktop local:

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Obter token da Ludopedia
python get_token.py

# 3. Configurar Claude Desktop
# Edite claude_desktop_config.json e adicione:
{
  "mcpServers": {
    "ludopedia": {
      "command": "python",
      "args": ["/caminho/para/ludopedia_mcp_server.py"],
      "env": {
        "LUDOPEDIA_ACCESS_TOKEN": "seu_token_aqui"
      }
    }
  }
}

# 4. Reinicie o Claude Desktop
```

**📖 Guia completo:** Veja `README.md` na raiz

### Opção 2: Deploy em Kubernetes (Multi-usuário)

Para compartilhar entre múltiplos usuários via rede:

```bash
# Setup automático para Rancher Desktop
chmod +x scripts/*.sh
./scripts/setup-rancher.sh

# OU manual:
make build           # Build da imagem
make deploy          # Deploy no K8s
./scripts/test.sh    # Testar instalação
```

**📖 Guia completo:** Veja `KUBERNETES.md`

## 🎯 Comparação: Local vs Remoto

| Característica | Local (stdio) | Remoto (SSE/K8s) |
|----------------|---------------|------------------|
| **Usuários** | 1 usuário | Múltiplos usuários |
| **Instalação** | Simples | Moderada |
| **Requisitos** | Python + Claude Desktop | Docker + Kubernetes |
| **Rede** | Não requer | Requer servidor |
| **Protocolo** | stdio (pipes) | SSE via HTTPS |
| **Escalabilidade** | N/A | Auto-scaling (HPA) |
| **Alta disponibilidade** | N/A | Sim (múltiplas replicas) |
| **Ideal para** | Uso pessoal | Times/empresas |

## 🎲 Funcionalidades

Ambas as versões oferecem as mesmas ferramentas:

- ✅ **Buscar jogos** - Pesquisar por nome, designer, editora
- ✅ **Detalhes de jogos** - Informações completas
- ✅ **Gerenciar coleção** - Ver jogos (TENHO, QUERO, TIVE)
- ✅ **Partidas** - Listar e registrar partidas
- ✅ **Perfil** - Ver estatísticas pessoais
- ✅ **Rankings** - Rankings por categoria

## 📚 Documentação

- **README.md** (versão local) - Guia para uso individual
- **KUBERNETES.md** - Guia completo para deploy em Kubernetes
  - Setup em Rancher Desktop
  - Deploy em clusters cloud (AWS, GCP, Azure)
  - Configuração de TLS/HTTPS
  - Múltiplos usuários
  - Monitoramento e logs
  - Troubleshooting

## 🔑 Obter Token da Ludopedia

Ambas as versões precisam de um token OAuth da Ludopedia:

```bash
python get_token.py
```

O script irá:
1. Pedir suas credenciais de aplicativo Ludopedia
2. Abrir o navegador para autorização
3. Retornar seu token de acesso

**Criar aplicativo:** https://www.ludopedia.com.br/aplicativos

## 💡 Exemplos de Uso

Depois de configurado, converse naturalmente com o Claude:

```
"Busque jogos de Wingspan na Ludopedia"

"Quais jogos eu tenho na minha coleção?"

"Liste minhas últimas 10 partidas"

"Registre uma partida de Catan que joguei hoje com 4 jogadores"

"Qual é o ranking de jogos de estratégia?"

"Me mostre detalhes do jogo com ID 12345"
```

## 🛠️ Comandos Úteis (Makefile)

Para a versão Kubernetes, use o Makefile:

```bash
make help              # Ver todos os comandos
make build             # Build da imagem
make deploy            # Deploy no K8s
make status            # Ver status
make logs              # Ver logs
make port-forward      # Port forward para localhost
make test-k8s          # Testar no K8s
make scale REPLICAS=5  # Escalar manualmente
```

## 🔧 Estrutura das Versões

### Versão Local (stdio)

```python
# ludopedia_mcp_server.py
- Roda como processo Python
- Comunicação via stdio (pipes)
- Token via variável de ambiente
- 1 instância por usuário
```

**Configuração Claude Desktop:**
```json
{
  "mcpServers": {
    "ludopedia": {
      "command": "python",
      "args": ["/path/to/ludopedia_mcp_server.py"],
      "env": {
        "LUDOPEDIA_ACCESS_TOKEN": "seu_token"
      }
    }
  }
}
```

### Versão Remota (SSE)

```python
# ludopedia_mcp_server_sse.py
- Roda como servidor HTTP (FastAPI)
- Comunicação via SSE (Server-Sent Events)
- Token via header Authorization
- Múltiplos usuários simultâneos
- Deploy em Kubernetes
```

**Configuração Claude Desktop:**
```json
{
  "mcpServers": {
    "ludopedia": {
      "url": "https://ludopedia-mcp.seudominio.com/sse",
      "transport": {
        "type": "sse",
        "headers": {
          "Authorization": "Bearer seu_token"
        }
      }
    }
  }
}
```

## 🐳 Docker

### Teste Rápido com Docker

```bash
# Build
docker build -t ludopedia-mcp-server .

# Run (substitua SEU_TOKEN)
docker run -p 8000:8000 ludopedia-mcp-server

# Ou use docker-compose
docker-compose up -d
```

### Health Check

```bash
curl http://localhost:8000/health
```

## ☸️ Kubernetes

### Deploy Rápido

```bash
# Setup automático (Rancher Desktop)
./scripts/setup-rancher.sh

# OU passo a passo
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### Verificar Status

```bash
kubectl get all -n mcp-servers
```

### Port Forward

```bash
kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000
```

## 🔐 Segurança

### Versão Local
- Token armazenado em variável de ambiente local
- Sem exposição de rede

### Versão Remota
- TLS/HTTPS obrigatório (via Ingress)
- Token por usuário (via header)
- Container non-root (UID 1000)
- Filesystem read-only
- Network policies opcionais

## 📊 Monitoramento

### Logs

```bash
# Versão local
# Ver logs no terminal

# Versão remota
kubectl logs -n mcp-servers -l app=ludopedia-mcp-server -f
```

### Métricas (Kubernetes)

```bash
kubectl top pods -n mcp-servers
```

## 🧪 Testes

### Teste Versão Local

```bash
# Definir token
export LUDOPEDIA_ACCESS_TOKEN="seu_token"

# Rodar servidor
python ludopedia_mcp_server.py

# Em outro terminal, testar com Claude Desktop
```

### Teste Versão Remota

```bash
# Teste automatizado
./scripts/test.sh

# Teste manual
kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000
curl -H "Authorization: Bearer seu_token" http://localhost:8000/health
```

## 🐛 Troubleshooting

### Versão Local

**Erro: Token não encontrado**
```bash
# Verificar variável de ambiente
echo $LUDOPEDIA_ACCESS_TOKEN

# Ou no config do Claude Desktop
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Claude não vê o servidor**
- Verifique o caminho no config
- Python está no PATH?
- Reiniciou o Claude Desktop?

### Versão Remota

**Pods não iniciam**
```bash
kubectl describe pod -n mcp-servers <pod-name>
kubectl logs -n mcp-servers <pod-name>
```

**Erro 401 (Unauthorized)**
- Token correto no Claude Desktop config?
- Header Authorization está sendo enviado?

**SSE não funciona**
- Verifique annotations do Ingress
- `proxy-buffering` deve ser "off"

## 📖 Recursos

- [Ludopedia](https://ludopedia.com.br)
- [API Ludopedia](https://ludopedia.com.br/api/documentacao.html)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude Desktop](https://claude.ai/download)
- [Rancher Desktop](https://rancherdesktop.io/)
- [Kubernetes](https://kubernetes.io/)

## 🤝 Contribuindo

Melhorias são bem-vindas! Considere adicionar:

**Para ambas versões:**
- Mais endpoints da API Ludopedia
- Melhor formatação de respostas
- Cache de requisições
- Testes automatizados

**Para versão remota:**
- Prometheus metrics
- Grafana dashboards
- Rate limiting
- Redis cache
- CI/CD pipelines

## 📄 Licença

MIT

## ✨ Próximos Passos

### Se escolheu versão LOCAL:
1. ✅ Instale dependências: `pip install -r requirements.txt`
2. ✅ Obtenha token: `python get_token.py`
3. ✅ Configure Claude Desktop
4. ✅ Leia `README.md` para mais detalhes

### Se escolheu versão REMOTA:
1. ✅ Verifique pré-requisitos (Docker, Kubernetes)
2. ✅ Execute setup: `./scripts/setup-rancher.sh`
3. ✅ Configure Claude Desktop com URL remota
4. ✅ Leia `KUBERNETES.md` para configuração avançada

## 🎉 Pronto para Usar!

Agora você tem um MCP Server completo para integrar o Claude com a Ludopedia!

**Dúvidas?** Leia a documentação detalhada ou abra uma issue.

**Funcionou?** Compartilhe suas experiências!

---

*Feito com ❤️ para a comunidade Ludopedia e Claude*
