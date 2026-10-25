from http import HTTPStatus

from fastapi import APIRouter, Request, Response

from main.conversor_service import ConversorService

router = APIRouter(prefix='/moedas', tags=['moedas'])


@router.post(
    '/{codigo}',
    status_code=HTTPStatus.CREATED,
    responses={HTTPStatus.BAD_REQUEST: {'model': ConversorService.Problema}},
)
def adicionar_moeda(
    request: Request, response: Response, codigo: str
) -> ConversorService.MoedaAdicionada:
    """Adiciona uma moeda às suportadas."""
    moeda = request.app.state.service.adicionar_moeda(codigo)
    response.headers['Location'] = str(
        request.url_for('taxa', moeda=moeda['moeda'])
    )
    return moeda
