import json
from datetime import UTC, datetime

import redis

from app import settings

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

TAXAS = 'meli:taxas'
ATUALIZADA_EM = 'meli:taxas:atualizada_em'
MOEDAS = 'meli:moedas'
CONVERSOES = 'meli:conversoes'
MOEDAS_PADRAO = {'USD', 'BRL', 'ARS'}


def moedas() -> set[str]:
    return MOEDAS_PADRAO | r.smembers(MOEDAS)


def adicionar_moeda(codigo: str) -> None:
    r.sadd(MOEDAS, codigo)


def taxas() -> dict[str, str]:
    return {'USD': '1'} | r.hgetall(TAXAS)


def datas() -> dict[str, str]:
    return r.hgetall(ATUALIZADA_EM)


def salvar_taxas(novas: dict[str, str]) -> str:
    agora = datetime.now(UTC).isoformat(timespec='seconds')
    with r.pipeline() as p:
        p.hset(TAXAS, mapping=novas)
        p.hset(ATUALIZADA_EM, mapping=dict.fromkeys(novas, agora))
        p.execute()
    return agora


def registrar_conversao(conversao: dict) -> None:
    with r.pipeline() as p:
        p.lpush(CONVERSOES, json.dumps(conversao))
        p.ltrim(CONVERSOES, 0, 4)
        p.execute()


def conversoes() -> list[dict]:
    return [json.loads(c) for c in r.lrange(CONVERSOES, 0, 4)]
