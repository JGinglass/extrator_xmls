FROM python:3.11-slim

WORKDIR /app

# Instala dependências primeiro — camada cacheada separadamente do código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da aplicação
COPY extratorxmls.py .
COPY app.py .
COPY criar_usuario.py .

# Configuração do Streamlit para rodar headless em container
COPY .streamlit/config.toml .streamlit/config.toml

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -sf http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
