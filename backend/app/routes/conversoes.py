from fastapi import APIRouter

from app import services
from app.schemas import Conversao, Erro, MoedaPath, ValorPath

conversoes_router = APIRouter(tags=['conversões'])


@conversoes_router.get(
    '/converter/{valor}/{moeda_origem}/{moeda_destino}',
    response_model=Conversao,
    summary='Converter um valor entre duas moedas',
    description='Fórmula: `valor ÷ taxa da origem × taxa do destino`, '
    'arredondado para 2 casas. Cada conversão entra no histórico. '
    'Exemplo: `GET /converter/100/BRL/ARS`.',
    responses={
        400: {
            'model': Erro,
            'description': 'Valor não numérico ou menor/igual a zero, moeda '
            'não suportada ou origem igual ao destino.',
        },
        404: {
            'model': Erro,
            'description': 'Alguma das moedas ainda não tem taxa cadastrada.',
        },
    },
)
def converter(
    valor: ValorPath, moeda_origem: MoedaPath, moeda_destino: MoedaPath
):
    return services.converter(valor, moeda_origem, moeda_destino)


@conversoes_router.get(
    '/conversoes',
    response_model=list[Conversao],
    summary='Histórico das últimas 5 conversões',
    description='Da mais nova para a mais antiga.',
    responses={
        404: {
            'model': Erro,
            'description': 'Ainda não existe nenhuma conversão.',
        }
    },
)
def listar_conversoes():
    return services.listar_conversoes()
