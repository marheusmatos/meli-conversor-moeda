FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# /app/data recebe o volume (logs); o dono é herdado pelo volume nomeado
RUN useradd --create-home app && mkdir -p /app/data && chown app /app/data
USER app

EXPOSE 8000

CMD ["uvicorn", "main.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
