# Requisitos

Veja também: [api.md](api.md) (contrato HTTP) e [system-design.md](system-design.md) (arquitetura e decisões).

## 1. Escopo

| | |
| --- | --- |
| **Entra** | Valor e par de moedas a converter; taxas cadastradas à mão; novas moedas; cotações de open.er-api.com |
| **Sai** | Valor convertido; histórico das últimas conversões; lista de moedas e taxas com data de atualização |
| **Substitui** | Planilha/tabela de câmbio fixa no código do front: as moedas e taxas passam a vir da API |

## 2. Glossário

| Termo | Significado |
| --- | --- |
| Moeda base | `USD`. Toda taxa diz quanto vale 1 USD; a taxa do USD é sempre 1 |
| Moeda suportada | `USD`, `BRL`, `ARS` + as adicionadas por `POST /moedas/{codigo}`. Código de 3 letras, sempre maiúsculo |
| Taxa | Quanto vale 1 USD em uma moeda, com a data/hora da última atualização |
| Conversão | `valor ÷ taxa da origem × taxa do destino`, arredondado para 2 casas (`ROUND_HALF_UP`) |
| Histórico | As 5 conversões mais recentes, da mais nova para a mais antiga |

## 3. Requisitos funcionais

| # | Requisito | Rota |
| --- | --- | --- |
| RF1 | Cadastrar a taxa de uma moeda; se existir, atualiza | `POST /taxas/{moeda}/{valor}` |
| RF2 | Converter um valor entre duas moedas | `GET /converter/{valor}/{origem}/{destino}` |
| RF3 | Toda conversão bem-sucedida entra no histórico | — |
| RF4 | Listar as últimas conversões, paginadas (`limit` 1–5, `offset` ≥ 0) | `GET /conversoes` |
| RF5 | Listar moedas e taxas, para o front não ter valores fixos | `GET /taxas` |
| RF6 | Consultar a taxa de uma moeda | `GET /taxas/{moeda}` |
| RF7 | Devolver erros com status correto e mensagem clara (problem+json) | todas |
| RF8 | Cadastrar nova moeda suportada sem mexer no código | `POST /moedas/{codigo}` |
| RF9 | Guardar e expor a data da última atualização de cada taxa | `GET /taxas` |
| RF10 | Atualizar as taxas pelo câmbio real, sob demanda ou por intervalo | `POST /taxas/atualizar` |
| RF11 | Verificar a saúde da API e do Redis | `GET /health` |

## 4. Regras de negócio

Mensagens exatas (campo `detail`), tiradas de `backend/main/settings.py` (`Mensagens`).

| # | Mensagem exata | Condição | Depende de |
| --- | --- | --- | --- |
| RN1 | `Valor inválido: {valor}. Informe um número maior que zero.` (400) | valor fora de `\d{1,15}(\.\d{1,8})?` ou igual a zero | — |
| RN2 | `Moeda não suportada: {moeda}.` (400; 404 em `GET /taxas/{moeda}`) | moeda fora da lista de suportadas | RN1 |
| RN3 | `Moeda de origem e de destino devem ser diferentes.` (400) | origem = destino em `/converter` | RN2 |
| RN4 | `Moeda sem taxa cadastrada: {moeda}.` (404) | origem ou destino sem taxa | RN3 |
| RN5 | `{moeda} é a moeda base e vale sempre 1.` (400) | `POST /taxas/USD/{valor}` com valor ≠ 1 | RN1, RN2 |
| RN6 | `Código inválido: {codigo}. Use 3 letras, como EUR.` (400) | código fora de `[A-Z]{3}` (após maiúsculas) | — |
| RN7 | `Ainda não existe nenhuma conversão.` (404) | histórico vazio | — |
| RN8 | `Use limit entre 1 e 5 e offset maior ou igual a 0.` (400) | `limit` fora de 1–5 ou `offset` < 0 | — |
| RN9 | `Parâmetros fora do formato esperado.` (422) | parâmetro não numérico (ex.: `limit=abc`) | — |
| RN10 | `API de câmbio indisponível. Tente novamente mais tarde.` (502) | falha ou timeout em open.er-api.com | — |
| RN11 | `Banco de dados indisponível. Tente novamente.` (503) | Redis fora do ar | — |
| RN12 | `Muitas requisições. Tente novamente em instantes.` (429, texto puro) | mais de 100 req/60 s por IP | — |

Ordem de avaliação em `/converter`: RN1 valor → RN2 moedas suportadas → RN3 origem ≠ destino → RN4 taxas cadastradas. Cada erro tem um único caminho.

Mensagens de sucesso: `Taxa salva: 1 USD = {valor} {moeda}.` e `Moeda {moeda} adicionada.`

## 5. Requisitos não funcionais

| Tema | Decisão |
| --- | --- |
| Exatidão | `Decimal`, 2 casas, `ROUND_HALF_UP`; JSON sem casas desnecessárias (`14000`, não `14000.0`) |
| Consistência | Histórico com `LPUSH`+`LTRIM` em `MULTI`; taxas lidas em um comando; last-write-wins |
| Desempenho | Operações O(1)/O(n) no Redis; meta p95 < 100 ms |
| Segurança | Segredos só no `.env`; CORS restrito; rate limit por IP no Redis; validação estrita |
| Observabilidade | Logs em stdout + arquivo rotativo `data/logs/api.log` (5 MB × 3) |
| Testabilidade | `fakeredis`, sem rede; `python -m tests.test_api` e `tests.test_cambio` |

## 6. Em aberto

Decisões provisórias, a revisar.

| Tema | Decisão provisória | Por quê |
| --- | --- | --- |
| Verbo na URL (`/converter/...`, `/taxas/atualizar`) | Mantido | Rotas obrigatórias do desafio; o front (outro repo) depende delas. REST puro seria `GET /conversoes?...` e `POST /atualizacoes` |
| Erros de regra com 400 em vez de 422 | Mantido | Contrato do desafio e do front; 422 só para formato de parâmetro (RN9) |
| Atualização automática sobrescreve taxas manuais | Aceito; vem desligada (`cotacoes.intervalo_horas = 0`) | Simples; separar "manual" de "câmbio" exigiria origem por taxa |
| Cadastro de taxa aberto | Aceito | Não há usuários; mitigado pelo rate limit |

## 7. A fazer

| Item | Gatilho |
| --- | --- |
| Autenticação no cadastro de taxa e de moeda | Quando houver usuários/perfis |
| Paginação em `GET /taxas` | Se passar de centenas de moedas |
| Histórico por usuário | Quando houver login |
| Mais de 1 worker com atualização automática | Mover o timer para um job externo (cron) antes de escalar |
