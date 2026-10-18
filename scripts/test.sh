#!/bin/bash
# Script de teste para validar a instalação do MCP Server

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

NAMESPACE="mcp-servers"
SERVICE_NAME="ludopedia-mcp-server"
TOKEN="${LUDOPEDIA_TOKEN:-}"

echo "🧪 Teste de Instalação - Ludopedia MCP Server"
echo "=============================================="
echo ""

# Função para imprimir resultados
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Teste 1: Verificar kubectl
echo "1️⃣  Verificando kubectl..."
if command -v kubectl &> /dev/null; then
    print_result 0 "kubectl instalado"
else
    print_result 1 "kubectl não encontrado"
    exit 1
fi
echo ""

# Teste 2: Verificar conexão com cluster
echo "2️⃣  Verificando conexão com cluster..."
if kubectl cluster-info &> /dev/null; then
    print_result 0 "Conectado ao cluster"
    kubectl cluster-info | grep "Kubernetes"
else
    print_result 1 "Não conectado ao cluster"
    exit 1
fi
echo ""

# Teste 3: Verificar namespace
echo "3️⃣  Verificando namespace..."
if kubectl get namespace $NAMESPACE &> /dev/null; then
    print_result 0 "Namespace $NAMESPACE existe"
else
    print_result 1 "Namespace $NAMESPACE não encontrado"
    echo "   Execute: kubectl apply -f deploy/namespace.yaml"
    exit 1
fi
echo ""

# Teste 4: Verificar deployment
echo "4️⃣  Verificando deployment..."
if kubectl get deployment $SERVICE_NAME -n $NAMESPACE &> /dev/null; then
    print_result 0 "Deployment existe"
    
    REPLICAS=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.replicas}')
    READY_REPLICAS=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
    
    echo "   Replicas: $READY_REPLICAS/$REPLICAS"
    
    if [ "$READY_REPLICAS" = "$REPLICAS" ]; then
        print_result 0 "Todas as replicas estão prontas"
    else
        print_result 1 "Algumas replicas não estão prontas"
        kubectl get pods -n $NAMESPACE
    fi
else
    print_result 1 "Deployment não encontrado"
    echo "   Execute: kubectl apply -f deploy/deployment.yaml"
    exit 1
fi
echo ""

# Teste 5: Verificar pods
echo "5️⃣  Verificando pods..."
PODS=$(kubectl get pods -n $NAMESPACE -l app=$SERVICE_NAME -o jsonpath='{.items[*].metadata.name}')
if [ -n "$PODS" ]; then
    print_result 0 "Pods encontrados"
    for POD in $PODS; do
        STATUS=$(kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.status.phase}')
        if [ "$STATUS" = "Running" ]; then
            echo "   ✅ $POD: $STATUS"
        else
            echo "   ❌ $POD: $STATUS"
        fi
    done
else
    print_result 1 "Nenhum pod encontrado"
    exit 1
fi
echo ""

# Teste 6: Verificar service
echo "6️⃣  Verificando service..."
if kubectl get service $SERVICE_NAME -n $NAMESPACE &> /dev/null; then
    print_result 0 "Service existe"
    kubectl get service $SERVICE_NAME -n $NAMESPACE
else
    print_result 1 "Service não encontrado"
    echo "   Execute: kubectl apply -f deploy/service.yaml"
    exit 1
fi
echo ""

# Teste 7: Verificar ingress
echo "7️⃣  Verificando ingress..."
if kubectl get ingress $SERVICE_NAME -n $NAMESPACE &> /dev/null; then
    print_result 0 "Ingress existe"
    kubectl get ingress $SERVICE_NAME -n $NAMESPACE
else
    echo -e "${YELLOW}⚠️  Ingress não encontrado (opcional)${NC}"
fi
echo ""

# Teste 8: Health check interno
echo "8️⃣  Testando health check interno..."
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=$SERVICE_NAME -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n $NAMESPACE $POD_NAME -- curl -sf http://localhost:8000/health &> /dev/null; then
    print_result 0 "Health check passou"
    kubectl exec -n $NAMESPACE $POD_NAME -- curl -s http://localhost:8000/health | head -n 5
else
    print_result 1 "Health check falhou"
fi
echo ""

# Teste 9: Health check via service
echo "9️⃣  Testando health check via service..."
if kubectl run test-curl-$RANDOM --rm -i --restart=Never --image=curlimages/curl -- \
    curl -sf http://$SERVICE_NAME.$NAMESPACE.svc.cluster.local:8000/health &> /dev/null; then
    print_result 0 "Acesso via service funcionando"
else
    print_result 1 "Acesso via service falhou"
fi
echo ""

# Teste 10: Verificar logs recentes
echo "🔟 Verificando logs recentes..."
echo "   Últimas 10 linhas de log:"
kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME --tail=10 | sed 's/^/   /'
echo ""

# Teste 11: Testar o endpoint MCP (se token fornecido)
if [ -n "$TOKEN" ]; then
    echo "1️⃣1️⃣  Testando endpoint MCP /mcp (com token)..."
    
    # Port forward temporário
    kubectl port-forward -n $NAMESPACE svc/$SERVICE_NAME 8000:8000 &
    PF_PID=$!
    sleep 3
    
    RESP=$(curl -sf -X POST http://localhost:8000/mcp \
        -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"meu_perfil","arguments":{}}}')
    if echo "$RESP" | grep -q '"id_usuario'; then
        print_result 0 "Ferramenta meu_perfil respondeu com o token"
    else
        print_result 1 "Ferramenta meu_perfil falhou: $RESP"
    fi
    
    # Matar port-forward
    kill $PF_PID 2>/dev/null || true
else
    echo -e "${YELLOW}1️⃣1️⃣  Teste MCP pulado (forneça LUDOPEDIA_TOKEN para testar)${NC}"
fi
echo ""

# Resumo
echo "=============================================="
echo "📊 RESUMO DOS TESTES"
echo "=============================================="
echo ""
echo "✅ Testes básicos passaram!"
echo ""
echo "🌐 Para acessar o serviço:"
echo ""
echo "   1. Port Forward (desenvolvimento):"
echo "      kubectl port-forward -n $NAMESPACE svc/$SERVICE_NAME 8000:8000"
echo "      URL: http://localhost:8000/mcp"
echo ""
echo "   2. Via Ingress (se configurado):"
INGRESS_HOST=$(kubectl get ingress $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
if [ -n "$INGRESS_HOST" ]; then
    echo "      URL: https://$INGRESS_HOST/mcp"
else
    echo "      Configure o Ingress primeiro"
fi
echo ""
echo "📝 Configuração do Claude Desktop:"
echo '   {
     "mcpServers": {
       "ludopedia": {
         "url": "http://localhost:8000/mcp",
         "transport": {
           "type": "streamable-http",
           "headers": {
             "Authorization": "Bearer SEU_TOKEN_AQUI"
           }
         }
       }
     }
   }'
echo ""
echo "🔍 Para ver logs em tempo real:"
echo "   kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME -f"
echo ""
