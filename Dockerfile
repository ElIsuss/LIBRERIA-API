FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Copiar e instalar dependencias primero para aprovechar la cache de capas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Crear usuario y grupo del sistema sin privilegios (no root)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# 3. Copiar unicamente los archivos necesarios para migrar y correr la API
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup migrations ./migrations
COPY --chown=appuser:appgroup app ./app

# 4. Activar el usuario sin privilegios
USER appuser

EXPOSE 8000

# 5. Declarar HEALTHCHECK sobre GET /health/ready usando wget contra 127.0.0.1 (IPv4)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8000/health/ready > /dev/null || exit 1

# 6. Aplicar migraciones con Alembic y luego iniciar Uvicorn en 0.0.0.0:8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
