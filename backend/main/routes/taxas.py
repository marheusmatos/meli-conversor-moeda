from http import HTTPStatus

from fastapi import APIRouter, Request, Response

from main.conversor_service import ConversorService

router = APIRouter(
    prefix='/taxas',
    tags=['taxas'],
    responses={
        HTTPStatus.BAD_REQUEST: {'model': ConversorService.Problema},
        HTTPStatus.SERVICE_UNAVAILABLE: {'model': ConversorService.Problema},
    },
)


@router.get('')
def listar_taxas(request: Request) -> list[ConversorService.Taxa]:
    """Lista as taxas de todas as moedas suportadas."""
    return request.app.state.service.listar_taxas()


@router.post(
    '/atualizar',
    responses={HTTPStatus.BAD_GATEWAY: {'model': ConversorService.Problema}},
)
def atualizar_taxas(request: Request) -> list[ConversorService.Taxa]:
    """Busca as cotações na API de câmbio e salva as taxas."""
    return request.app.state.service.atualizar_taxas()


@router.get(
    '/{moeda}',
    name='taxa',
    responses={HTTPStatus.NOT_FOUND: {'model': ConversorService.Problema}},
)
def taxa(request: Request, moeda: str) -> ConversorService.Taxa:
    """Mostra a taxa de uma moeda."""
    return request.app.state.service.taxa(moeda)


@router.post('/{moeda}/{valor}', status_code=HTTPStatus.CREATED)
def salvar_taxa(
    request: Request, response: Response, moeda: str, valor: str
) -> ConversorService.TaxaSalva:
    """Salva a taxa de uma moeda (1 moeda base = valor moeda)."""
    salva = request.app.state.service.salvar_taxa(moeda, valor)
    response.headers['Location'] = str(
        request.url_for('taxa', moeda=salva['moeda'])
    )
    return salva
