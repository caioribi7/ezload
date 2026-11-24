# Instalador do EZLOAD para Windows.
#   irm https://raw.githubusercontent.com/caioribi7/ezload/main/install.ps1 | iex
#
# Instala o uv (gerenciador de Python da Astral) se faltar, e o EZLOAD como comando global.
# Não precisa ter Python nem ffmpeg: o uv baixa o Python e o ffmpeg vem junto.
# Com integração Masterbase:  $env:EZLOAD_EXTRAS="masterbase"; irm ... | iex

$ErrorActionPreference = "Continue"  # o uv escreve progresso no stderr; erros são checados por $LASTEXITCODE
$Repo = if ($env:EZLOAD_REPO) { $env:EZLOAD_REPO } else { "git+https://github.com/caioribi7/ezload" }

Write-Host ""
Write-Host "  EZLOAD - baixa MP4/MP3 do YouTube, TikTok e Instagram" -ForegroundColor Magenta
Write-Host ""

$Bin = "$HOME\.local\bin"
$env:Path = "$Bin;$env:Path"

# Baixa o uv direto da página de releases (zip oficial). Não abre outro PowerShell
# com -ExecutionPolicy Bypass: o Windows Defender trata esse padrão como ameaça.
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "> Instalando o uv..." -ForegroundColor Cyan
    $Arq = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }
    $Zip = Join-Path $env:TEMP "uv-$([guid]::NewGuid()).zip"
    $Tmp = Join-Path $env:TEMP "uv-$([guid]::NewGuid())"
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest "https://github.com/astral-sh/uv/releases/latest/download/uv-$Arq-pc-windows-msvc.zip" -OutFile $Zip -UseBasicParsing -ErrorAction Stop
    Expand-Archive $Zip $Tmp -Force -ErrorAction Stop
    New-Item -ItemType Directory -Force $Bin | Out-Null
    Copy-Item "$Tmp\*.exe" $Bin -Force -ErrorAction Stop
    Remove-Item $Zip, $Tmp -Recurse -Force
}

# Usa o Python oficial (assinado). O Python que o uv baixaria não tem assinatura
# e o Smart App Control do Windows 11 bloqueia.
uv python find --system ">=3.10" *> $null
if ($LASTEXITCODE -ne 0) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "> Instalando o Python 3.13 (winget)..." -ForegroundColor Cyan
        winget install --id Python.Python.3.13 -e --scope user --silent --accept-package-agreements --accept-source-agreements
        $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python313;$env:LOCALAPPDATA\Programs\Python\Python313\Scripts;$env:Path"
    } else {
        Write-Host "Sem Python e sem winget: o uv vai baixar um Python proprio." -ForegroundColor Yellow
    }
}

$Pacote = if ($env:EZLOAD_EXTRAS) { "ezload[$($env:EZLOAD_EXTRAS)] @ $Repo" } else { "ezload @ $Repo" }

Write-Host "> Instalando o EZLOAD..." -ForegroundColor Cyan
uv tool install --force --python ">=3.10" "$Pacote"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o EZLOAD." }
uv tool update-shell *> $null

Write-Host ""
Write-Host "Pronto! Abra um terminal novo e use:" -ForegroundColor Green
Write-Host "  ezload                           (menu)"
Write-Host "  ezload <link>                    (MP4)"
Write-Host "  ezload <link> --mp3              (MP3)"
Write-Host ""
Write-Host "Para desinstalar: uv tool uninstall ezload"
