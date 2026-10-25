import json
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from urllib.request import urlopen

import redis

from main.settings import CambioConfig, CotacoesConfig


class Cambio:
    """Taxas, moedas e histórico de conversões no Redis."""

    def __init__(self, config: CambioConfig, redis: redis.Redis):
        self.config = config
        self.chaves = config.chaves
        self.redis = redis

    def moedas(self) -> set[str]:
        """Moedas padrão mais as adicionadas."""
        extras = self.redis.smembers(self.chaves.moedas)
        return set(self.config.moedas_padrao) | extras

    def adicionar_moeda(self, codigo: str) -> None:
        self.redis.sadd(self.chaves.moedas, codigo)

    def taxas(self) -> dict[str, Decimal]:
        """Taxas por moeda em relação à base."""
        brutas = self.redis.hgetall(self.chaves.taxas)
        return {moeda: Decimal(v) for moeda, v in brutas.items()}

    def datas(self) -> dict[str, str]:
        """Data ISO 8601 da última atualização de cada taxa."""
        return self.redis.hgetall(self.chaves.atualizada_em)

    def salvar_taxas(self, novas: dict[str, Decimal]) -> str:
        """Grava taxas e data numa transação; devolve a data."""
        agora = datetime.now(UTC).isoformat(timespec='seconds')
        pipe = self.redis.pipeline()
        pipe.hset(
            self.chaves.taxas,
            mapping={m: str(t) for m, t in novas.items()},
        )
        pipe.hset(
            self.chaves.atualizada_em, mapping=dict.fromkeys(novas, agora)
        )
        pipe.execute()
        return agora

    def converter(
        self, valor: Decimal, taxa_origem: Decimal, taxa_destino: Decimal
    ) -> Decimal:
        """Converte passando pela moeda base."""
        convertido = valor / taxa_origem * taxa_destino
        return convertido.quantize(self.config.casas, ROUND_HALF_UP)

    def registrar_conversao(self, conversao: dict) -> None:
        """Guarda a conversão, mantendo só as mais novas."""
        pipe = self.redis.pipeline()
        pipe.lpush(self.chaves.conversoes, json.dumps(conversao))
        pipe.ltrim(self.chaves.conversoes, 0, self.config.historico - 1)
        pipe.execute()

    def conversoes(self, limit: int, offset: int) -> list[dict]:
        """Página do histórico, mais nova primeiro."""
        itens = self.redis.lrange(
            self.chaves.conversoes, offset, offset + limit - 1
        )
        return [json.loads(i) for i in itens]

    def ping(self) -> None:
        self.redis.ping()

    @staticmethod
    def numero(d: Decimal) -> int | float:
        """int se inteiro (14000, não 14000.0), senão float."""
        return int(d) if d == d.to_integral_value() else float(d)


class Cotacoes:
    """Cotações reais com base na moeda base (API pública)."""

    def __init__(self, config: CotacoesConfig):
        self.config = config

    def buscar(self) -> dict[str, Decimal]:
        """Busca as cotações; erros de rede/JSON sobem para quem chamou."""
        with urlopen(self.config.url, timeout=self.config.timeout) as resp:
            dados = json.load(resp)
        return {
            m: Decimal(str(v)) for m, v in dados[self.config.campo].items()
        }
