"""Integração opcional com o Masterbase (github.com/caioribi7/masterbase).

Guarda o histórico de downloads numa tabela Postgres `ezload_downloads`
e abre o painel do Masterbase em cima dela. Desligada por padrão.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from ezload import config
from ezload.downloader import Resultado

TABELA = "ezload_downloads"
PORTA = "127.0.0.1:8091"
CONFIG_MB = config.PASTA_CONFIG / "masterbase.toml"

SQL_TABELA = f"""
create table if not exists public.{TABELA} (
  id            bigserial primary key,
  url           text not null,
  titulo        text,
  plataforma    text,
  formato       text,
  arquivo       text,
  tamanho_bytes bigint,
  baixado_em    timestamptz not null default now()
)
"""


class ErroMasterbase(Exception):
    pass


def database_url() -> str | None:
    return os.environ.get("EZLOAD_DATABASE_URL") or config.get("database_url")


def _conectar(url: str):
    try:
        import psycopg
    except ImportError:
        raise ErroMasterbase(
            "Falta o driver do Postgres. Instale com:\n"
            '  uv tool install --force "ezload[masterbase] @ git+https://github.com/caioribi7/ezload"'
        )
    return psycopg.connect(url, connect_timeout=8)


def setup(url: str) -> None:
    """Testa a conexão, cria a tabela e liga o registro de downloads."""
    with _conectar(url) as conn:
        conn.execute(SQL_TABELA)
    config.set("database_url", url)


def desligar() -> None:
    config.set("database_url", None)


def registrar(resultados: list[Resultado]) -> str | None:
    """Grava os downloads se a integração estiver ligada. Devolve aviso em caso de falha."""
    url = database_url()
    if not url or not resultados:
        return None
    try:
        with _conectar(url) as conn, conn.cursor() as cur:
            cur.executemany(
                f"insert into public.{TABELA} (url, titulo, plataforma, formato, arquivo, tamanho_bytes)"
                " values (%s, %s, %s, %s, %s, %s)",
                [(r.url, r.titulo, r.plataforma, r.formato, str(r.arquivo), r.tamanho) for r in resultados],
            )
    except Exception as e:  # o download já deu certo; o histórico é só um extra
        return f"Não consegui salvar no Masterbase: {e}"
    return None


def abrir() -> subprocess.Popen:
    url = database_url()
    if not url:
        raise ErroMasterbase("Integração desligada. Rode antes: ezload masterbase setup")
    binario = shutil.which("masterbase")
    if not binario:
        raise ErroMasterbase(
            "Masterbase não está instalado. Veja https://github.com/caioribi7/masterbase\n"
            "  Linux/macOS: curl -fsSL https://raw.githubusercontent.com/caioribi7/masterbase/main/install.sh | sh"
        )
    env = {**os.environ, "DATABASE_URL": url, "MB_CONFIG": str(CONFIG_MB), "MB_ADDR": PORTA}
    return subprocess.Popen([binario], env=env)
