.PHONY: help build push deploy clean logs shell test port-forward

IMAGE_NAME ?= ludopedia-mcp-server
IMAGE_TAG ?= latest
NAMESPACE ?= mcp-servers
REGISTRY ?= localhost:5000

help: ## Mostra esta mensagem de ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build da imagem Docker
	@echo "🐳 Building Docker image..."
	docker build -f docker/Dockerfile -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "✅ Build concluído: $(IMAGE_NAME):$(IMAGE_TAG)"

build-push: build ## Build e push para registry
	@echo "📤 Pushing to registry..."
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✅ Push concluído!"

deploy: ## Deploy no Kubernetes
	@echo "🚀 Deploying to Kubernetes..."
	kubectl apply -f deploy/namespace.yaml
	kubectl apply -f deploy/deployment.yaml
	kubectl apply -f deploy/service.yaml
	kubectl apply -f deploy/ingress.yaml
	@echo "⏳ Aguardando deployment..."
	kubectl rollout status deployment/$(IMAGE_NAME) -n $(NAMESPACE) --timeout=5m
	@echo "✅ Deploy concluído!"

deploy-hpa: ## Deploy com HPA
	@echo "🚀 Deploying with HPA..."
	$(MAKE) deploy
	kubectl apply -f deploy/hpa.yaml
	@echo "✅ HPA configurado!"

undeploy: ## Remove do Kubernetes
	@echo "🗑️  Removing from Kubernetes..."
	kubectl delete -f deploy/ingress.yaml || true
	kubectl delete -f deploy/service.yaml || true
	kubectl delete -f deploy/deployment.yaml || true
	kubectl delete -f deploy/hpa.yaml || true
	@echo "✅ Removido!"

clean: undeploy ## Limpa tudo (undeploy + remove namespace)
	@echo "🧹 Cleaning up..."
	kubectl delete namespace $(NAMESPACE) || true
	@echo "✅ Limpeza concluída!"

status: ## Mostra status dos recursos
	@echo "📊 Status dos recursos:"
	kubectl get all,ingress -n $(NAMESPACE)

logs: ## Mostra logs dos pods
	@echo "📋 Logs:"
	kubectl logs -n $(NAMESPACE) -l app=$(IMAGE_NAME) -f

logs-tail: ## Mostra últimas 100 linhas dos logs
	@echo "📋 Últimos logs:"
	kubectl logs -n $(NAMESPACE) -l app=$(IMAGE_NAME) --tail=100

shell: ## Abre shell em um pod
	@echo "🐚 Abrindo shell..."
	kubectl exec -it -n $(NAMESPACE) $$(kubectl get pods -n $(NAMESPACE) -l app=$(IMAGE_NAME) -o jsonpath='{.items[0].metadata.name}') -- /bin/sh

describe: ## Descreve os recursos
	@echo "📝 Descrevendo recursos..."
	kubectl describe deployment $(IMAGE_NAME) -n $(NAMESPACE)
	kubectl describe service $(IMAGE_NAME) -n $(NAMESPACE)
	kubectl describe ingress $(IMAGE_NAME) -n $(NAMESPACE)

port-forward: ## Port forward para acesso local (8000:8000)
	@echo "🔌 Port forwarding para localhost:8000..."
	kubectl port-forward -n $(NAMESPACE) svc/$(IMAGE_NAME) 8000:8000

test-local: build ## Testa localmente com Docker
	@echo "🧪 Testando localmente..."
	docker run --rm -p 8000:8000 $(IMAGE_NAME):$(IMAGE_TAG) &
	sleep 5
	curl -f http://localhost:8000/health || (echo "❌ Health check falhou"; exit 1)
	@echo "✅ Teste local passou!"

test-k8s: ## Testa no Kubernetes
	@echo "🧪 Testando no Kubernetes..."
	kubectl run test-curl --rm -i --restart=Never --image=curlimages/curl -- \
		curl -f http://$(IMAGE_NAME).$(NAMESPACE).svc.cluster.local:8000/health
	@echo "✅ Teste K8s passou!"

scale: ## Escala deployment (use: make scale REPLICAS=5)
	@echo "📈 Escalando para $(REPLICAS) replicas..."
	kubectl scale deployment/$(IMAGE_NAME) -n $(NAMESPACE) --replicas=$(REPLICAS)

restart: ## Reinicia o deployment
	@echo "🔄 Reiniciando deployment..."
	kubectl rollout restart deployment/$(IMAGE_NAME) -n $(NAMESPACE)
	kubectl rollout status deployment/$(IMAGE_NAME) -n $(NAMESPACE)

watch: ## Observa status dos pods
	watch kubectl get pods -n $(NAMESPACE)

tls-cert: ## Gera certificado TLS auto-assinado
	@echo "🔐 Gerando certificado TLS..."
	./scripts/generate-tls-cert.sh

docker-compose-up: ## Inicia com docker-compose
	docker-compose up -d
	@echo "✅ Rodando em http://localhost:8000"

docker-compose-down: ## Para docker-compose
	docker-compose down

docker-compose-logs: ## Logs do docker-compose
	docker-compose logs -f

all: build deploy ## Build e deploy
