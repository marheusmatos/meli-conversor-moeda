from http import HTTPStatus

from fastapi import APIRouter, Request

from main.conversor_service import ConversorService

router = APIRouter(
    tags=['conversões'],
    responses={
        HTTPStatus.BAD_REQUEST: {'model': ConversorService.Problema},
        HTTPStatus.NOT_FOUND: {'model': ConversorService.Problema},
    },
)


@router.get('/converter/{valor}/{moeda_origem}/{moeda_destino}')
def converter(
    request: Request, valor: str, moeda_origem: str, moeda_destino: str
) -> ConversorService.Conversao:
    """Converte um valor entre duas moedas."""
    return request.app.state.service.converter(
        valor, moeda_origem, moeda_destino
    )


@router.get('/conversoes')
def listar_conversoes(
    request: Request, limit: int | None = None, offset: int = 0
) -> list[ConversorService.Conversao]:
    """Lista as últimas conversões, mais nova primeiro."""
    return request.app.state.service.listar_conversoes(limit, offset)
