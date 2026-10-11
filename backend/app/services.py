import json
import re
from decimal import ROUND_HALF_UP, Decimal
from urllib.request import urlopen

from fastapi import HTTPException

from app import repository

CAMBIO_URL = 'https://open.er-api.com/v6/latest/USD'


def numero(d: Decimal) -> int | float:
    return int(d) if d == d.to_integral_value() else float(d)


def validar_valor(valor: str) -> Decimal:
    if not re.fullmatch(r'\d{1,15}(\.\d{1,8})?', valor) or Decimal(valor) <= 0:
        raise HTTPException(
            400, f'Valor inválido: {valor}. Informe um número maior que zero.'
        )
    return Decimal(valor)


def validar_moedas(*moedas: str) -> None:
    suportadas = repository.moedas()
    for moeda in moedas:
        if moeda not in suportadas:
            raise HTTPException(400, f'Moeda não suportada: {moeda}.')


def salvar_taxa(moeda: str, valor: str) -> dict:
    taxa = validar_valor(valor)
    moeda = moeda.upper()
    validar_moedas(moeda)
    if moeda == 'USD' and taxa != 1:
        raise HTTPException(400, 'USD é a moeda base e vale sempre 1.')
    agora = repository.salvar_taxas({moeda: str(taxa)})
    return {
        'moeda': moeda,
        'valor': numero(taxa),
        'atualizada_em': agora,
        'mensagem': f'Taxa salva: 1 USD = {numero(taxa)} {moeda}.',
    }


def listar_taxas() -> list[dict]:
    taxas, datas = repository.taxas(), repository.datas()
    return [
        {
            'moeda': m,
            'valor': numero(Decimal(taxas[m])) if m in taxas else None,
            'atualizada_em': datas.get(m),
        }
        for m in sorted(repository.moedas())
    ]


def adicionar_moeda(codigo: str) -> dict:
    codigo = codigo.upper()
    if not re.fullmatch(r'[A-Z]{3}', codigo):
        raise HTTPException(
            400, f'Código inválido: {codigo}. Use 3 letras, como EUR.'
        )
    repository.adicionar_moeda(codigo)
    return {'moeda': codigo, 'mensagem': f'Moeda {codigo} adicionada.'}


def converter(valor: str, origem: str, destino: str) -> dict:
    quantia = validar_valor(valor)
    origem, destino = origem.upper(), destino.upper()
    validar_moedas(origem, destino)
    if origem == destino:
        raise HTTPException(
            400, 'Moeda de origem e de destino devem ser diferentes.'
        )
    taxas = repository.taxas()
    for moeda in (origem, destino):
        if moeda not in taxas:
            raise HTTPException(404, f'Moeda sem taxa cadastrada: {moeda}.')
    convertido = quantia / Decimal(taxas[origem]) * Decimal(taxas[destino])
    conversao = {
        'valor': numero(quantia),
        'moeda_origem': origem,
        'moeda_destino': destino,
        'convertido': numero(
            convertido.quantize(Decimal('0.01'), ROUND_HALF_UP)
        ),
    }
    repository.registrar_conversao(conversao)
    return conversao


def listar_conversoes() -> list[dict]:
    historico = repository.conversoes()
    if not historico:
        raise HTTPException(404, 'Ainda não existe nenhuma conversão.')
    return historico


def atualizar_taxas() -> list[dict]:
    try:
        with urlopen(CAMBIO_URL, timeout=10) as resposta:
            cotacoes = json.load(resposta)['rates']
    except (OSError, ValueError, KeyError) as erro:
        raise HTTPException(
            502, 'API de câmbio indisponível. Tente novamente mais tarde.'
        ) from erro
    novas = {
        m: str(cotacoes[m])
        for m in repository.moedas()
        if m != 'USD' and m in cotacoes
    }
    if novas:
        repository.salvar_taxas(novas)
    return listar_taxas()
