"""Configuração do middleware fastapi-guard.

Docs: https://rennf93.github.io/fastapi-guard
"""

from guard import SecurityConfig

from app import settings

security_config = SecurityConfig(
    # Rate limit global, contado em memória no próprio processo (sem Redis).
    enable_rate_limiting=True,
    rate_limit=settings.RATE_LIMIT_REQUESTS,
    rate_limit_window=settings.RATE_LIMIT_WINDOW,
    enable_redis=False,
    # Desligados para não bloquear tráfego local/legítimo.
    enable_ip_banning=False,
    enable_penetration_detection=False,
    # HTTPS é responsabilidade do proxy reverso.
    enforce_https=False,
    custom_error_responses={
        429: 'Rate limit exceeded. Please try again later.',
    },
)
