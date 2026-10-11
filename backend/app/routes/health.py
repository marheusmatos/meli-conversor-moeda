from fastapi import APIRouter

from app import repository

health_router = APIRouter(tags=['health'])


@health_router.get('/health', summary='Verificar a API e o Redis')
def health():
    repository.r.ping()
    return {'status': 'ok'}
