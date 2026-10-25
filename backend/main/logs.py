import logging
import sys
from logging.handlers import RotatingFileHandler

from main.settings import LogConfig


class Logs:
    @staticmethod
    def configurar(config: LogConfig, nome: str) -> logging.Logger:
        raiz = logging.getLogger()
        if not raiz.handlers:
            config.pasta.mkdir(parents=True, exist_ok=True)
            formato = logging.Formatter(config.formato)
            for handler in (
                logging.StreamHandler(sys.stdout),
                RotatingFileHandler(
                    config.pasta / f'{nome}.log',
                    maxBytes=config.max_bytes,
                    backupCount=config.backups,
                    encoding='utf-8',
                ),
            ):
                handler.setFormatter(formato)
                raiz.addHandler(handler)
        raiz.setLevel(config.nivel)
        return logging.getLogger(nome)
