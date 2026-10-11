"""Configuração do middleware fastapi-guard.

Docs: https://rennf93.github.io/fastapi-guard
"""

from guard import SecurityConfig

from app import settings

security_config = SecurityConfig(
    enable_rate_limiting=settings.RATE_LIMIT_ENABLED,
    rate_limit=settings.RATE_LIMIT_REQUESTS,
    rate_limit_window=settings.RATE_LIMIT_WINDOW,
    enable_redis=settings.RATE_LIMIT_ENABLED,
    redis_url=settings.REDIS_URL,
    redis_prefix='meli:guard:',
    # Desligados para não bloquear tráfego local/legítimo.
    enable_ip_banning=False,
    enable_penetration_detection=False,
    # HTTPS é responsabilidade do proxy reverso.
    enforce_https=False,
    custom_error_responses={
        429: 'Muitas requisições. Tente novamente em instantes.',
        503: 'Banco de dados indisponível. Tente novamente.',
    },
)
