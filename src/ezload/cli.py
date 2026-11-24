"""Linha de comando do EZLOAD.

    ezload <link>            baixa MP4
    ezload <link> --mp3      baixa MP3
    ezload                   abre o menu
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Prompt

from ezload import __version__, config, masterbase
from ezload.downloader import (
    QUALIDADES,
    ErroDownload,
    Resultado,
    baixar,
    eh_link,
    ler_corte,
    plataforma,
)

console = Console()
app = typer.Typer(
    name="ezload",
    help="Baixa MP4 ou MP3 do YouTube, TikTok e Instagram.",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
mb_app = typer.Typer(help="Integração opcional com o Masterbase (histórico de downloads no Postgres).")
app.add_typer(mb_app, name="masterbase")

LOGO = r"""[bold magenta]
  ___ ____  _      ___    _   ___
 | __|_  / | |    / _ \  /_\ |   \
 | _| / /  | |__ | (_) |/ _ \| |) |
 |___/___| |____| \___//_/ \_\___/[/]  [dim]v{v}[/]
"""


def _tamanho(n: int) -> str:
    for un in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {un}" if un == "B" else f"{n:.1f} {un}"
        n /= 1024
    return f"{n:.1f} TB"


def _executar(urls: list[str | tuple[str, dict]], formato: str, pasta: Path, **kw) -> list[Resultado]:
    """Baixa cada item. Um item pode ser só o link/busca ou (link, opções extras daquele item)."""
    todos: list[Resultado] = []
    falhas: list[str] = []
    with Progress(
        TextColumn("[bold]{task.description}", table_column=None),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as prog:
        tarefa = prog.add_task("preparando...", total=None)

        def hook(d: dict) -> None:
            titulo = (d.get("info_dict") or {}).get("title") or "baixando"
            titulo = titulo[:40]
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                prog.update(tarefa, description=titulo, completed=d.get("downloaded_bytes") or 0, total=total)
            elif d["status"] == "finished":
                prog.update(tarefa, description=f"{titulo} (convertendo...)")

        for item in urls:
            url, extra = item if isinstance(item, tuple) else (item, {})
            if eh_link(url) and not plataforma(url):
                console.print(f"[yellow]Aviso:[/] {url} não é YouTube/TikTok/Instagram. Tentando mesmo assim.")
            prog.reset(tarefa, description="buscando..." if not eh_link(url) else "preparando...", total=None)
            try:
                res = baixar(url, formato, pasta, progresso=hook, **{**kw, **extra})
            except ErroDownload as e:
                prog.console.print(Panel(str(e), title=f"[red]Falhou[/] {url}", border_style="red"))
                falhas.append(url)
                continue
            todos.extend(res)
            for r in res:
                nome = r.arquivo.stem
                veio = f"  [dim]← {r.titulo}  {r.origem}[/]" if not eh_link(url) else ""
                prog.console.print(f"[green]✔[/] {nome}  [dim]{_tamanho(r.tamanho)}[/]{veio}")

    if todos:
        console.print(f"\n[bold green]Pronto![/] {len(todos)} arquivo(s) em [cyan]{pasta}[/]")
    if falhas:
        console.print(f"[red]{len(falhas)} falharam:[/] " + "; ".join(falhas))
    if todos:
        aviso = masterbase.registrar(todos)
        if aviso:
            console.print(f"[yellow]{aviso}[/]")
    return todos


@app.command("baixar")
def cmd_baixar(
    links: list[str] = typer.Argument(..., help="Links de vídeo, ou o nome da música entre aspas para buscar no YouTube."),
    mp3: bool = typer.Option(False, "--mp3", "-a", help="Baixa só o áudio em MP3."),
    mp4: bool = typer.Option(False, "--mp4", "-v", help="Baixa vídeo em MP4 (padrão)."),
    pasta: Path | None = typer.Option(None, "--pasta", "-o", help="Onde salvar. Padrão: ~/Downloads/EZLOAD"),
    qualidade: str = typer.Option("1080", "--qualidade", "-q", help=f"Altura máxima do vídeo: {', '.join(QUALIDADES)}"),
    kbps: int = typer.Option(320, "--kbps", help="Qualidade do MP3 (128, 192, 256, 320)."),
    playlist: bool = typer.Option(False, "--playlist", "-p", help="Se o link for de playlist, baixa todos."),
    cookies: str | None = typer.Option(
        None, "--cookies-do-navegador", "-c", help="Usa o login do navegador (chrome, edge, firefox, brave)."
    ),
    corte: str | None = typer.Option(None, "--corte", "-t", help="Só um trecho. Ex.: 0:24-3:26"),
    nome: str | None = typer.Option(None, "--nome", "-n", help="Nome do arquivo (sem extensão)."),
):
    """Baixa vídeo (MP4) ou áudio (MP3). Ex.: [cyan]ezload https://youtu.be/xxxx --mp3[/]"""
    if mp3 and mp4:
        raise typer.BadParameter("escolha --mp3 ou --mp4, não os dois")
    if qualidade not in QUALIDADES:
        raise typer.BadParameter(f"use uma destas: {', '.join(QUALIDADES)}", param_hint="--qualidade")
    if nome and len(links) > 1:
        raise typer.BadParameter("--nome só funciona com um link por vez (use `ezload lista`)")
    try:
        trecho = ler_corte(corte) if corte else None
    except ValueError as e:
        raise typer.BadParameter(str(e), param_hint="--corte")
    destino = (pasta or config.pasta_downloads()).expanduser()
    res = _executar(
        links, "mp3" if mp3 else "mp4", destino,
        qualidade=qualidade, kbps=kbps, playlist=playlist, cookies_navegador=cookies,
        corte=trecho, nome=nome,
    )
    if not res:
        raise typer.Exit(1)


def ler_lista(arquivo: Path) -> list[tuple[str, dict]]:
    """Cada linha: `nome do arquivo | link ou busca | corte (opcional)`.
    Linhas vazias e começando com # são ignoradas. Sem `|`, a linha é o link/busca."""
    itens = []
    for n, linha in enumerate(arquivo.read_text(encoding="utf-8-sig").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = [p.strip() for p in linha.split("|")]
        if len(partes) == 1:
            itens.append((partes[0], {}))
            continue
        if len(partes) > 3 or not partes[1]:
            raise typer.BadParameter(f"linha {n}: use `nome | link ou busca | corte`")
        extra: dict = {"nome": partes[0] or None}
        if len(partes) == 3 and partes[2]:
            try:
                extra["corte"] = ler_corte(partes[2])
            except ValueError as e:
                raise typer.BadParameter(f"linha {n}: {e}")
        itens.append((partes[1], extra))
    return itens


@app.command("lista")
def cmd_lista(
    arquivo: Path = typer.Argument(..., exists=True, dir_okay=False, help="Arquivo .txt com uma música/vídeo por linha."),
    mp4: bool = typer.Option(False, "--mp4", "-v", help="Baixa vídeo em vez de MP3."),
    pasta: Path | None = typer.Option(None, "--pasta", "-o", help="Onde salvar."),
    kbps: int = typer.Option(320, "--kbps", help="Qualidade do MP3."),
    qualidade: str = typer.Option("1080", "--qualidade", "-q", help="Altura máxima do vídeo."),
):
    """Baixa vários de uma vez a partir de um arquivo. Por padrão em [bold]MP3[/].

    Formato de cada linha:  [cyan]Valentina - Color Esperanza | color esperanza diego torres | 0:24-3:26[/]
    """
    itens = ler_lista(arquivo)
    destino = (pasta or config.pasta_downloads()).expanduser()
    console.print(f"{len(itens)} itens na lista.")
    res = _executar(itens, "mp4" if mp4 else "mp3", destino, kbps=kbps, qualidade=qualidade)
    if len(res) < len(itens):
        raise typer.Exit(1)


@app.command("pasta")
def cmd_pasta(nova: Path | None = typer.Argument(None, help="Nova pasta padrão de downloads.")):
    """Mostra ou muda a pasta onde os arquivos são salvos."""
    if nova:
        config.set("pasta", str(nova.expanduser().resolve()))
    console.print(f"Pasta de downloads: [cyan]{config.pasta_downloads()}[/]")


@app.command("atualizar")
def cmd_atualizar():
    """Atualiza o EZLOAD e o yt-dlp (resolve a maioria dos erros novos do YouTube)."""
    if getattr(sys, "frozen", False):
        console.print("Versão do instalador: baixe o novo Setup em https://github.com/caioribi7/ezload/releases")
        return
    uv = shutil.which("uv")
    if uv and "uv" in Path(sys.prefix).parts:
        cmd = [uv, "tool", "upgrade", "ezload"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default]", "ezload"]
    console.print(f"[dim]$ {' '.join(cmd)}[/]")
    raise typer.Exit(subprocess.call(cmd))


@mb_app.command("setup")
def mb_setup(
    database_url: str | None = typer.Argument(None, help="postgresql://usuario:senha@host:5432/banco"),
):
    """Liga o histórico: cria a tabela ezload_downloads e salva a conexão."""
    url = database_url or Prompt.ask("DATABASE_URL do Postgres", password=True)
    try:
        masterbase.setup(url)
    except masterbase.ErroMasterbase as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Não conectou no Postgres:[/] {e}")
        raise typer.Exit(1)
    console.print(f"[green]✔[/] Tabela [bold]{masterbase.TABELA}[/] pronta. Todo download vai pro histórico.")
    console.print("Abra o painel com: [cyan]ezload masterbase open[/]")


@mb_app.command("open")
def mb_open():
    """Abre o painel do Masterbase com o histórico de downloads."""
    try:
        proc = masterbase.abrir()
    except masterbase.ErroMasterbase as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
    console.print(f"Masterbase em [cyan]http://{masterbase.PORTA}[/] (Ctrl+C para fechar)")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


@mb_app.command("off")
def mb_off():
    """Desliga a integração (a tabela continua no banco)."""
    masterbase.desligar()
    console.print("Integração com o Masterbase desligada.")


def menu() -> None:
    console.print(LOGO.format(v=__version__))
    while True:
        mb = "[green]ligado[/]" if masterbase.database_url() else "[dim]desligado[/]"
        console.print(
            "\n[bold]1[/] Baixar MP4   [bold]2[/] Baixar MP3   [bold]3[/] Pasta de downloads\n"
            f"[bold]4[/] Integrações (Masterbase: {mb})   [bold]5[/] Atualizar   [bold]0[/] Sair"
        )
        op = Prompt.ask("Escolha", choices=["1", "2", "3", "4", "5", "0"], default="1", show_choices=False)
        try:
            if op in ("1", "2"):
                link = Prompt.ask("Cole o link").strip()
                if link:
                    _executar([link], "mp4" if op == "1" else "mp3", config.pasta_downloads())
            elif op == "3":
                nova = Prompt.ask("Pasta", default=str(config.pasta_downloads()))
                cmd_pasta(Path(nova))
            elif op == "4":
                _menu_masterbase()
            elif op == "5":
                cmd_atualizar()
            else:
                return
        except typer.Exit:
            pass


def _menu_masterbase() -> None:
    console.print(
        "\n[bold]Masterbase[/]: guarda o histórico de downloads num Postgres e mostra numa tela visual.\n"
        "[dim]https://github.com/caioribi7/masterbase  (opcional)[/]\n"
        "[bold]1[/] Ligar/configurar   [bold]2[/] Abrir painel   [bold]3[/] Desligar   [bold]0[/] Voltar"
    )
    op = Prompt.ask("Escolha", choices=["1", "2", "3", "0"], default="0", show_choices=False)
    if op == "1":
        mb_setup(None)
    elif op == "2":
        mb_open()
    elif op == "3":
        mb_off()


COMANDOS = {"baixar", "lista", "pasta", "atualizar", "masterbase"}


def main() -> None:
    if os.name == "nt":  # acentos e barra de progresso no terminal do Windows
        for s in (sys.stdout, sys.stderr):
            try:
                s.reconfigure(encoding="utf-8")
            except Exception:
                pass
    args = sys.argv[1:]
    if not args:
        try:
            menu()
        except (KeyboardInterrupt, EOFError):
            console.print()
        return
    if args[0] in ("--version", "-V"):
        console.print(f"ezload {__version__}")
        return
    # `ezload <link>` vira `ezload baixar <link>`
    if args[0] not in COMANDOS and args[0] not in ("--help", "-h"):
        args = ["baixar", *args]
    try:
        app(args, prog_name="ezload")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado.[/]")
        sys.exit(130)
