import asyncio
import contextlib
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from guard import SecurityConfig, SecurityMiddleware
from redis import Redis, RedisError

from main.cambio import Cambio, Cotacoes
from main.conversor_service import ApiError, ConversorService
from main.logs import Logs
from main.routes import conversoes, health, moedas, taxas
from main.settings import Settings


class Api:
    """Monta a aplicação FastAPI."""

    def __init__(
        self,
        config: Settings,
        redis: Redis | None = None,
        cotacoes: Cotacoes | None = None,
    ):
        self.config = config
        self.mensagens = config.api.mensagens
        self.log = Logs.configurar(config.log, 'api')
        url_redis = config.redis.url.get_secret_value()
        if redis is None:
            redis = Redis.from_url(
                url_redis,
                decode_responses=True,
                socket_timeout=config.redis.timeout,
            )
        self.service = ConversorService(
            self.mensagens,
            config.cambio,
            Cambio(config.cambio, redis),
            cotacoes or Cotacoes(config.cotacoes),
            self.log,
        )
        self.app = FastAPI(
            title=config.api.titulo,
            description=config.api.descricao,
            version=config.api.versao,
            root_path=config.api.root_path,
            lifespan=self.lifespan,
        )
        self.app.state.service = self.service
        self.app.state.status_ok = config.api.status_ok
        limite = config.rate_limit
        if limite.habilitado:
            self.app.add_middleware(
                SecurityMiddleware,
                config=SecurityConfig(
                    enable_rate_limiting=True,
                    rate_limit=limite.requisicoes,
                    rate_limit_window=limite.janela,
                    enable_redis=True,
                    redis_url=url_redis,
                    redis_prefix=limite.prefixo,
                    enable_ip_banning=False,
                    enable_penetration_detection=False,
                    enforce_https=False,
                    custom_error_responses={
                        HTTPStatus.TOO_MANY_REQUESTS: (
                            self.mensagens.muitas_requisicoes
                        ),
                        HTTPStatus.SERVICE_UNAVAILABLE: (
                            self.mensagens.banco_indisponivel[1]
                        ),
                    },
                ),
            )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.api.cors_origins,
            allow_methods=config.api.cors_metodos,
        )
        for modulo in (health, taxas, moedas, conversoes):
            self.app.include_router(modulo.router)
        self.app.add_exception_handler(ApiError, self.erro_api)
        self.app.add_exception_handler(
            RequestValidationError, self.erro_validacao
        )
        self.app.add_exception_handler(RedisError, self.erro_redis)
        if config.api.static_dir.is_dir():
            self.app.mount(
                '/',
                StaticFiles(directory=config.api.static_dir, html=True),
            )

    def problema(
        self, request: Request, status: int, mensagem, **extras
    ) -> JSONResponse:
        titulo, detalhe = mensagem
        return JSONResponse(
            {
                'type': self.config.api.problem_type,
                'title': titulo,
                'status': status,
                'detail': detalhe,
                'instance': request.url.path,
                **extras,
            },
            status_code=status,
            media_type='application/problem+json',
        )

    async def erro_api(self, request: Request, erro: ApiError):
        return self.problema(
            request, erro.status, (erro.titulo, erro.detalhe), **erro.extras
        )

    async def erro_validacao(self, request: Request, _erro):
        return self.problema(
            request,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            self.mensagens.requisicao_invalida,
        )

    async def erro_redis(self, request: Request, erro: Exception):
        self.log.error('Redis indisponível: %s', erro)
        return self.problema(
            request,
            HTTPStatus.SERVICE_UNAVAILABLE,
            self.mensagens.banco_indisponivel,
        )

    async def atualizar_periodicamente(self, intervalo: float):
        while True:
            try:
                await asyncio.to_thread(self.service.atualizar_taxas)
            except Exception:
                self.log.exception('Falha na atualização automática')
            await asyncio.sleep(intervalo)

    @contextlib.asynccontextmanager
    async def lifespan(self, _app: FastAPI):
        horas = self.config.cotacoes.intervalo_horas
        tarefa = None
        if horas > 0:
            tarefa = asyncio.create_task(
                self.atualizar_periodicamente(horas * 3600)
            )
        yield
        if tarefa:
            tarefa.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarefa


app = Api(Settings()).app
