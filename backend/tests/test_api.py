from decimal import Decimal

import fakeredis
from fastapi.testclient import TestClient

from main.app import Api
from main.settings import Settings

PROBLEMA = 'application/problem+json'


class CotacoesFalsas:
    def __init__(self, cotacoes: dict | None = None):
        self.cotacoes = cotacoes

    def buscar(self) -> dict:
        if self.cotacoes is None:
            raise OSError('fora do ar')
        return self.cotacoes


class Cenario:
    config = Settings(_env_file=None, rate_limit={'habilitado': False})
    msg = config.api.mensagens

    @classmethod
    def cliente(cls, cotacoes=None, redis=None) -> TestClient:
        redis = redis or fakeredis.FakeRedis(decode_responses=True)
        api = Api(cls.config, redis, CotacoesFalsas(cotacoes))
        return TestClient(api.app)

    @classmethod
    def com_taxas(cls) -> TestClient:
        c = cls.cliente()
        assert c.post('/taxas/BRL/5').status_code == 201
        assert c.post('/taxas/ARS/700').status_code == 201
        assert c.post('/taxas/USD/1').status_code == 201
        return c

    @staticmethod
    def problema(r, status: int, mensagem):
        assert r.status_code == status, r.text
        assert r.headers['content-type'] == PROBLEMA
        assert r.json()['title'] == mensagem[0]


def test_salvar_taxa():
    c = Cenario.cliente()
    r = c.post('/taxas/brl/5.25')
    assert r.status_code == 201
    assert r.headers['location'].endswith('/taxas/BRL')
    assert r.json()['moeda'] == 'BRL'
    assert r.json()['valor'] == 5.25
    c.post('/taxas/BRL/6')
    assert c.get('/taxas/BRL').json()['valor'] == 6


def test_salvar_taxa_invalida():
    c = Cenario.cliente()
    m = Cenario.msg
    Cenario.problema(c.post('/taxas/XYZ/5'), 400, m.moeda_nao_suportada)
    for valor in ('abc', '0', '-5', 'nan', '1e5'):
        r = c.post(f'/taxas/BRL/{valor}')
        Cenario.problema(r, 400, m.valor_invalido)
    Cenario.problema(c.post('/taxas/USD/2'), 400, m.taxa_base)


def test_converter():
    c = Cenario.com_taxas()
    r = c.get('/converter/100/BRL/ARS')
    assert r.json()['convertido'] == 14000
    assert '14000.0' not in r.text
    assert c.get('/converter/500/ARS/BRL').json()['convertido'] == 3.57
    assert c.get('/converter/10/USD/BRL').json()['convertido'] == 50


def test_converter_invalido():
    c = Cenario.com_taxas()
    m = Cenario.msg
    Cenario.problema(c.get('/converter/abc/BRL/ARS'), 400, m.valor_invalido)
    Cenario.problema(c.get('/converter/1/XYZ/ARS'), 400, m.moeda_nao_suportada)
    Cenario.problema(c.get('/converter/1/BRL/brl'), 400, m.moedas_iguais)
    r = Cenario.cliente().get('/converter/1/BRL/ARS')
    Cenario.problema(r, 404, m.sem_taxa)
    assert 'BRL' in r.json()['detail']


def test_conversoes():
    m = Cenario.msg
    c = Cenario.com_taxas()
    Cenario.problema(c.get('/conversoes'), 404, m.historico_vazio)
    for valor in range(1, 8):
        c.get(f'/converter/{valor}/USD/BRL')
    valores = [x['valor'] for x in c.get('/conversoes').json()]
    assert valores == [7, 6, 5, 4, 3]
    r = c.get('/conversoes?limit=2&offset=1')
    assert [x['valor'] for x in r.json()] == [6, 5]
    for query in ('limit=0', 'limit=6', 'offset=-1'):
        r = c.get(f'/conversoes?{query}')
        Cenario.problema(r, 400, m.paginacao_invalida)
    r = c.get('/conversoes?limit=x')
    Cenario.problema(r, 422, m.requisicao_invalida)


def test_adicionar_moeda():
    m = Cenario.msg
    c = Cenario.cliente()
    Cenario.problema(c.post('/taxas/EUR/0.9'), 400, m.moeda_nao_suportada)
    r = c.post('/moedas/eur')
    assert r.status_code == 201
    assert r.headers['location'].endswith('/taxas/EUR')
    assert c.post('/moedas/EUR').status_code == 201
    assert c.post('/taxas/EUR/0.9').status_code == 201
    for codigo in ('EURO', 'E1', 'R$'):
        r = c.post(f'/moedas/{codigo}')
        Cenario.problema(r, 400, m.codigo_invalido)


def test_taxa():
    c = Cenario.com_taxas()
    assert c.get('/taxas/brl').json()['valor'] == 5
    r = Cenario.cliente().get('/taxas/USD')
    assert r.json()['valor'] is None
    Cenario.problema(c.get('/taxas/XYZ'), 404, Cenario.msg.moeda_nao_suportada)
    moedas = [t['moeda'] for t in c.get('/taxas').json()]
    assert moedas == ['ARS', 'BRL', 'USD']


def test_atualizar_taxas():
    cotacoes = {
        'BRL': Decimal('5.5'),
        'ARS': Decimal(1400),
        'USD': Decimal(1),
        'EUR': Decimal('0.9'),
    }
    r = Cenario.cliente(cotacoes).post('/taxas/atualizar')
    assert r.status_code == 200
    taxas = {t['moeda']: t['valor'] for t in r.json()}
    assert taxas == {'ARS': 1400, 'BRL': 5.5, 'USD': 1}
    r = Cenario.cliente().post('/taxas/atualizar')
    Cenario.problema(r, 502, Cenario.msg.cambio_indisponivel)


def test_health():
    r = Cenario.cliente().get('/health')
    assert r.json() == {'status': Cenario.config.api.status_ok}


def test_redis_fora():
    servidor = fakeredis.FakeServer()
    servidor.connected = False
    redis = fakeredis.FakeRedis(server=servidor, decode_responses=True)
    c = Cenario.cliente(redis=redis)
    for url in ('/taxas', '/health'):
        Cenario.problema(c.get(url), 503, Cenario.msg.banco_indisponivel)


if __name__ == '__main__':
    for nome, teste in list(globals().items()):
        if nome.startswith('test_'):
            teste()
    print('ok')
