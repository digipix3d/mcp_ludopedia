FROM python:3.11-slim

# Metadados
LABEL maintainer="your@email.com"
LABEL description="Ludopedia MCP Server (Streamable HTTP)"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de dependências
COPY src/requirements.txt requirements.txt

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY src/ludopedia_mcp_server.py .

# Criar usuário não-root para segurança
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app

# Mudar para usuário não-root
USER mcpuser

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["python", "ludopedia_mcp_server.py"]
