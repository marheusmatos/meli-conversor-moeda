import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from guard import SecurityMiddleware
from redis import RedisError

from app import services, settings
from app.routes.conversoes import conversoes_router
from app.routes.health import health_router
from app.routes.taxas import taxas_router
from app.security import security_config


async def atualizar_periodicamente():
    while True:
        try:
            await asyncio.to_thread(services.atualizar_taxas)
        except Exception:
            logging.exception('Falha ao atualizar as taxas')
        await asyncio.sleep(settings.ATUALIZACAO_AUTOMATICA_HORAS * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarefa = (
        asyncio.create_task(atualizar_periodicamente())
        if settings.ATUALIZACAO_AUTOMATICA_HORAS
        else None
    )
    yield
    if tarefa:
        tarefa.cancel()


app = FastAPI(
    title='Meli Conversor de Moeda',
    description='Converte valores entre moedas usando o dólar (USD) como '
    'base. As taxas ficam guardadas no Redis.',
    version='0.1.0',
    root_path=settings.BASE_PATH,
    lifespan=lifespan,
)

app.add_middleware(SecurityMiddleware, config=security_config)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=['GET', 'POST'],
)

app.include_router(taxas_router)
app.include_router(conversoes_router)
app.include_router(health_router)


@app.exception_handler(RedisError)
def redis_indisponivel(request, exc):
    return JSONResponse(
        {'detail': 'Banco de dados indisponível. Tente novamente.'},
        status_code=503,
    )
