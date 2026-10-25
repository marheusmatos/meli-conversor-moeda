import io
import json
from decimal import Decimal

import fakeredis

import main.cambio
from main.cambio import Cambio, Cotacoes
from main.settings import CambioConfig, CotacoesConfig


def novo() -> Cambio:
    return Cambio(CambioConfig(), fakeredis.FakeRedis(decode_responses=True))


def test_moedas():
    c = novo()
    c.adicionar_moeda('EUR')
    assert c.moedas() == set(c.config.moedas_padrao) | {'EUR'}


def test_salvar_taxas():
    c = novo()
    agora = c.salvar_taxas({'BRL': Decimal('5'), 'ARS': Decimal('700.5')})
    assert c.taxas() == {'BRL': Decimal('5'), 'ARS': Decimal('700.5')}
    assert c.datas() == {'BRL': agora, 'ARS': agora}


def test_converter():
    c = novo()
    brl, ars = Decimal('5'), Decimal('700')
    assert c.converter(Decimal('100'), brl, ars) == Decimal('14000')
    assert c.converter(Decimal('500'), ars, brl) == Decimal('3.57')


def test_historico():
    c = novo()
    total = c.config.historico + 2
    for i in range(total):
        c.registrar_conversao({'valor': i})
    valores = [x['valor'] for x in c.conversoes(c.config.historico, 0)]
    assert valores == list(range(total - 1, 1, -1))
    assert [x['valor'] for x in c.conversoes(2, 1)] == valores[1:3]


def test_numero():
    assert Cambio.numero(Decimal('14000.00')) == 14000
    assert type(Cambio.numero(Decimal('14000.00'))) is int
    assert type(Cambio.numero(Decimal('3.57'))) is float


def test_cotacoes():
    config = CotacoesConfig()
    corpo = json.dumps({config.campo: {'BRL': 5.1, 'USD': 1}}).encode()
    original = main.cambio.urlopen
    main.cambio.urlopen = lambda url, timeout: io.BytesIO(corpo)
    try:
        taxas = Cotacoes(config).buscar()
    finally:
        main.cambio.urlopen = original
    assert taxas == {'BRL': Decimal('5.1'), 'USD': Decimal('1')}


if __name__ == '__main__':
    test_moedas()
    test_salvar_taxas()
    test_converter()
    test_historico()
    test_numero()
    test_cotacoes()
    print('ok')
