# Gera dist\ezload\ezload.exe (PyInstaller) e, se o Inno Setup estiver instalado,
# o instalador dist\EZLOAD-Setup-<versao>.exe.
# Rode na raiz do repositório, com o ambiente já instalado: pip install -e ".[dev]"

$ErrorActionPreference = "Stop"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

$Versao = & $Python -c "import ezload; print(ezload.__version__)"
$Deno = & $Python -c "import deno; print(deno.find_deno_bin())"

& $Python -m PyInstaller packaging\entry.py `
    --name ezload --onedir --console --noconfirm --clean `
    --collect-data imageio_ffmpeg `
    --collect-all yt_dlp_ejs `
    --add-binary "$Deno;." `
    --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$Iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $Iscc) { $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (Test-Path $Iscc) {
    & $Iscc "/DVersao=$Versao" packaging\ezload.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou" }
    Write-Host "Instalador: dist\EZLOAD-Setup-$Versao.exe" -ForegroundColor Green
} else {
    Write-Host "Inno Setup nao encontrado: gerei so dist\ezload\ezload.exe" -ForegroundColor Yellow
}
