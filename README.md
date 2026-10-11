# Meli Conversor de Moeda

API em FastAPI que converte valores entre moedas usando o dólar (USD) como base. As taxas ficam guardadas no Redis.

O desenho do sistema (requisitos, estimativas, entidades e diagramas) está em [docs/system-design.md](docs/system-design.md).

## Rodar com Docker

```bash
cp .env.example .env
docker compose up --build
```

Sobe a API em http://localhost:8000 e um Redis local.

## Rodar local

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements-dev.txt

cp .env.example .env
docker compose up -d redis
cd backend
uvicorn app.main:app --reload
```

- Health check: http://localhost:8000/health
- Documentação (Swagger): http://localhost:8000/docs

## Testes

```bash
cd backend
pytest
ruff check .
```

Os testes usam `fakeredis`, então não precisam de Redis nem de rede. O GitHub Actions roda os dois comandos a cada push.

## Endpoints

| Método e rota | O que faz | Status |
| --- | --- | --- |
| `POST /taxas/{moeda}/{valor}` | Cadastra ou atualiza quanto vale 1 USD na moeda | `201`, `400` |
| `GET /converter/{valor}/{moeda_origem}/{moeda_destino}` | Converte o valor e guarda no histórico | `200`, `400`, `404` |
| `GET /conversoes` | Últimas 5 conversões, da mais nova para a mais antiga | `200`, `404` |
| `GET /taxas` | Moedas suportadas, suas taxas e a data da última atualização | `200` |
| `POST /moedas/{codigo}` | Adiciona uma moeda suportada (ex.: `EUR`) | `201`, `400` |
| `POST /taxas/atualizar` | Atualiza as taxas pelo câmbio real | `200`, `502` |
| `GET /health` | Verifica a API e o Redis | `200`, `503` |

Fórmula: `valor convertido = valor ÷ taxa da origem × taxa do destino`, arredondado para 2 casas.

### Exemplos

```bash
curl -X POST http://localhost:8000/taxas/USD/1
# 201 {"moeda":"USD","valor":1,"atualizada_em":"2026-10-11T15:45:35+00:00","mensagem":"Taxa salva: 1 USD = 1 USD."}

curl -X POST http://localhost:8000/taxas/BRL/5
# 201 {"moeda":"BRL","valor":5,"atualizada_em":"2026-10-11T15:45:35+00:00","mensagem":"Taxa salva: 1 USD = 5 BRL."}

curl -X POST http://localhost:8000/taxas/ARS/700
# 201 {"moeda":"ARS","valor":700,"atualizada_em":"2026-10-11T15:45:35+00:00","mensagem":"Taxa salva: 1 USD = 700 ARS."}

curl http://localhost:8000/converter/100/BRL/ARS
# 200 {"valor":100,"moeda_origem":"BRL","moeda_destino":"ARS","convertido":14000}

curl http://localhost:8000/conversoes
# 200 [{"valor":100,"moeda_origem":"BRL","moeda_destino":"ARS","convertido":14000}]

curl -X POST http://localhost:8000/moedas/EUR
# 201 {"moeda":"EUR","mensagem":"Moeda EUR adicionada."}
```

### Erros

| Se acontecer | Status |
| --- | --- |
| Valor não numérico ou menor/igual a zero | `400` |
| Moeda não suportada | `400` |
| Moeda de origem igual à de destino | `400` |
| Moeda sem taxa cadastrada | `404` |
| Histórico vazio | `404` |
| Limite de requisições por IP excedido | `429` |
| API de câmbio indisponível | `502` |
| Redis fora do ar | `503` |

Os erros saem como `{"detail": "mensagem"}`. As exceções são o `429` e o `503` devolvidos pelo middleware de rate limit, que vêm como texto puro com o cabeçalho `Retry-After`.

```bash
curl http://localhost:8000/converter/-5/BRL/ARS
# 400 {"detail":"Valor inválido: -5. Informe um número maior que zero."}

curl http://localhost:8000/converter/100/BRL/EUR
# 404 {"detail":"Moeda sem taxa cadastrada: EUR."}
```

As taxas ficam só no Redis; nenhuma vem no código. Em um ambiente novo, cadastre USD, BRL e ARS antes de converter. O USD é a base, então `POST /taxas/USD/{valor}` só aceita o valor 1.

## Variáveis de ambiente

Tudo é lido do `.env` na raiz, que não é versionado. Não use aspas nos valores.

| Variável | Default | Descrição |
| --- | --- | --- |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://usuario:senha@host:porta/db` (`rediss://` com TLS) |
| `CORS_ORIGINS` | `http://localhost:5173` | Origens do front-end, separadas por vírgula |
| `ATUALIZACAO_AUTOMATICA_HORAS` | `0` | Intervalo da atualização automática pelo câmbio real; `0` desliga |
| `RATE_LIMIT_ENABLED` | `true` | `false` desliga o rate limit |
| `RATE_LIMIT_REQUESTS` | `100` | Requisições permitidas por IP dentro da janela |
| `RATE_LIMIT_WINDOW` | `60` | Tamanho da janela, em segundos |
| `BASE_PATH` | vazio | Prefixo quando roda atrás de proxy (ex.: `/meli`) |

Com a atualização automática ligada, as taxas cadastradas à mão são sobrescritas pelo câmbio real a cada intervalo.

## Estrutura

```
docs/system-design.md
docker-compose.yml        # API + Redis
backend/
  requirements.txt
  requirements-dev.txt    # testes e lint
  pyproject.toml          # ruff, pytest e tasks
  app/
    main.py               # app, middlewares, routers e atualização automática
    settings.py           # lê o .env
    security.py           # rate limit no Redis (fastapi-guard)
    schemas.py            # modelos das respostas
    services.py           # validações, fórmula e câmbio
    repository.py         # acesso ao Redis
    routes/
      taxas.py
      conversoes.py
      health.py
  tests/
```

## Deploy

O `Jenkinsfile` faz o build da imagem e sobe o container em `127.0.0.1:5500`. As variáveis de produção vêm de uma credencial do Jenkins do tipo *Secret file* com o id `meli-env`, que é o `.env` de produção (com `REDIS_URL`, `CORS_ORIGINS` e `BASE_PATH=/meli`).

Na branch `develop` o pipeline sobe o container com `RATE_LIMIT_ENABLED=false`, usando a mesma credencial.

O rate limit é contado no Redis, então vale para todos os workers. Com a atualização automática ligada, rode com um único worker, para o job não rodar em duplicidade.

## Créditos

Cotações do câmbio real: [Rates By Exchange Rate API](https://www.exchangerate-api.com).
