#!/bin/bash
# Script para gerar certificado TLS auto-assinado para desenvolvimento
# Para produção, use cert-manager com Let's Encrypt

set -e

DOMAIN="${1:-ludopedia-mcp.local}"
NAMESPACE="${2:-mcp-servers}"

echo "🔐 Gerando certificado TLS auto-assinado"
echo "   Domínio: $DOMAIN"
echo "   Namespace: $NAMESPACE"
echo ""

# Criar diretório para certificados
mkdir -p ./certs

# Gerar chave privada
openssl genrsa -out ./certs/tls.key 2048

# Gerar certificado auto-assinado (válido por 365 dias)
openssl req -new -x509 -sha256 \
  -key ./certs/tls.key \
  -out ./certs/tls.crt \
  -days 365 \
  -subj "/C=BR/ST=State/L=City/O=Organization/CN=$DOMAIN"

echo "✅ Certificados gerados em ./certs/"
echo ""
echo "📝 Criando Secret no Kubernetes..."

# Criar Secret TLS no Kubernetes
kubectl create secret tls ludopedia-mcp-tls \
  --cert=./certs/tls.crt \
  --key=./certs/tls.key \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml > ./deploy/tls-secret.yaml

echo "✅ Secret criado: ./deploy/tls-secret.yaml"
echo ""
echo "Para aplicar o secret:"
echo "  kubectl apply -f ./deploy/tls-secret.yaml"
echo ""
echo "⚠️  NOTA: Este é um certificado auto-assinado para desenvolvimento."
echo "   Para produção, use cert-manager com Let's Encrypt:"
echo "   https://cert-manager.io/docs/installation/"
