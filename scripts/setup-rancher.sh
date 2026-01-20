#!/bin/bash
# Script de setup automatizado para Rancher Desktop

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════╗
║   Ludopedia MCP Server - Setup Rancher       ║
╚═══════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Verificar se está no Rancher Desktop
echo "🔍 Verificando ambiente..."
if kubectl config current-context | grep -q "rancher-desktop"; then
    echo -e "${GREEN}✅ Rancher Desktop detectado${NC}"
else
    echo -e "${YELLOW}⚠️  Não está usando Rancher Desktop${NC}"
    read -p "Continuar mesmo assim? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi
echo ""

# Verificar dependências
echo "📦 Verificando dependências..."

command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker não encontrado${NC}"; exit 1; }
echo -e "${GREEN}✅ Docker${NC}"

command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}❌ kubectl não encontrado${NC}"; exit 1; }
echo -e "${GREEN}✅ kubectl${NC}"
echo ""

# Verificar Nginx Ingress
echo "🔌 Verificando Nginx Ingress Controller..."
if kubectl get namespace ingress-nginx >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Nginx Ingress já instalado${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx Ingress não encontrado${NC}"
    read -p "Instalar Nginx Ingress Controller? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 Instalando Nginx Ingress..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml
        echo "⏳ Aguardando Ingress Controller estar pronto..."
        kubectl wait --namespace ingress-nginx \
          --for=condition=ready pod \
          --selector=app.kubernetes.io/component=controller \
          --timeout=300s
        echo -e "${GREEN}✅ Nginx Ingress instalado${NC}"
    fi
fi
echo ""

# Build da imagem
echo "🐳 Fazendo build da imagem Docker..."
if [ -f "Makefile" ]; then
    make build
else
    docker build -t ludopedia-mcp-server:latest .
fi
echo -e "${GREEN}✅ Build concluído${NC}"
echo ""

# Criar namespace
echo "📁 Criando namespace..."
kubectl apply -f deploy/namespace.yaml
echo ""

# Gerar certificado TLS
echo "🔐 Configurando TLS..."
if [ -f "./certs/tls.crt" ] && [ -f "./certs/tls.key" ]; then
    echo -e "${YELLOW}⚠️  Certificados já existem${NC}"
    read -p "Gerar novos certificados? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./scripts/generate-tls-cert.sh ludopedia-mcp.local mcp-servers
    fi
else
    echo "Gerando certificado auto-assinado para desenvolvimento..."
    ./scripts/generate-tls-cert.sh ludopedia-mcp.local mcp-servers
fi
kubectl apply -f deploy/tls-secret.yaml
echo ""

# Deploy
echo "🚀 Fazendo deploy no Kubernetes..."
kubectl apply -f deploy/deployment.yaml
kubectl apply -f deploy/service.yaml
kubectl apply -f deploy/ingress.yaml
echo ""

echo "⏳ Aguardando pods estarem prontos..."
kubectl rollout status deployment/ludopedia-mcp-server -n mcp-servers --timeout=5m
echo ""

# Deploy HPA
read -p "Configurar auto-scaling (HPA)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Configurando HPA..."
    kubectl apply -f deploy/hpa.yaml
    echo -e "${GREEN}✅ HPA configurado${NC}"
fi
echo ""

# Status
echo "📊 Status do deployment:"
kubectl get all,ingress -n mcp-servers
echo ""

# Configuração do /etc/hosts para desenvolvimento
echo -e "${YELLOW}⚠️  IMPORTANTE: Configuração do /etc/hosts${NC}"
echo ""
echo "Para acessar via domínio local, adicione ao /etc/hosts:"
echo ""
echo "127.0.0.1 ludopedia-mcp.local"
echo ""
read -p "Adicionar automaticamente? (requer sudo) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if grep -q "ludopedia-mcp.local" /etc/hosts; then
        echo -e "${YELLOW}Entrada já existe no /etc/hosts${NC}"
    else
        echo "127.0.0.1 ludopedia-mcp.local" | sudo tee -a /etc/hosts
        echo -e "${GREEN}✅ /etc/hosts atualizado${NC}"
    fi
fi
echo ""

# Obter porta do Ingress (Rancher Desktop)
INGRESS_PORT=$(kubectl get service -n ingress-nginx ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}' 2>/dev/null || echo "443")

# Instruções finais
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════╗"
echo "║          ✅ SETUP CONCLUÍDO!                  ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "🌐 URLs de Acesso:"
echo ""
echo "   1. Health Check:"
echo "      kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000"
echo "      http://localhost:8000/health"
echo ""
echo "   2. MCP Server (SSE):"
echo "      kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000"
echo "      http://localhost:8000/sse"
echo ""
echo "   3. Via Ingress (se /etc/hosts configurado):"
echo "      https://ludopedia-mcp.local:$INGRESS_PORT/sse"
echo "      (Aceite o certificado auto-assinado)"
echo ""
echo "📝 Configuração do Claude Desktop:"
echo ""
echo "Edite o arquivo de configuração:"
echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  Windows: %APPDATA%/Claude/claude_desktop_config.json"
echo ""
echo "Adicione:"
cat << 'EOF'
{
  "mcpServers": {
    "ludopedia": {
      "url": "http://localhost:8000/sse",
      "transport": {
        "type": "sse",
        "headers": {
          "Authorization": "Bearer SEU_TOKEN_LUDOPEDIA"
        }
      }
    }
  }
}
EOF
echo ""
echo "🔑 Obter Token da Ludopedia:"
echo "   Execute: python get_token.py"
echo ""
echo "🧪 Para testar a instalação:"
echo "   ./scripts/test.sh"
echo ""
echo "📋 Para ver logs:"
echo "   kubectl logs -n mcp-servers -l app=ludopedia-mcp-server -f"
echo ""
echo "🔄 Para fazer port-forward permanente:"
echo "   kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000"
echo ""
echo "📚 Mais informações: Leia KUBERNETES.md"
echo ""
