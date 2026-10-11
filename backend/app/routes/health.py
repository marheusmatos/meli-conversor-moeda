from fastapi import APIRouter

health_router = APIRouter(tags=['health'])


@health_router.get('/health')
def health():
    return {'status': 'ok'}
