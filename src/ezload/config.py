"""Configuração simples em ~/.ezload/config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

PASTA_CONFIG = Path(os.environ.get("EZLOAD_HOME", Path.home() / ".ezload"))
ARQUIVO = PASTA_CONFIG / "config.json"


def pasta_padrao() -> Path:
    return Path.home() / "Downloads" / "EZLOAD"


def ler() -> dict:
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar(dados: dict) -> None:
    PASTA_CONFIG.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        ARQUIVO.chmod(0o600)  # pode guardar a DATABASE_URL
    except OSError:
        pass


def get(chave: str, padrao=None):
    return ler().get(chave, padrao)


def set(chave: str, valor) -> None:  # noqa: A001
    dados = ler()
    if valor is None:
        dados.pop(chave, None)
    else:
        dados[chave] = valor
    salvar(dados)


def pasta_downloads() -> Path:
    return Path(get("pasta") or pasta_padrao()).expanduser()
