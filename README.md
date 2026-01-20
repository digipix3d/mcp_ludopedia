# 🎲 Ludopedia MCP Server

Servidor MCP (Model Context Protocol) para integração com a API da Ludopedia, permitindo que assistentes de IA como Claude consultem informações sobre jogos de tabuleiro.

## 📁 Estrutura do Projeto

```
.
├── src/                          # 🐍 Código fonte MCP
│   ├── ludopedia_mcp_server_sse.py
│   └── requirements-sse.txt
│
├── docker/                       # 🐳 Containerização
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── deploy/                       # ☸️ Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   └── cert-issuer.yaml
│
├── scripts/                      # 🛠️ Scripts de automação
│   ├── build.sh
│   ├── deploy.sh
│   ├── test.sh
│   ├── setup-rancher.sh
│   └── generate-tls-cert.sh
│
├── docs/                         # 📚 Documentação
│   ├── README.md
│   └── KUBERNETES.md
│
├── Makefile                      # ⚡ Comandos úteis
└── README.md                     # Este arquivo
```

## 🚀 Quick Start

### Desenvolvimento Local

```bash
# Instalar dependências
pip install -r src/requirements-sse.txt

# Rodar servidor
python src/ludopedia_mcp_server_sse.py
```

### Docker

```bash
# Build
make build

# Rodar localmente
docker-compose -f docker/docker-compose.yml up
```

### Kubernetes

```bash
# Setup completo (Rancher Desktop)
./scripts/setup-rancher.sh

# Ou manual
make deploy
```

## 📖 Documentação Completa

- **[docs/README.md](docs/README.md)** - Guia completo de uso
- **[docs/KUBERNETES.md](docs/KUBERNETES.md)** - Deploy em Kubernetes

## 🎯 Funcionalidades

- 🔍 Buscar jogos por nome, designer, editora
- 📊 Consultar detalhes completos de jogos
- ⭐ Ver avaliações e comentários
- 📝 Gerenciar coleções pessoais
- 👥 Consultar perfis de usuários
- 🏆 Acessar rankings

## 🛠️ Comandos Úteis (Make)

```bash
make help           # Lista todos os comandos
make build          # Build da imagem Docker
make deploy         # Deploy no Kubernetes
make logs           # Ver logs dos pods
make status         # Status dos recursos
make test-k8s       # Testar instalação
```

## 📦 Tecnologias

- **MCP**: Model Context Protocol
- **Python**: FastAPI + httpx
- **Docker**: Containerização
- **Kubernetes**: Orquestração
- **SSE**: Server-Sent Events para streaming

## 📄 Licença

MIT License
