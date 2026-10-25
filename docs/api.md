# API

Veja também: [requisitos.md](requisitos.md) (regras e mensagens) e [system-design.md](system-design.md) (arquitetura).

Base local: `http://localhost:8000`. Em produção, atrás do proxy: `https://<host>/meli/api`. Swagger em `/docs`.

## Rotas

| Método e rota | O que faz | Sucesso | Erros |
| --- | --- | --- | --- |
| `GET /health` | API e Redis de pé | `200` | `503` |
| `GET /taxas` | Moedas suportadas e taxas | `200` | — |
| `GET /taxas/{moeda}` | Taxa de uma moeda | `200` | `404` |
| `POST /taxas/{moeda}/{valor}` | Cadastra/atualiza taxa (1 USD = valor) | `201` + `Location` | `400` |
| `POST /taxas/atualizar` | Atualiza pelo câmbio real | `200` | `502` |
| `POST /moedas/{codigo}` | Adiciona moeda suportada (idempotente) | `201` + `Location` | `400` |
| `GET /converter/{valor}/{moeda_origem}/{moeda_destino}` | Converte e grava no histórico | `200` | `400`, `404` |
| `GET /conversoes?limit=&offset=` | Histórico, mais nova primeiro | `200` | `400`, `404`, `422` |

Em todas: `429` (rate limit, texto puro, com `Retry-After`) e `503` (Redis fora do ar). Códigos de moeda são normalizados para maiúsculas.

## Recursos

| Recurso | Campos |
| --- | --- |
| **Taxa** | `moeda` (3 letras), `valor` (número ou `null` sem taxa), `atualizada_em` (ISO 8601 ou `null`) |
| **Moeda** | `moeda`, `mensagem` |
| **Conversão** | `valor`, `moeda_origem`, `moeda_destino`, `convertido` |
| **Problema** (RFC 9457, `application/problem+json`) | `type`, `title`, `status`, `detail`, `instance`, + extras. `detail` é a mensagem para o usuário |

## Exemplos

```bash
curl http://localhost:8000/health
# 200 {"status":"ok"}

curl -X POST http://localhost:8000/taxas/BRL/5
# 201  Location: http://localhost:8000/taxas/BRL
# {"moeda":"BRL","valor":5,"atualizada_em":"2026-10-25T12:00:00+00:00","mensagem":"Taxa salva: 1 USD = 5 BRL."}

curl -X POST http://localhost:8000/taxas/ARS/700
# 201  Location: http://localhost:8000/taxas/ARS

curl http://localhost:8000/taxas
# 200 [{"moeda":"ARS","valor":700,"atualizada_em":"..."},{"moeda":"BRL","valor":5,"atualizada_em":"..."},{"moeda":"USD","valor":null,"atualizada_em":null}]

curl http://localhost:8000/taxas/brl
# 200 {"moeda":"BRL","valor":5,"atualizada_em":"2026-10-25T12:00:00+00:00"}

curl -X POST http://localhost:8000/moedas/EUR
# 201  Location: http://localhost:8000/taxas/EUR
# {"moeda":"EUR","mensagem":"Moeda EUR adicionada."}

curl http://localhost:8000/converter/100/BRL/ARS
# 200 {"valor":100,"moeda_origem":"BRL","moeda_destino":"ARS","convertido":14000}

curl "http://localhost:8000/conversoes?limit=2&offset=0"
# 200 [{"valor":100,"moeda_origem":"BRL","moeda_destino":"ARS","convertido":14000}]

curl -X POST http://localhost:8000/taxas/atualizar
# 200 [{"moeda":"ARS","valor":1450.5,"atualizada_em":"..."}, ...]
```

Erro (problem+json):

```bash
curl -i http://localhost:8000/converter/-5/BRL/ARS
# 400  Content-Type: application/problem+json
# {"type":"about:blank","title":"Valor inválido","status":400,
#  "detail":"Valor inválido: -5. Informe um número maior que zero.",
#  "instance":"/converter/-5/BRL/ARS"}
```

## Erros por rota

| Rota | Status | Quando ([regras](requisitos.md#4-regras-de-negócio)) |
| --- | --- | --- |
| `GET /taxas/{moeda}` | 404 | moeda não suportada |
| `POST /taxas/{moeda}/{valor}` | 400 | valor inválido, moeda não suportada, USD ≠ 1 |
| `POST /taxas/atualizar` | 502 | câmbio indisponível |
| `POST /moedas/{codigo}` | 400 | código inválido |
| `GET /converter/...` | 400 | valor inválido, moeda não suportada, moedas iguais |
| `GET /converter/...` | 404 | moeda sem taxa |
| `GET /conversoes` | 400 / 422 / 404 | limit/offset fora do intervalo / não numérico / histórico vazio |
| `GET /health` | 503 | Redis fora do ar |

## Fora do escopo

- Autenticação e usuários (cadastro é aberto; ver [A fazer](requisitos.md#7-a-fazer)).
- Edição/remoção de moedas e de conversões.
- Taxas históricas por data e conversão com outra moeda base.
- Frontend: fica em outro repositório; se o export estático estiver em `/app/static`, a API serve em `/`.
