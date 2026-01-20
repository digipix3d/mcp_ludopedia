#!/bin/bash
# Script para deploy no Kubernetes

set -e

echo "🚀 Deploying Ludopedia MCP Server to Kubernetes"
echo ""

# Verificar se kubectl está disponível
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl não encontrado. Instale o kubectl primeiro."
    exit 1
fi

# Verificar conexão com cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Não foi possível conectar ao cluster Kubernetes."
    echo "   Verifique se o Rancher Desktop está rodando."
    exit 1
fi

echo "✅ Conectado ao cluster Kubernetes"
echo ""

# Criar namespace
echo "📁 Criando namespace..."
kubectl apply -f deploy/namespace.yaml

# Aguardar namespace estar pronto
kubectl wait --for=jsonpath='{.status.phase}'=Active namespace/mcp-servers --timeout=30s

echo ""
echo "🔐 Configurando TLS..."
echo "   Verifique se você já tem o secret TLS criado."
echo "   Se não, execute: ./scripts/generate-tls-cert.sh"
echo ""
read -p "Continuar com o deploy? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deploy cancelado."
    exit 0
fi

# Aplicar manifests
echo ""
echo "📦 Aplicando manifests..."

kubectl apply -f deploy/deployment.yaml
kubectl apply -f deploy/service.yaml
kubectl apply -f deploy/ingress.yaml

echo ""
echo "⏳ Aguardando deployment estar pronto..."
kubectl rollout status deployment/ludopedia-mcp-server -n mcp-servers --timeout=5m

echo ""
echo "✅ Deploy concluído!"
echo ""
echo "📊 Status do deployment:"
kubectl get deployment,pods,service,ingress -n mcp-servers

echo ""
echo "🌐 Para acessar o serviço:"
echo ""
echo "   1. Via Port Forward (desenvolvimento):"
echo "      kubectl port-forward -n mcp-servers svc/ludopedia-mcp-server 8000:8000"
echo "      URL: http://localhost:8000/sse"
echo ""
echo "   2. Via Ingress (configurado):"
echo "      URL: https://ludopedia-mcp.seudominio.com/sse"
echo "      (Configure o DNS para apontar para o IP do ingress)"
echo ""
echo "📝 Para configurar no Claude Desktop:"
echo '   {
     "mcpServers": {
       "ludopedia": {
         "url": "https://ludopedia-mcp.seudominio.com/sse",
         "transport": {
           "type": "sse",
           "headers": {
             "Authorization": "Bearer SEU_TOKEN_LUDOPEDIA"
           }
         }
       }
     }
   }'
echo ""
echo "🔍 Para ver logs:"
echo "   kubectl logs -n mcp-servers -l app=ludopedia-mcp-server -f"
