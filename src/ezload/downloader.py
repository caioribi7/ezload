"""Baixa os arquivos usando o yt-dlp, com ffmpeg e deno embutidos."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import yt_dlp

PLATAFORMAS = {
    "youtube": ("youtube.com", "youtu.be"),
    "tiktok": ("tiktok.com",),
    "instagram": ("instagram.com",),
}

# "max" = sem limite; o resto vira altura máxima do vídeo
QUALIDADES = ("max", "2160", "1440", "1080", "720", "480", "360")


class ErroDownload(Exception):
    pass


@dataclass
class Resultado:
    url: str
    titulo: str
    plataforma: str
    formato: str
    arquivo: Path
    origem: str = ""  # link do vídeo que foi baixado (útil quando veio de busca)

    @property
    def tamanho(self) -> int:
        return self.arquivo.stat().st_size if self.arquivo.exists() else 0


def plataforma(url: str) -> str | None:
    """Diz de qual plataforma é o link, ou None se não for suportado."""
    host = (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()
    for nome, dominios in PLATAFORMAS.items():
        if any(host == d or host.endswith("." + d) for d in dominios):
            return nome
    return None


def eh_link(texto: str) -> bool:
    t = texto.strip().lower()
    return t.startswith(("http://", "https://")) or plataforma(t) is not None


def para_segundos(t: str) -> float:
    """'1:02:03', '3:26', '45' -> segundos."""
    partes = [float(p) for p in t.strip().split(":")]
    if not 1 <= len(partes) <= 3 or any(p < 0 for p in partes):
        raise ValueError(f"tempo inválido: {t!r}")
    s = 0.0
    for p in partes:
        s = s * 60 + p
    return s


def ler_corte(texto: str) -> tuple[float, float]:
    """'0:24-3:26' ou '0:24 até 3:26' -> (24.0, 206.0)."""
    t = texto.lower().replace("até", "-").replace("ate", "-").replace("a", "-")
    partes = [p for p in t.replace(" ", "").split("-") if p]
    if len(partes) != 2:
        raise ValueError(f"corte inválido: {texto!r} (use 0:24-3:26)")
    ini, fim = para_segundos(partes[0]), para_segundos(partes[1])
    if fim <= ini:
        raise ValueError(f"corte inválido: {texto!r} (o fim vem antes do início)")
    return ini, fim


def nome_seguro(nome: str) -> str:
    """Tira o que o Windows não aceita em nome de arquivo."""
    limpo = "".join("-" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in nome)
    return " ".join(limpo.split()).strip(" .")[:150] or "audio"


def ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg

        embutido = Path(imageio_ffmpeg.get_ffmpeg_exe())
        # O yt-dlp só reconhece o executável se ele se chamar exatamente "ffmpeg"
        # (o download de trechos depende disso). Copia uma vez para ~/.ezload/bin.
        nome = "ffmpeg.exe" if embutido.suffix == ".exe" else "ffmpeg"
        if embutido.name == nome:
            return str(embutido)
        from ezload import config

        copia = config.PASTA_CONFIG / "bin" / nome
        if not copia.exists() or copia.stat().st_size != embutido.stat().st_size:
            copia.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(embutido, copia)
        # Alguns testes internos do yt-dlp só procuram o ffmpeg no PATH
        if str(copia.parent) not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = str(copia.parent) + os.pathsep + os.environ.get("PATH", "")
        return str(copia)
    except Exception:
        sistema = shutil.which("ffmpeg")
        if not sistema:
            raise ErroDownload("ffmpeg não encontrado. Reinstale o EZLOAD ou instale o ffmpeg.")
        return sistema


def deno_path() -> str | None:
    # No .exe do instalador, o deno vai junto na pasta do programa
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        for nome in ("deno.exe", "deno"):
            if (Path(bundle) / nome).exists():
                return str(Path(bundle) / nome)
    try:
        import deno

        return deno.find_deno_bin()
    except Exception:
        return shutil.which("deno")


def opcoes(
    formato: str,
    pasta: Path,
    qualidade: str = "1080",
    kbps: int = 320,
    playlist: bool = False,
    cookies_navegador: str | None = None,
    progresso: Callable[[dict], None] | None = None,
    corte: tuple[float, float] | None = None,
    nome: str | None = None,
) -> dict:
    """Monta as opções do yt-dlp para MP3 ou MP4."""
    if formato not in ("mp3", "mp4"):
        raise ValueError("formato deve ser mp3 ou mp4")
    if qualidade not in QUALIDADES:
        raise ValueError(f"qualidade deve ser uma de: {', '.join(QUALIDADES)}")

    modelo = f"{nome_seguro(nome)}.%(ext)s" if nome else "%(title).120B [%(id)s].%(ext)s"
    o: dict = {
        "outtmpl": str(pasta / modelo),
        "ffmpeg_location": ffmpeg_path(),
        "noplaylist": not playlist,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [progresso] if progresso else [],
        "writethumbnail": formato == "mp3",
    }
    deno = deno_path()
    if deno:
        o["js_runtimes"] = {"deno": {"path": deno}}
    if cookies_navegador:
        o["cookiesfrombrowser"] = (cookies_navegador,)
    if corte:
        from yt_dlp.utils import download_range_func

        o["download_ranges"] = download_range_func(None, [corte])
        o["force_keyframes_at_cuts"] = True

    if formato == "mp3":
        o["format"] = "bestaudio/best"
        o["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": str(kbps)},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ]
    else:
        # Prioriza H.264 + AAC dentro do limite de resolução: abre em qualquer player.
        res = "res" if qualidade == "max" else f"res:{qualidade}"
        o["format"] = "bv*+ba/b"
        o["format_sort"] = [res, "vcodec:h264", "acodec:aac", "ext:mp4:m4a"]
        o["merge_output_format"] = "mp4"
        o["postprocessors"] = [
            {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"},
            {"key": "FFmpegMetadata"},
        ]
    return o


def _arquivo_final(info: dict) -> Path | None:
    for d in info.get("requested_downloads") or []:
        if d.get("filepath"):
            return Path(d["filepath"])
    return Path(info["filepath"]) if info.get("filepath") else None


def baixar(url: str, formato: str, pasta: Path, **kw) -> list[Resultado]:
    """Baixa um link (ou playlist, se pedido). Sem link, busca o texto no YouTube
    e baixa o primeiro resultado. Devolve um Resultado por arquivo."""
    pasta.mkdir(parents=True, exist_ok=True)
    o = opcoes(formato, pasta, **kw)
    if eh_link(url):
        alvo = url
    elif formato == "mp3":
        # Faixa de estúdio do YouTube Music (mesma versão do Spotify, sem intro de clipe)
        alvo = f"https://music.youtube.com/search?q={quote_plus(url)}#songs"
        o["playlist_items"] = "1"
    else:
        alvo = f"ytsearch1:{url}"
    nome_plataforma = plataforma(url) or ("outro" if eh_link(url) else "youtube")
    try:
        with yt_dlp.YoutubeDL(o) as ydl:
            info = ydl.extract_info(alvo, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise ErroDownload(_explicar(str(e), nome_plataforma)) from None

    itens = [e for e in (info.get("entries") or [info]) if e]
    resultados = []
    for item in itens:
        arquivo = _arquivo_final(item)
        if arquivo:
            resultados.append(
                Resultado(
                    url, item.get("title") or arquivo.stem, nome_plataforma, formato, arquivo,
                    item.get("webpage_url") or "",
                )
            )
    return resultados


def _explicar(msg: str, nome_plataforma: str) -> str:
    msg = msg.removeprefix("ERROR: ").strip()
    baixo = msg.lower()
    if any(p in baixo for p in ("login", "cookies", "sign in", "rate-limit", "private", "not a bot")):
        return (
            f"{msg}\n\nEsse conteúdo pede login ({nome_plataforma}). Entre na conta no navegador e rode de novo com:\n"
            "  --cookies-do-navegador chrome   (ou edge, firefox, brave)"
        )
    if "unsupported url" in baixo:
        return f"{msg}\n\nLink não reconhecido. Use um link de vídeo do YouTube, TikTok ou Instagram."
    return msg
