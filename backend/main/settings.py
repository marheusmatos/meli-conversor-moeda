from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Mensagens(BaseModel):
    """Erros em pares (título, detalhe); o detalhe aceita str.format."""

    valor_invalido: tuple[str, str] = (
        'Valor inválido',
        'Valor inválido: {valor}. Informe um número maior que zero.',
    )
    moeda_nao_suportada: tuple[str, str] = (
        'Moeda não suportada',
        'Moeda não suportada: {moeda}.',
    )
    taxa_base: tuple[str, str] = (
        'Taxa da moeda base',
        '{moeda} é a moeda base e vale sempre 1.',
    )
    codigo_invalido: tuple[str, str] = (
        'Código inválido',
        'Código inválido: {codigo}. Use 3 letras, como EUR.',
    )
    moedas_iguais: tuple[str, str] = (
        'Moedas iguais',
        'Moeda de origem e de destino devem ser diferentes.',
    )
    sem_taxa: tuple[str, str] = (
        'Moeda sem taxa',
        'Moeda sem taxa cadastrada: {moeda}.',
    )
    historico_vazio: tuple[str, str] = (
        'Histórico vazio',
        'Ainda não existe nenhuma conversão.',
    )
    paginacao_invalida: tuple[str, str] = (
        'Paginação inválida',
        'Use limit entre 1 e {limite} e offset maior ou igual a 0.',
    )
    requisicao_invalida: tuple[str, str] = (
        'Requisição inválida',
        'Parâmetros fora do formato esperado.',
    )
    cambio_indisponivel: tuple[str, str] = (
        'Câmbio indisponível',
        'API de câmbio indisponível. Tente novamente mais tarde.',
    )
    banco_indisponivel: tuple[str, str] = (
        'Banco indisponível',
        'Banco de dados indisponível. Tente novamente.',
    )
    muitas_requisicoes: str = (
        'Muitas requisições. Tente novamente em instantes.'
    )
    taxa_salva: str = 'Taxa salva: 1 {base} = {valor} {moeda}.'
    moeda_adicionada: str = 'Moeda {moeda} adicionada.'


class ApiConfig(BaseModel):
    titulo: str = 'Meli Conversor de Moeda'
    descricao: str = (
        'Converte valores entre moedas usando o dólar (USD) como base. '
        'As taxas ficam guardadas no Redis.'
    )
    versao: str = '0.2.0'
    root_path: str = ''  # prefixo do proxy, ex.: /meli/api
    cors_origins: list[str] = ['http://localhost:5173']
    cors_metodos: list[str] = ['GET', 'POST']
    static_dir: Path = Path('static')  # export do front; só se existir
    problem_type: str = 'about:blank'
    status_ok: str = 'ok'
    mensagens: Mensagens = Mensagens()


class LogConfig(BaseModel):
    nivel: str = 'INFO'
    formato: str = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    pasta: Path = Path('data/logs')  # no volume, sobrevive ao deploy
    max_bytes: int = 5_000_000
    backups: int = 3


class RedisConfig(BaseModel):
    url: SecretStr = SecretStr('redis://localhost:6379/0')
    timeout: float = 5  # segundos de socket


class RateLimitConfig(BaseModel):
    habilitado: bool = True
    requisicoes: int = 100  # por IP dentro da janela
    janela: int = 60  # segundos
    prefixo: str = 'meli:guard:'


class CotacoesConfig(BaseModel):
    url: str = 'https://open.er-api.com/v6/latest/USD'
    timeout: float = 10
    campo: str = 'rates'  # chave do JSON com as cotações
    intervalo_horas: float = 0  # atualização automática; 0 desliga


class ChavesRedis(BaseModel):
    taxas: str = 'meli:taxas'
    atualizada_em: str = 'meli:taxas:atualizada_em'
    moedas: str = 'meli:moedas'
    conversoes: str = 'meli:conversoes'


class CambioConfig(BaseModel):
    moeda_base: str = 'USD'
    moedas_padrao: list[str] = ['USD', 'BRL', 'ARS']
    padrao_valor: str = r'\d{1,15}(\.\d{1,8})?'
    padrao_codigo: str = r'[A-Z]{3}'
    casas: Decimal = Decimal('0.01')  # arredondamento ROUND_HALF_UP
    historico: int = 5  # conversões guardadas
    chaves: ChavesRedis = ChavesRedis()


class Settings(BaseSettings):
    """Toda a configuração; env no formato GRUPO__CAMPO."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[1] / '.env',
        env_nested_delimiter='__',
        extra='ignore',
    )

    api: ApiConfig = ApiConfig()
    log: LogConfig = LogConfig()
    redis: RedisConfig = RedisConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    cotacoes: CotacoesConfig = CotacoesConfig()
    cambio: CambioConfig = CambioConfig()

    @model_validator(mode='after')
    def ancorar_caminhos(self):
        # caminho relativo vale a partir da pasta do backend
        base = Path(__file__).parents[1]
        self.log.pasta = base / self.log.pasta
        self.api.static_dir = base / self.api.static_dir
        return self
