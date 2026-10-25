import logging
import re
import time
from decimal import Decimal
from http import HTTPStatus

from pydantic import BaseModel

from main.cambio import Cambio, Cotacoes
from main.settings import CambioConfig, Mensagens


class ApiError(Exception):
    def __init__(self, status: int, mensagem: tuple[str, str], **extras):
        super().__init__(mensagem[1])
        self.status = status
        self.titulo, self.detalhe = mensagem
        self.extras = extras


class ConversorService:
    """Valida a entrada e orquestra o domínio."""

    class Taxa(BaseModel):
        moeda: str
        valor: int | float | None
        atualizada_em: str | None

    class TaxaSalva(Taxa):
        mensagem: str

    class MoedaAdicionada(BaseModel):
        moeda: str
        mensagem: str

    class Conversao(BaseModel):
        valor: int | float
        moeda_origem: str
        moeda_destino: str
        convertido: int | float

    class Health(BaseModel):
        status: str

    class Problema(BaseModel):
        type: str
        title: str
        status: int
        detail: str
        instance: str

    def __init__(
        self,
        mensagens: Mensagens,
        config: CambioConfig,
        cambio: Cambio,
        cotacoes: Cotacoes,
        log: logging.Logger,
    ):
        self.mensagens = mensagens
        self.config = config
        self.cambio = cambio
        self.cotacoes = cotacoes
        self.log = log

    @staticmethod
    def _msg(mensagem: tuple[str, str], **campos) -> tuple[str, str]:
        return mensagem[0], mensagem[1].format(**campos)

    def _valor(self, valor: str) -> Decimal:
        if (
            re.fullmatch(self.config.padrao_valor, valor)
            and Decimal(valor) > 0
        ):
            return Decimal(valor)
        raise ApiError(
            HTTPStatus.BAD_REQUEST,
            self._msg(self.mensagens.valor_invalido, valor=valor),
        )

    def _moeda(self, moeda: str, status=HTTPStatus.BAD_REQUEST) -> str:
        moeda = moeda.upper()
        if moeda not in self.cambio.moedas():
            raise ApiError(
                status,
                self._msg(self.mensagens.moeda_nao_suportada, moeda=moeda),
            )
        return moeda

    @staticmethod
    def _taxa(moeda: str, taxas: dict, datas: dict) -> dict:
        valor = taxas.get(moeda)
        return {
            'moeda': moeda,
            'valor': None if valor is None else Cambio.numero(valor),
            'atualizada_em': datas.get(moeda),
        }

    def salvar_taxa(self, moeda: str, valor: str) -> dict:
        taxa = self._valor(valor)
        moeda = self._moeda(moeda)
        base = self.config.moeda_base
        if moeda == base and taxa != 1:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                self._msg(self.mensagens.taxa_base, moeda=moeda),
            )
        agora = self.cambio.salvar_taxas({moeda: taxa})
        mensagem = self.mensagens.taxa_salva.format(
            base=base, valor=Cambio.numero(taxa), moeda=moeda
        )
        self.log.info(mensagem)
        return {
            'moeda': moeda,
            'valor': Cambio.numero(taxa),
            'atualizada_em': agora,
            'mensagem': mensagem,
        }

    def taxa(self, moeda: str) -> dict:
        moeda = self._moeda(moeda, HTTPStatus.NOT_FOUND)
        return self._taxa(moeda, self.cambio.taxas(), self.cambio.datas())

    def listar_taxas(self) -> list[dict]:
        taxas, datas = self.cambio.taxas(), self.cambio.datas()
        return [
            self._taxa(m, taxas, datas) for m in sorted(self.cambio.moedas())
        ]

    def adicionar_moeda(self, codigo: str) -> dict:
        codigo = codigo.upper()
        if not re.fullmatch(self.config.padrao_codigo, codigo):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                self._msg(self.mensagens.codigo_invalido, codigo=codigo),
            )
        self.cambio.adicionar_moeda(codigo)
        mensagem = self.mensagens.moeda_adicionada.format(moeda=codigo)
        self.log.info(mensagem)
        return {'moeda': codigo, 'mensagem': mensagem}

    def converter(self, valor: str, origem: str, destino: str) -> dict:
        quantia = self._valor(valor)
        origem, destino = self._moeda(origem), self._moeda(destino)
        if origem == destino:
            raise ApiError(
                HTTPStatus.BAD_REQUEST, self.mensagens.moedas_iguais
            )
        taxas = self.cambio.taxas()
        for moeda in (origem, destino):
            if moeda not in taxas:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    self._msg(self.mensagens.sem_taxa, moeda=moeda),
                )
        convertido = self.cambio.converter(
            quantia, taxas[origem], taxas[destino]
        )
        conversao = {
            'valor': Cambio.numero(quantia),
            'moeda_origem': origem,
            'moeda_destino': destino,
            'convertido': Cambio.numero(convertido),
        }
        self.cambio.registrar_conversao(conversao)
        self.log.info('Conversão: %s', conversao)
        return conversao

    def listar_conversoes(self, limit: int | None, offset: int) -> list[dict]:
        maximo = self.config.historico
        limit = maximo if limit is None else limit
        if not 1 <= limit <= maximo or offset < 0:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                self._msg(self.mensagens.paginacao_invalida, limite=maximo),
            )
        conversoes = self.cambio.conversoes(limit, offset)
        if not conversoes:
            raise ApiError(
                HTTPStatus.NOT_FOUND, self.mensagens.historico_vazio
            )
        return conversoes

    def atualizar_taxas(self) -> list[dict]:
        inicio = time.perf_counter()
        self.log.info('Atualizando taxas')
        try:
            cotacoes = self.cotacoes.buscar()
        except (OSError, ValueError, KeyError) as erro:
            self.log.warning('Falha ao buscar cotações: %s', erro)
            raise ApiError(
                HTTPStatus.BAD_GATEWAY, self.mensagens.cambio_indisponivel
            ) from erro
        novas = {m: cotacoes[m] for m in self.cambio.moedas() if m in cotacoes}
        if novas:
            self.cambio.salvar_taxas(novas)
        self.log.info(
            'Taxas atualizadas: %s em %.2fs',
            sorted(novas),
            time.perf_counter() - inicio,
        )
        return self.listar_taxas()

    def health(self) -> None:
        self.cambio.ping()
