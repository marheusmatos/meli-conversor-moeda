# Conversor de Moedas

API em Python que converte valores entre moedas usando o dólar (USD) como base, com as taxas guardadas em um banco chave-valor (Redis).

## 1. Requisitos funcionais

| # | Requisito |
|---|---|
| RF1 | Cadastrar a taxa de uma moeda (quanto vale 1 USD); se já existir, atualiza |
| RF2 | Converter um valor entre duas moedas pela fórmula `valor ÷ taxa da origem × taxa do destino` |
| RF3 | Toda conversão bem-sucedida entra no histórico |
| RF4 | Listar as 5 conversões mais recentes, da mais nova para a mais antiga |
| RF5 | Listar moedas e taxas, para o front-end montar as listas sem valores fixos no código |
| RF6 | Devolver erros com o status HTTP correto e uma mensagem clara |
| RF7 | Cadastrar uma nova moeda suportada sem mexer no código |
| RF8 | Guardar e expor a data e hora da última atualização de cada taxa |
| RF9 | Atualizar as taxas a partir de uma API pública de câmbio |


## 2. Requisitos não funcionais

| Tema | Decisão |
|---|---|
| Exatidão | Cálculo em `Decimal` arredondado para 2 casas (`ROUND_HALF_UP`) |
| Consistência | Escrita do histórico atômica (`LPUSH` + `LTRIM` em `MULTI`). As taxas de uma conversão são lidas em um único comando. Atualização de taxa é last-write-wins |
| Desempenho | Todas as operações no Redis são O(1) ou O(n). Meta: p95 abaixo de 100 ms |
| Disponibilidade | Alta disponibilidade (24/7) |
| Durabilidade | A do Redis usado. No `docker-compose` ele roda com AOF e volume |
| Segurança | Nenhum segredo no repositório: a URL do Redis vem de variável de ambiente. CORS restrito às origens do front-end. Rate limit por IP, contado no Redis. Validação estrita de entrada. A API não tem login, então o cadastro de taxa é aberto |
| Testabilidade | `pytest` + `fakeredis`: os testes não usam Redis real nem rede |

## 3. Estimativas

O tráfego real de uma demonstração é de dezenas de requisições. Para dimensionar, o cenário hipotético é o de uma fintech com **500 usuários por dia fazendo 10 conversões cada, ou 5.000 conversões por dia**.

| Métrica | Conta | Resultado |
|---|---|---|
| Requisições HTTP por dia | 5.000 × 2 (converter + recarregar o histórico) + 500 × 2 (carga da página) | ~11.000 |
| Média e pico (10×) | 11.000 ÷ 86.400 | 0,13 req/s e ~1,3 req/s |
| Comandos Redis por conversão | `SMEMBERS` + `HGETALL` + `LPUSH` + `LTRIM` + `LRANGE` do histórico + 2 do rate limit (1 por requisição) | 7 |
| Comandos Redis por mês | (5.000 × 7 + 500 × 6) × 30 | ~1,1 milhão |
| Armazenamento das taxas | ~100 B por moeda; 3 moedas ou as 160 moedas ISO | ~0,3 KB ou ~16 KB |
| Armazenamento do histórico | 5 itens × ~95 B, constante por causa do `LTRIM` | ~0,5 KB |
| Contadores do rate limit | até 60 entradas × ~50 B por IP ativo, expirando em 2 janelas | ~3 KB por IP ativo |
| Banda por dia | 11.000 × ~0,5 KB | ~5,5 MB |

Conclusões:

- **Capacidade não é o problema.** Um worker uvicorn atende centenas de requisições por segundo nessa carga, contra um pico de ~1,3. Os dados cabem em menos de 2 MB, mesmo com centenas de IPs ativos ao mesmo tempo.
- **O limite relevante é a cota de comandos de um Redis gerenciado gratuito.** Com 500 mil comandos por mês, o teto fica em ~2.400 conversões por dia. Um Redis próprio não tem essa cota.
- **O rate limit vale para todos os workers**, porque é contado no Redis. A atualização automática roda dentro do processo; com ela ligada, a API deve ter 1 worker, para o job não rodar em duplicidade.
- O rate limit de 60 requisições por minuto por IP permite ~30 conversões por minuto por pessoa pela tela.

## 4. Entidades

| Entidade | Campos | Regras |
|---|---|---|
| **Moeda** | `codigo` | 3 letras, sempre em maiúsculas (`brl` vira `BRL`). Suportadas = `USD`, `BRL` e `ARS` + as adicionadas pela API |
| **Taxa** | `moeda`, `valor`, `atualizada_em` | `valor` é quanto vale 1 USD e deve ser maior que zero. As taxas ficam só no Redis, inclusive a do USD, que é a base e só aceita o valor 1 |
| **Conversão** | `valor`, `moeda_origem`, `moeda_destino`, `convertido` | Guardada no histórico com exatamente esses 4 campos |

Modelo no Redis:

| Chave | Tipo | Conteúdo |
|---|---|---|
| `meli:taxas` | HASH | `ARS → 700`, `BRL → 5` (decimal como texto) |
| `meli:taxas:atualizada_em` | HASH | `ARS → 2026-10-11T15:00:00+00:00` |
| `meli:moedas` | SET | moedas adicionadas pela API (`EUR`, `CLP`...) |
| `meli:conversoes` | LIST | até 5 JSONs, com a mais nova na cabeça |
| `meli:guard:rate_limit:rate:{ip}` | ZSET | requisições do IP na janela; criada pelo fastapi-guard e expira sozinha |

## 5. Endpoints

**Obrigatórios**

| Método e rota | Sucesso | Erros |
|---|---|---|
| `POST /taxas/{moeda}/{valor}` | `201` `{moeda, valor, atualizada_em, mensagem}` | `400` moeda não suportada, valor não numérico ou ≤ 0, USD diferente de 1 |
| `GET /converter/{valor}/{moeda_origem}/{moeda_destino}` | `200` `{valor, moeda_origem, moeda_destino, convertido}` | `400` valor inválido, moeda não suportada ou origem igual ao destino · `404` moeda sem taxa |
| `GET /conversoes` | `200` lista com até 5 conversões | `404` histórico vazio |

**De apoio**

| Método e rota | Sucesso | Erros |
|---|---|---|
| `GET /taxas` | `200` `[{moeda, valor, atualizada_em}]` de todas as moedas suportadas, com `valor: null` nas que ainda não têm taxa | — |
| `POST /moedas/{codigo}` | `201` `{moeda, mensagem}` (idempotente) | `400` código fora do formato de 3 letras |
| `POST /taxas/atualizar` | `200` lista das taxas atualizadas pelo câmbio real | `502` API de câmbio indisponível |
| `GET /health` | `200` `{status: ok}` | `503` Redis fora do ar |

Em todas as rotas:

- Erros de validação e de regra saem como `{"detail": "mensagem"}`.
- `429` quando o IP passa do rate limit e `503` quando o Redis está fora do ar. Os dois vêm do middleware como texto puro, com o cabeçalho `Retry-After`.

Ordem de validação em `/converter`: valor → moedas suportadas → origem diferente do destino → taxas cadastradas. Assim cada erro tem um único caminho.

Duas decisões que evitam bugs:

- `valor` é recebido como texto e validado pela expressão `\d{1,15}(\.\d{1,8})?`. Tipar como `float` faria o FastAPI devolver `422` em vez de `400` e aceitaria `nan`, `inf` e `1e5`.
- Os números saem no JSON sem casas desnecessárias: `14000`, e não `14000.0`.

## 6. Arquitetura

```mermaid
flowchart LR
    subgraph cliente["Cliente"]
        B["Navegador<br/>React + Vite<br/>(outro repositório)"]
    end

    subgraph infra["Servidor"]
        P["Proxy reverso"]
        subgraph api["Container da API · 1 worker uvicorn"]
            M["Middlewares<br/>CORS + rate limit por IP"]
            R["routes<br/>taxas · conversoes · health"]
            S["services<br/>validações · fórmula · câmbio"]
            D["repository"]
            M --> R --> S --> D
        end
        RD[("Redis<br/>chaves meli:*")]
    end

    EXT["open.er-api.com<br/>câmbio público"]

    subgraph entrega["Entrega"]
        GH["GitHub"]
        GA["GitHub Actions<br/>ruff + pytest"]
        JK["Jenkins<br/>docker build + run"]
        GH --> GA
        GH --> JK
    end

    B -->|"HTTPS + JSON"| P --> M
    D -->|"REDIS_URL"| RD
    M -->|"contadores do rate limit"| RD
    S -.->|"sob demanda ou a cada N horas"| EXT
    JK -.->|"deploy"| api
```

Camadas do código: `routes` cuida do HTTP e da documentação, `services` concentra as regras e `repository` é o único módulo que fala com o Redis.

## 7. Diagramas de sequência

### Converter um valor

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário
    participant F as Front-end
    participant A as API
    participant R as Redis

    U->>F: informa 100, BRL e ARS e clica em Converter
    F->>A: GET /converter/100/BRL/ARS
    A->>R: conta a requisição do IP (rate limit)
    R-->>A: total na janela
    A->>A: valida valor (número maior que zero)
    A->>R: SMEMBERS meli:moedas
    R-->>A: moedas adicionadas
    A->>A: valida moedas suportadas e origem diferente do destino
    alt entrada inválida
        A-->>F: 400 com mensagem
        F-->>U: mostra o erro
    else entrada válida
        A->>R: HGETALL meli:taxas
        R-->>A: BRL 5 e ARS 700
        alt alguma moeda sem taxa
            A-->>F: 404 com mensagem
            F-->>U: mostra o erro
        else taxas encontradas
            A->>A: 100 ÷ 5 × 700 = 14000
            A->>R: MULTI, LPUSH meli:conversoes, LTRIM 0 4, EXEC
            R-->>A: OK
            A-->>F: 200 com a conversão
            F->>A: GET /conversoes
            A->>R: LRANGE meli:conversoes 0 4
            R-->>A: até 5 itens
            A-->>F: 200 com a lista
            F-->>U: resultado e histórico atualizado
        end
    end
```

### Cadastrar ou atualizar uma taxa

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário
    participant F as Front-end
    participant A as API
    participant R as Redis

    U->>F: informa ARS e 700 e clica em Salvar
    F->>A: POST /taxas/ARS/700
    A->>A: valida valor (número maior que zero)
    A->>R: SMEMBERS meli:moedas
    R-->>A: moedas adicionadas
    alt moeda não suportada ou valor inválido
        A-->>F: 400 com mensagem
        F-->>U: mostra o erro
    else dados válidos
        A->>R: MULTI, HSET meli:taxas ARS 700, HSET meli:taxas:atualizada_em ARS agora, EXEC
        R-->>A: OK
        A-->>F: 201 Taxa salva, 1 USD = 700 ARS
        F->>A: GET /taxas
        A-->>F: 200 com taxas e data de atualização
        F-->>U: tabela de taxas atualizada
    end
```

### Atualizar as taxas pela API pública

```mermaid
sequenceDiagram
    autonumber
    participant G as Gatilho (botão do front ou timer)
    participant A as API
    participant C as open.er-api.com
    participant R as Redis

    G->>A: POST /taxas/atualizar
    A->>C: GET /v6/latest/USD
    alt falha ou timeout
        C--xA: erro
        A-->>G: 502 API de câmbio indisponível
    else resposta ok
        C-->>A: taxas com base em USD
        A->>R: SMEMBERS meli:moedas
        R-->>A: moedas adicionadas
        A->>R: MULTI, HSET das moedas suportadas e das datas, EXEC
        R-->>A: OK
        A-->>G: 200 com as taxas atualizadas
    end
```

O timer é opcional e fica desligado por padrão (`ATUALIZACAO_AUTOMATICA_HORAS=0`), porque ele sobrescreve as taxas cadastradas à mão pelo câmbio real.
