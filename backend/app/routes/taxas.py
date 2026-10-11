from fastapi import APIRouter

from app import services
from app.schemas import Erro, Moeda, MoedaPath, Taxa, TaxaSalva, ValorPath

taxas_router = APIRouter(tags=['taxas'])


@taxas_router.post(
    '/taxas/atualizar',
    response_model=list[Taxa],
    summary='Atualizar taxas pelo câmbio real',
    description='Busca as cotações em open.er-api.com e atualiza a taxa de '
    'todas as moedas suportadas.',
    responses={
        502: {'model': Erro, 'description': 'API de câmbio indisponível.'}
    },
)
def atualizar_taxas():
    return services.atualizar_taxas()


@taxas_router.post(
    '/taxas/{moeda}/{valor}',
    status_code=201,
    response_model=TaxaSalva,
    summary='Cadastrar ou atualizar uma taxa',
    description='Guarda quanto vale 1 USD na moeda informada. Se a moeda já '
    'tiver taxa, o valor é atualizado. Exemplo: `POST /taxas/ARS/700`.',
    responses={
        400: {
            'model': Erro,
            'description': 'Moeda não suportada, valor não numérico ou '
            'menor/igual a zero.',
        }
    },
)
def salvar_taxa(moeda: MoedaPath, valor: ValorPath):
    return services.salvar_taxa(moeda, valor)


@taxas_router.get(
    '/taxas',
    response_model=list[Taxa],
    summary='Listar moedas suportadas e suas taxas',
    description='Moedas ainda sem taxa aparecem com `valor: null`.',
)
def listar_taxas():
    return services.listar_taxas()


@taxas_router.post(
    '/moedas/{codigo}',
    status_code=201,
    response_model=Moeda,
    summary='Adicionar uma moeda suportada',
    description='Depois de adicionada, cadastre a taxa em '
    '`POST /taxas/{moeda}/{valor}`. Exemplo: `POST /moedas/EUR`.',
    responses={400: {'model': Erro, 'description': 'Código fora do formato.'}},
)
def adicionar_moeda(codigo: MoedaPath):
    return services.adicionar_moeda(codigo)
