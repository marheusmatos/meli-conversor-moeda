import io

import fakeredis
import pytest

from app import repository, services


def cadastrar_taxas(client):
    client.post('/taxas/BRL/5')
    client.post('/taxas/ARS/700')


def test_salvar_taxa(client):
    resposta = client.post('/taxas/ars/700')
    assert resposta.status_code == 201
    assert resposta.json()['moeda'] == 'ARS'
    assert resposta.json()['valor'] == 700
    assert resposta.json()['atualizada_em']


def test_salvar_taxa_atualiza_existente(client):
    client.post('/taxas/ARS/700')
    assert client.post('/taxas/ARS/750.5').status_code == 201
    taxas = {t['moeda']: t['valor'] for t in client.get('/taxas').json()}
    assert taxas == {'ARS': 750.5, 'BRL': None, 'USD': 1}


@pytest.mark.parametrize(
    'rota',
    [
        '/taxas/XYZ/10',
        '/taxas/ARS/abc',
        '/taxas/ARS/0',
        '/taxas/ARS/-5',
        '/taxas/ARS/nan',
        '/taxas/ARS/1e5',
        '/taxas/USD/2',
    ],
)
def test_salvar_taxa_invalida(client, rota):
    resposta = client.post(rota)
    assert resposta.status_code == 400
    assert resposta.json()['detail']


def test_converter(client):
    cadastrar_taxas(client)
    resposta = client.get('/converter/100/brl/ars')
    assert resposta.status_code == 200
    assert resposta.json() == {
        'valor': 100,
        'moeda_origem': 'BRL',
        'moeda_destino': 'ARS',
        'convertido': 14000,
    }
    assert '14000.0' not in resposta.text
    assert client.get('/converter/500/ARS/BRL').json()['convertido'] == 3.57
    assert client.get('/converter/10/USD/BRL').json()['convertido'] == 50


@pytest.mark.parametrize(
    'rota',
    [
        '/converter/abc/BRL/ARS',
        '/converter/0/BRL/ARS',
        '/converter/-1/BRL/ARS',
        '/converter/100/XYZ/ARS',
        '/converter/100/BRL/XYZ',
        '/converter/100/BRL/BRL',
    ],
)
def test_converter_invalido(client, rota):
    cadastrar_taxas(client)
    resposta = client.get(rota)
    assert resposta.status_code == 400
    assert resposta.json()['detail']


def test_converter_moeda_sem_taxa(client):
    client.post('/taxas/BRL/5')
    resposta = client.get('/converter/100/BRL/ARS')
    assert resposta.status_code == 404
    assert 'ARS' in resposta.json()['detail']


def test_conversoes_vazio(client):
    assert client.get('/conversoes').status_code == 404


def test_conversoes_ultimas_cinco_da_mais_nova_para_a_mais_antiga(client):
    cadastrar_taxas(client)
    for valor in range(1, 7):
        client.get(f'/converter/{valor}/BRL/ARS')
    client.get('/converter/abc/BRL/ARS')
    resposta = client.get('/conversoes')
    assert resposta.status_code == 200
    assert [c['valor'] for c in resposta.json()] == [6, 5, 4, 3, 2]


def test_adicionar_moeda(client):
    assert client.post('/taxas/EUR/0.9').status_code == 400
    assert client.post('/moedas/eur').status_code == 201
    assert client.post('/taxas/EUR/0.9').status_code == 201


@pytest.mark.parametrize('codigo', ['EURO', 'E1', 'R$'])
def test_adicionar_moeda_invalida(client, codigo):
    assert client.post(f'/moedas/{codigo}').status_code == 400


def test_atualizar_taxas(client, monkeypatch):
    cotacoes = b'{"rates": {"USD": 1, "BRL": 5.5, "ARS": 1400, "EUR": 0.9}}'
    monkeypatch.setattr(
        services, 'urlopen', lambda *a, **k: io.BytesIO(cotacoes)
    )
    resposta = client.post('/taxas/atualizar')
    assert resposta.status_code == 200
    assert {t['moeda']: t['valor'] for t in resposta.json()} == {
        'ARS': 1400,
        'BRL': 5.5,
        'USD': 1,
    }


def test_atualizar_taxas_api_indisponivel(client, monkeypatch):
    def falhar(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(services, 'urlopen', falhar)
    assert client.post('/taxas/atualizar').status_code == 502


def test_health(client):
    assert client.get('/health').json() == {'status': 'ok'}


def test_redis_indisponivel(client, monkeypatch):
    servidor = fakeredis.FakeServer()
    servidor.connected = False
    monkeypatch.setattr(repository, 'r', fakeredis.FakeRedis(server=servidor))
    assert client.get('/taxas').status_code == 503
    assert client.get('/health').status_code == 503
