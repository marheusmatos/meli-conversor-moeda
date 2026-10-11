from fastapi import FastAPI
from guard import SecurityMiddleware

from app import settings
from app.routes.health import health_router
from app.security import security_config

app = FastAPI(
    title='Meli Conversor de Moeda',
    version='0.1.0',
    root_path=settings.BASE_PATH,
)

app.add_middleware(SecurityMiddleware, config=security_config)

app.include_router(health_router)
