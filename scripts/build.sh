#!/bin/bash
# Script para build da imagem Docker

set -e

IMAGE_NAME="${1:-ludopedia-mcp-server}"
IMAGE_TAG="${2:-latest}"
FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

echo "🐳 Building Docker image: $FULL_IMAGE"
echo ""

# Build da imagem
docker build -t "$FULL_IMAGE" .

echo ""
echo "✅ Build concluído!"
echo ""
echo "📦 Imagem: $FULL_IMAGE"
echo ""
echo "🚀 Próximos passos:"
echo "   1. Para testar localmente:"
echo "      docker run -p 8000:8000 -e LUDOPEDIA_ACCESS_TOKEN=seu_token $FULL_IMAGE"
echo ""
echo "   2. Para carregar no Rancher Desktop:"
echo "      # A imagem já está disponível no Docker local do Rancher"
echo "      kubectl apply -f deploy/"
echo ""
echo "   3. Para fazer push para um registry:"
echo "      docker tag $FULL_IMAGE your-registry/$FULL_IMAGE"
echo "      docker push your-registry/$FULL_IMAGE"
