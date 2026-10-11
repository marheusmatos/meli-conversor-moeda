import os

from dotenv import load_dotenv

load_dotenv()

RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
BASE_PATH = os.getenv('BASE_PATH', '')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
ATUALIZACAO_AUTOMATICA_HORAS = float(
    os.getenv('ATUALIZACAO_AUTOMATICA_HORAS', '0')
)
