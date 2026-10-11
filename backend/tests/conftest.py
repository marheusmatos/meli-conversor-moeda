import os

os.environ['REDIS_URL'] = 'redis://localhost:1/0'
os.environ['RATE_LIMIT_ENABLED'] = 'false'
os.environ['ATUALIZACAO_AUTOMATICA_HORAS'] = '0'

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import repository
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        repository, 'r', fakeredis.FakeRedis(decode_responses=True)
    )
    return TestClient(app, client=('127.0.0.1', 50000))
