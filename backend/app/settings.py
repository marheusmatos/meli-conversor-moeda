import os

from dotenv import load_dotenv

# Procura o .env subindo a partir deste arquivo (ele fica na raiz do repo).
load_dotenv()

RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
# Prefixo quando a API roda atrás de um proxy reverso (ex.: /meli).
BASE_PATH = os.getenv('BASE_PATH', '')
