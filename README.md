# Meli Conversor de Moeda

API em FastAPI com rate limit global (fastapi-guard).

## Rodar local

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
cd backend
uvicorn app.main:app --reload
```

- Health check: http://localhost:8000/health
- Documentação: http://localhost:8000/docs

## Variáveis de ambiente

| Variável              | Padrão | Descrição                                        |
| --------------------- | ------ | ------------------------------------------------ |
| `RATE_LIMIT_REQUESTS` | `100`  | Requisições permitidas por IP dentro da janela   |
| `RATE_LIMIT_WINDOW`   | `60`   | Tamanho da janela, em segundos                   |
| `BASE_PATH`           | vazio  | Prefixo quando roda atrás de proxy (ex.: `/meli`) |

## Estrutura

```
backend/
  requirements.txt
  pyproject.toml        # ruff + tasks
  app/
    main.py             # cria o app e registra middlewares/routers
    settings.py         # lê o .env
    security.py         # configuração do fastapi-guard
    routes/             # um arquivo por recurso
      health.py
```

Para adicionar um recurso: crie `app/routes/<recurso>.py` com um `APIRouter` e
registre com `app.include_router(...)` em `app/main.py`.

## Deploy

O `Jenkinsfile` faz o build da imagem (`Dockerfile`) e sobe o container em
`127.0.0.1:5500` com `BASE_PATH=/meli`. Ajuste `IMAGE_NAME`, `CONTAINER_NAME`,
`HOST_PORT` e `BASE_PATH` conforme o projeto.
