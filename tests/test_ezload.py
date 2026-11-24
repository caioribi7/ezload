import sys
from pathlib import Path

import pytest

from ezload import cli, downloader
from ezload.downloader import Resultado, opcoes, plataforma


@pytest.mark.parametrize(
    "url,esperado",
    [
        ("https://www.youtube.com/watch?v=jNQXAC9IVRw", "youtube"),
        ("https://youtu.be/jNQXAC9IVRw", "youtube"),
        ("https://music.youtube.com/watch?v=abc", "youtube"),
        ("youtube.com/shorts/abc", "youtube"),
        ("https://vm.tiktok.com/ZMabc/", "tiktok"),
        ("https://www.tiktok.com/@user/video/123", "tiktok"),
        ("https://www.instagram.com/reel/abc/", "instagram"),
        ("https://example.com/video", None),
        ("https://notyoutube.com/x", None),
    ],
)
def test_plataforma(url, esperado):
    assert plataforma(url) == esperado


def test_opcoes_mp3(tmp_path):
    o = opcoes("mp3", tmp_path, kbps=192)
    assert o["format"] == "bestaudio/best"
    extrai = o["postprocessors"][0]
    assert extrai["key"] == "FFmpegExtractAudio"
    assert extrai["preferredcodec"] == "mp3" and extrai["preferredquality"] == "192"
    assert Path(o["ffmpeg_location"]).exists()


def test_opcoes_mp4_limita_resolucao(tmp_path):
    o = opcoes("mp4", tmp_path, qualidade="720")
    assert o["merge_output_format"] == "mp4"
    assert o["format_sort"][0] == "res:720"
    assert opcoes("mp4", tmp_path, qualidade="max")["format_sort"][0] == "res"


def test_opcoes_invalidas(tmp_path):
    with pytest.raises(ValueError):
        opcoes("avi", tmp_path)
    with pytest.raises(ValueError):
        opcoes("mp4", tmp_path, qualidade="999")


def test_link_direto_vira_baixar(monkeypatch, tmp_path):
    chamadas = []

    def falso(url, formato, pasta, **kw):
        chamadas.append((url, formato, pasta, kw["qualidade"]))
        arq = pasta / "x.mp3"
        arq.write_bytes(b"123")
        return [Resultado(url, "x", "youtube", formato, arq)]

    monkeypatch.setattr(cli, "baixar", falso)
    monkeypatch.setattr(cli.masterbase, "database_url", lambda: None)
    monkeypatch.setattr(sys, "argv", ["ezload", "https://youtu.be/abc", "--mp3", "-o", str(tmp_path)])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 0
    assert chamadas == [("https://youtu.be/abc", "mp3", tmp_path, "1080")]


@pytest.mark.parametrize(
    "texto,esperado",
    [("0:24-3:26", (24, 206)), ("0:24 até 3:26", (24, 206)), ("1:02:03-1:05:00", (3723, 3900)), ("10-70", (10, 70))],
)
def test_ler_corte(texto, esperado):
    assert downloader.ler_corte(texto) == esperado


@pytest.mark.parametrize("texto", ["3:00-1:00", "abc", "1:00", "1:00-2:00-3:00"])
def test_ler_corte_invalido(texto):
    with pytest.raises(ValueError):
        downloader.ler_corte(texto)


def test_nome_seguro():
    assert downloader.nome_seguro('AC/DC: "Back" in Black?') == "AC-DC- -Back- in Black-"
    assert downloader.nome_seguro("  ... ") == "audio"


def test_opcoes_corte_e_nome(tmp_path):
    o = opcoes("mp3", tmp_path, corte=(24, 206), nome="Valentina - Color Esperanza")
    assert o["outtmpl"].endswith("Valentina - Color Esperanza.%(ext)s")
    assert "download_ranges" in o and o["force_keyframes_at_cuts"]


def test_eh_link():
    assert downloader.eh_link("https://youtu.be/x")
    assert downloader.eh_link("tiktok.com/@a/video/1")
    assert not downloader.eh_link("color esperanza diego torres")


def test_ler_lista(tmp_path):
    arq = tmp_path / "lista.txt"
    arq.write_text(
        "# comentario\n\n"
        "01 - Ana - Roar | roar katy perry | 0:45-2:38\n"
        "02 - Bia - Heroes | heroes david bowie |\n"
        "https://youtu.be/abc\n",
        encoding="utf-8",
    )
    itens = cli.ler_lista(arq)
    assert itens[0] == ("roar katy perry", {"nome": "01 - Ana - Roar", "corte": (45, 158)})
    assert itens[1] == ("heroes david bowie", {"nome": "02 - Bia - Heroes"})
    assert itens[2] == ("https://youtu.be/abc", {})


def test_explica_login():
    msg = downloader._explicar("ERROR: [Instagram] abc: login required", "instagram")
    assert "--cookies-do-navegador" in msg
