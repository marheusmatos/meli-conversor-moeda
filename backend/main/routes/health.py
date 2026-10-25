from http import HTTPStatus

from fastapi import APIRouter, Request

from main.conversor_service import ConversorService

router = APIRouter(tags=['health'])


@router.get(
    '/health',
    responses={
        HTTPStatus.SERVICE_UNAVAILABLE: {'model': ConversorService.Problema}
    },
)
def health(request: Request) -> ConversorService.Health:
    """Confere se a API e o Redis respondem."""
    request.app.state.service.health()
    return {'status': request.app.state.status_ok}
