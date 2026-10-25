# Meli Conversor de Moeda

API em FastAPI que converte valores entre moedas usando o dólar (USD) como base. As taxas e o histórico ficam no Redis.

Documentação:

- [docs/requisitos.md](docs/requisitos.md): o que o sistema faz, regras de negócio e pendências
- [docs/api.md](docs/api.md): rotas, recursos, exemplos com `curl` e erros
- [docs/system-design.md](docs/system-design.md): arquitetura, fluxos, decisões e implantação

## Rodar com Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

API em http://localhost:8000 (Swagger em `/docs`) e um Redis local.

## Rodar local

```bash
docker compose up -d redis
cd backend
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn main.app:app --reload
```

## Testes e lint

```bash
cd backend
python -m tests.test_api && python -m tests.test_cambio
ruff check . && ruff format --check .
```

Os testes usam `fakeredis`: não precisam de Redis nem de rede. O GitHub Actions roda tudo a cada push.

## Variáveis de ambiente

O `backend/.env` (não versionado) tem só conexão e segredo. O resto é default em `backend/main/settings.py` e muda por código. Formato `GRUPO__CAMPO`, sem aspas externas.

| Variável | Exemplo | Onde |
| --- | --- | --- |
| `REDIS__URL` | `redis://usuario:senha@host:6379/0` | `.env` |
| `API__CORS_ORIGINS` | `["https://meu-front.com"]` (lista JSON) | `.env` |
| `API__ROOT_PATH` | `/meli/api` | injetada pelo Jenkins |
| `RATE_LIMIT__HABILITADO` | `false` | injetada pelo Jenkins na `develop` |

## Deploy

O `Jenkinsfile` faz o build e sobe o container em `127.0.0.1:5500`, com o volume `meli-dev-data` em `/app/data` (logs). O `.env` de produção vem da credencial *Secret file* `meli-env`.

**Atenção:** atualize o Secret file `meli-env` para os nomes novos (`REDIS__URL`, `API__CORS_ORIGINS`). `REDIS_URL`, `CORS_ORIGINS`, `BASE_PATH`, `RATE_LIMIT_*` e `ATUALIZACAO_AUTOMATICA_HORAS` deixaram de existir e são ignoradas.

Detalhes e sintomas comuns em [docs/system-design.md](docs/system-design.md#7-implantação).

## Créditos

Cotações do câmbio real: [Rates By Exchange Rate API](https://www.exchangerate-api.com).
