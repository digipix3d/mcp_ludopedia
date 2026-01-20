# Ludopedia MCP Server - Kubernetes Deployment

MCP Server para Ludopedia com suporte SSE (Server-Sent Events) via HTTPS, pronto para deploy em Kubernetes/Rancher Desktop com suporte a múltiplos usuários.

## 🏗️ Arquitetura

```
┌─────────────┐
│   Claude    │
│  Desktop    │
└─────┬───────┘
      │ HTTPS + SSE
      │ Authorization: Bearer <token>
      ▼
┌─────────────────────────────────┐
│        Kubernetes Cluster        │
│  ┌───────────────────────────┐  │
│  │    Nginx Ingress (TLS)    │  │
│  └───────────┬───────────────┘  │
│              │                   │
│  ┌───────────▼───────────────┐  │
│  │   Service (ClusterIP)     │  │
│  └───────────┬───────────────┘  │
│              │                   │
│  ┌───────────▼───────────────┐  │
│  │  Deployment (2+ replicas) │  │
│  │  ┌─────────────────────┐  │  │
│  │  │ ludopedia-mcp-server│  │  │
│  │  │   (FastAPI + SSE)   │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────┬───────────────┘  │
└──────────────┼───────────────────┘
               │
               ▼
        ┌──────────────┐
        │  Ludopedia   │
        │     API      │
        └──────────────┘
```

## 📋 Pré-requisitos

- **Docker** instalado
- **Kubernetes** (Rancher Desktop, minikube, ou cluster cloud)
- **kubectl** configurado
- **Nginx Ingress Controller** instalado no cluster
- Tokens de acesso da Ludopedia (um por usuário)

### Instalar Nginx Ingress no Rancher Desktop

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml
```

## 🚀 Quick Start

### 1. Build da Imagem Docker

```bash
chmod +x scripts/*.sh
./scripts/build.sh
```

Para Rancher Desktop, a imagem já estará disponível localmente.

### 2. Gerar Certificado TLS (Desenvolvimento)

```bash
./scripts/generate-tls-cert.sh ludopedia-mcp.local mcp-servers
kubectl apply -f k8s/tls-secret.yaml
```

**Para Produção:** Use cert-manager com Let's Encrypt (veja seção abaixo)

### 3. Deploy no Kubernetes

```bash
./scripts/deploy.sh
```

O script irá:
- Criar o namespace `mcp-servers`
- Fazer deploy do application
- Configurar Service e Ingress
- Aguardar até estar pronto

### 4. Verificar Deploy

```bash
kubectl get all -n mcp-servers
```

Você deve ver:
- Deployment com 2+ pods em Running
- Service ClusterIP
- Ingress configurado

## 🔧 Configuração

### Acessar o Serviço

#### Opção 1: Port Forward (Desenvolvimento)

```bash
kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000
```

URL: `http://localhost:8000/sse`

#### Opção 2: Ingress (Produção)

1. Configure DNS para apontar `ludopedia-mcp.seudominio.com` para o IP do Ingress:

```bash
kubectl get ingress -n mcp-servers
```

2. Acesse via: `https://ludopedia-mcp.seudominio.com/sse`

### Configurar no Claude Desktop

Edite o arquivo de configuração:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

#### Usando Port Forward (Desenvolvimento)

```json
{
  "mcpServers": {
    "ludopedia": {
      "url": "http://localhost:8000/sse",
      "transport": {
        "type": "sse",
        "headers": {
          "Authorization": "Bearer SEU_TOKEN_LUDOPEDIA_AQUI"
        }
      }
    }
  }
}
```

#### Usando Ingress (Produção)

```json
{
  "mcpServers": {
    "ludopedia": {
      "url": "https://ludopedia-mcp.seudominio.com/sse",
      "transport": {
        "type": "sse",
        "headers": {
          "Authorization": "Bearer SEU_TOKEN_LUDOPEDIA_AQUI"
        }
      }
    }
  }
}
```

## 👥 Múltiplos Usuários

Cada usuário deve ter seu próprio token da Ludopedia. Configure o Claude Desktop de cada usuário com seu token individual no header `Authorization`.

**Exemplo:**

```json
// Usuário 1
{
  "mcpServers": {
    "ludopedia": {
      "url": "https://ludopedia-mcp.seudominio.com/sse",
      "transport": {
        "type": "sse",
        "headers": {
          "Authorization": "Bearer token_usuario_1"
        }
      }
    }
  }
}

// Usuário 2
{
  "mcpServers": {
    "ludopedia": {
      "url": "https://ludopedia-mcp.seudominio.com/sse",
      "transport": {
        "type": "sse",
        "headers": {
          "Authorization": "Bearer token_usuario_2"
        }
      }
    }
  }
}
```

O servidor irá automaticamente:
- Validar o token
- Isolar as sessões de cada usuário
- Fazer requisições à API com o token correto

## 🔐 Configuração de TLS/HTTPS para Produção

### Usando cert-manager com Let's Encrypt

1. **Instalar cert-manager:**

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml
```

2. **Criar ClusterIssuer:**

```yaml
# k8s/cert-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: seu-email@exemplo.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

```bash
kubectl apply -f k8s/cert-issuer.yaml
```

3. **Atualizar Ingress:**

Descomente a linha no `k8s/ingress.yaml`:

```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

4. **Aplicar:**

```bash
kubectl apply -f k8s/ingress.yaml
```

O cert-manager irá automaticamente provisionar e renovar certificados.

## 📊 Monitoramento e Logs

### Ver Logs

```bash
# Todos os pods
kubectl logs -n mcp-servers -l app=ludopedia-mcp-server -f

# Pod específico
kubectl logs -n mcp-servers <pod-name> -f
```

### Health Check

```bash
kubectl exec -n mcp-servers <pod-name> -- curl http://localhost:8000/health
```

### Métricas

```bash
kubectl top pods -n mcp-servers
```

## 🔄 Scaling

### Manual

```bash
kubectl scale deployment ludopedia-mcp-server -n mcp-servers --replicas=5
```

### Auto-scaling (HPA)

O HPA está configurado para escalar entre 2-10 replicas baseado em CPU (70%) e memória (80%):

```bash
kubectl apply -f k8s/hpa.yaml
kubectl get hpa -n mcp-servers
```

## 🧪 Testes

### Teste Local com Docker Compose

```bash
docker-compose up -d
curl -H "Authorization: Bearer seu_token" http://localhost:8000/health
```

### Teste no Kubernetes

```bash
# Port forward
kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000

# Testar health check
curl http://localhost:8000/health

# Testar SSE endpoint (requer token válido)
curl -H "Authorization: Bearer seu_token" \
     -H "Accept: text/event-stream" \
     http://localhost:8000/sse
```

## 🔧 Troubleshooting

### Pods não iniciam

```bash
kubectl describe pod -n mcp-servers <pod-name>
kubectl logs -n mcp-servers <pod-name>
```

Problemas comuns:
- Imagem não encontrada (verifique imagePullPolicy)
- Recursos insuficientes (ajuste requests/limits)

### Ingress não funciona

```bash
kubectl get ingress -n mcp-servers
kubectl describe ingress ludopedia-mcp-server -n mcp-servers
```

Verifique:
- Nginx Ingress Controller está rodando
- DNS está configurado corretamente
- Certificado TLS está válido

### Erro 401 (Unauthorized)

- Verifique se o token está correto no Claude Desktop config
- Teste o token diretamente na API da Ludopedia
- Verifique se o header Authorization está sendo enviado

### SSE Connection não funciona

Verifique annotations do Ingress:
- `proxy-buffering: "off"` deve estar configurado
- `proxy-read-timeout` deve ser alto (3600)

## 📝 Estrutura do Projeto

```
.
├── Dockerfile                      # Container definition
├── docker-compose.yml              # Local testing
├── ludopedia_mcp_server_sse.py    # MCP Server com SSE
├── requirements-sse.txt            # Python dependencies
├── k8s/
│   ├── namespace.yaml             # Namespace
│   ├── deployment.yaml            # Deployment
│   ├── service.yaml               # Service
│   ├── ingress.yaml               # Ingress com TLS
│   ├── hpa.yaml                   # HorizontalPodAutoscaler
│   └── tls-secret.yaml            # TLS Secret (gerado)
└── scripts/
    ├── build.sh                   # Build Docker image
    ├── deploy.sh                  # Deploy to K8s
    └── generate-tls-cert.sh       # Generate TLS cert
```

## 🚀 Deploy em Cloud Providers

### AWS EKS

```bash
# Build e push para ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag ludopedia-mcp-server:latest <account>.dkr.ecr.us-east-1.amazonaws.com/ludopedia-mcp-server:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/ludopedia-mcp-server:latest

# Atualizar deployment.yaml com imagem do ECR
# Deploy
kubectl apply -f k8s/
```

### GCP GKE

```bash
# Build e push para GCR
docker tag ludopedia-mcp-server:latest gcr.io/<project-id>/ludopedia-mcp-server:latest
docker push gcr.io/<project-id>/ludopedia-mcp-server:latest

# Deploy
kubectl apply -f k8s/
```

### Azure AKS

```bash
# Build e push para ACR
az acr login --name <registry-name>
docker tag ludopedia-mcp-server:latest <registry-name>.azurecr.io/ludopedia-mcp-server:latest
docker push <registry-name>.azurecr.io/ludopedia-mcp-server:latest

# Deploy
kubectl apply -f k8s/
```

## 🔒 Segurança

- ✅ Container roda como usuário não-root (UID 1000)
- ✅ Filesystem read-only
- ✅ Capabilities dropped
- ✅ TLS/HTTPS obrigatório via Ingress
- ✅ Tokens individuais por usuário
- ✅ Network Policies podem ser adicionadas
- ✅ RBAC configurável

### Adicionar Network Policy (opcional)

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ludopedia-mcp-server
  namespace: mcp-servers
spec:
  podSelector:
    matchLabels:
      app: ludopedia-mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS para Ludopedia API
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

## 📚 Recursos Adicionais

- [MCP Documentation](https://modelcontextprotocol.io)
- [Ludopedia API](https://ludopedia.com.br/api/documentacao.html)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager](https://cert-manager.io/)

## 🤝 Contribuindo

Melhorias são bem-vindas! Considere adicionar:
- Prometheus metrics
- Grafana dashboards
- Rate limiting
- Cache Redis
- Backup/restore procedures

## 📄 Licença

MIT
