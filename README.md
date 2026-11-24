# EZLOAD

**Easy Load.** Cola o link, sai o arquivo. Baixa vídeo em **MP4** ou áudio em **MP3** do
**YouTube**, **TikTok** e **Instagram**, pelo terminal. Grátis, open source, sem anúncio e sem site
cheio de pop-up.

```powershell
ezload https://youtu.be/jNQXAC9IVRw          # vídeo MP4
ezload https://youtu.be/jNQXAC9IVRw --mp3    # áudio MP3
ezload                                       # menu
```

Não precisa instalar ffmpeg, Python nem nada à parte: o instalador cuida de tudo.

## Instalar

### Windows: instalador

Baixe o `EZLOAD-Setup-x.y.z.exe` na página de [Releases](https://github.com/caioribi7/ezload/releases),
rode e pronto. Ele instala só para o seu usuário (não pede admin), coloca o `ezload` no PATH e cria
atalho no Menu Iniciar. Tem também um `.zip` portátil, sem instalação.

> O executável ainda não tem assinatura digital. Se o Windows mostrar "O Windows protegeu o computador",
> clique em **Mais informações → Executar assim mesmo**. Se o **Smart App Control** estiver ligado ele
> bloqueia sem opção; nesse caso use a instalação por comando abaixo.

### Windows: por comando (PowerShell)

```powershell
irm https://raw.githubusercontent.com/caioribi7/ezload/main/install.ps1 | iex
```

### Linux e macOS

```sh
curl -fsSL https://raw.githubusercontent.com/caioribi7/ezload/main/install.sh | sh
```

Os dois scripts instalam o [uv](https://github.com/astral-sh/uv) se faltar e, com ele, o `ezload` como
comando global. No Windows, se não houver Python, o script instala o Python oficial pelo `winget`.

### Já tenho Python

```sh
pipx install git+https://github.com/caioribi7/ezload
# ou
uv tool install git+https://github.com/caioribi7/ezload
```

## Usar

| Comando | O que faz |
| --- | --- |
| `ezload <link>` | Baixa o vídeo em MP4 (até 1080p, H.264 + AAC, abre em qualquer player) |
| `ezload <link> --mp3` | Baixa só o áudio em MP3 320 kbps, com capa e título |
| `ezload <link1> <link2> ...` | Baixa vários de uma vez |
| `ezload "heroes david bowie" --mp3` | Sem link: busca pelo nome (MP3 vem da faixa de estúdio do YouTube Music) |
| `ezload <link> --mp3 -t 0:24-3:26` | Baixa só um trecho |
| `ezload <link> --mp3 -n "Festa - Abertura"` | Escolhe o nome do arquivo |
| `ezload lista musicas.txt` | Baixa uma lista inteira (veja abaixo) |
| `ezload <link> -q 720` | Limita a resolução (`max`, `2160`, `1440`, `1080`, `720`, `480`, `360`) |
| `ezload <link> --mp3 --kbps 192` | MP3 menor |
| `ezload <link> -o D:\Musicas` | Salva em outra pasta só dessa vez |
| `ezload <link> --playlist` | Se o link for de playlist, baixa todos os vídeos |
| `ezload <link> -c chrome` | Usa o login do navegador (conteúdo que pede conta, ver abaixo) |
| `ezload pasta D:\Downloads` | Muda a pasta padrão (começa em `~/Downloads/EZLOAD`) |
| `ezload atualizar` | Atualiza o EZLOAD e o motor de download |
| `ezload` | Abre o menu interativo |

### Baixar uma lista

Bom para playlist de festa, formatura, apresentação: um arquivo `.txt` com uma linha por música,
no formato `nome do arquivo | busca ou link | trecho (opcional)`:

```text
# linhas com # são ignoradas
01 - Abertura - Heroes        | heroes david bowie       | 0:00-3:36
02 - Valsa - Viva La Vida     | viva la vida coldplay    | 0:10-3:42
03 - Saída - Feel So Close    | https://youtu.be/xxxx    |
```

```sh
ezload lista musicas.txt -o "Formatura"      # MP3 por padrão; --mp4 para vídeo
```

O terminal mostra, para cada linha, qual faixa foi encontrada e o link, para você conferir.

### Deu erro?

- **Parou de funcionar no YouTube/TikTok/Instagram:** as plataformas mudam o site toda hora. Rode
  `ezload atualizar` antes de qualquer coisa.
- **"login required" / "private" / "not a bot":** o conteúdo pede conta. Entre na conta no seu
  navegador e rode com `-c chrome` (ou `edge`, `firefox`, `brave`). O EZLOAD lê os cookies do
  navegador só na sua máquina; nada sai daqui.

## Integra com

Integrações são **opcionais**: o EZLOAD funciona sozinho. Ficam no menu (`ezload` → *Integrações*).

### Masterbase: histórico de downloads

O [Masterbase](https://github.com/caioribi7/masterbase) é um Postgres com tela visual. Ligando a
integração, todo download vira uma linha na tabela `ezload_downloads` (link, título, plataforma,
formato, arquivo, tamanho, data) e você navega e filtra o histórico pelo painel, sem SQL.

```sh
# instala o EZLOAD com o driver do Postgres
uv tool install --force "ezload[masterbase] @ git+https://github.com/caioribi7/ezload"

ezload masterbase setup     # pede a DATABASE_URL, cria a tabela e liga o histórico
ezload masterbase open      # abre o painel em http://127.0.0.1:8091
ezload masterbase off       # desliga (a tabela continua no banco)
```

A conexão fica em `~/.ezload/config.json` (ou na variável `EZLOAD_DATABASE_URL`, que tem prioridade).
O painel usa um config próprio (`~/.ezload/masterbase.toml`), então não mexe no seu Masterbase
principal. Com o usuário `postgres` o painel enxerga tudo como administrador; em banco compartilhado,
prefira um usuário só com acesso a essa tabela.

### VibeSec: checagem antes de publicar

Para quem mexe no código: o [VibeSec](https://github.com/caioribi7/vibesec) roda um pentest no
repositório. `vibesec scan caioribi7/ezload` antes de cada release.

## Como funciona

O EZLOAD é uma casca simples em cima de projetos excelentes:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp): o motor que entende cada site (Unlicense)
- [ffmpeg](https://ffmpeg.org), via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg):
  junta áudio e vídeo e converte para MP3 (binário LGPL/GPL, distribuído sem alteração)
- [Deno](https://deno.com): o YouTube exige rodar JavaScript para liberar os vídeos (MIT)
- [Typer](https://typer.tiangolo.com) + [Rich](https://github.com/Textualize/rich): terminal bonito

## Desenvolver

```sh
git clone https://github.com/caioribi7/ezload && cd ezload
python -m venv .venv && .venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check .
```

Gerar o instalador do Windows localmente (precisa do [Inno Setup 6](https://jrsoftware.org/isinfo.php)
para o `Setup.exe`; sem ele sai só a pasta `dist/ezload`):

```powershell
./packaging/build-windows.ps1
```

Para publicar uma versão: suba o número em `pyproject.toml` e `src/ezload/__init__.py`, depois
`git tag v0.2.0 && git push --tags`. O GitHub Actions gera o `Setup.exe` e o `.zip` na página de Releases.

## Uso responsável

Baixe o que é seu, o que é livre ou o que você tem permissão para guardar. Respeite os termos de cada
plataforma e os direitos de quem criou o conteúdo. O EZLOAD não burla DRM nem paywall.

## Licença

[MIT](LICENSE). Feito por [caioribi7](https://github.com/caioribi7).
