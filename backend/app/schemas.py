from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, ConfigDict

MoedaPath = Annotated[
    str, Path(description='Código da moeda, com 3 letras.', examples=['ARS'])
]
ValorPath = Annotated[
    str, Path(description='Número maior que zero.', examples=['700'])
]


class Erro(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={'example': {'detail': 'Moeda não suportada: XYZ.'}}
    )


class Taxa(BaseModel):
    moeda: str
    valor: int | float | None
    atualizada_em: str | None

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'moeda': 'ARS',
                'valor': 700,
                'atualizada_em': '2026-10-11T15:00:00+00:00',
            }
        }
    )


class TaxaSalva(Taxa):
    mensagem: str

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'moeda': 'ARS',
                'valor': 700,
                'atualizada_em': '2026-10-11T15:00:00+00:00',
                'mensagem': 'Taxa salva: 1 USD = 700 ARS.',
            }
        }
    )


class Moeda(BaseModel):
    moeda: str
    mensagem: str

    model_config = ConfigDict(
        json_schema_extra={
            'example': {'moeda': 'EUR', 'mensagem': 'Moeda EUR adicionada.'}
        }
    )


class Conversao(BaseModel):
    valor: int | float
    moeda_origem: str
    moeda_destino: str
    convertido: int | float

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'valor': 100,
                'moeda_origem': 'BRL',
                'moeda_destino': 'ARS',
                'convertido': 14000,
            }
        }
    )
