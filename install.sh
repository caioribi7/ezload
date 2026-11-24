#!/bin/sh
# Instalador do EZLOAD para Linux e macOS.
#   curl -fsSL https://raw.githubusercontent.com/caioribi7/ezload/main/install.sh | sh
#
# Instala o uv (gerenciador de Python da Astral) se faltar, e o EZLOAD como comando global.
# Não precisa ter Python nem ffmpeg: o uv baixa o Python e o ffmpeg vem junto.
# Com integração Masterbase:  curl ... | EZLOAD_EXTRAS=masterbase sh
set -eu

REPO="${EZLOAD_REPO:-git+https://github.com/caioribi7/ezload}"

printf '\n  \033[35mEZLOAD - baixa MP4/MP3 do YouTube, TikTok e Instagram\033[0m\n\n'

if ! command -v uv >/dev/null 2>&1; then
  printf '\033[36m> Instalando o uv...\033[0m\n'
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    wget -qO- https://astral.sh/uv/install.sh | sh
  fi
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi

if [ -n "${EZLOAD_EXTRAS:-}" ]; then
  PACOTE="ezload[$EZLOAD_EXTRAS] @ $REPO"
else
  PACOTE="ezload @ $REPO"
fi

printf '\033[36m> Instalando o EZLOAD...\033[0m\n'
uv tool install --force --python ">=3.10" "$PACOTE"
uv tool update-shell >/dev/null 2>&1 || true

printf '\n\033[32mPronto!\033[0m Abra um terminal novo e use:\n'
printf '  ezload                  (menu)\n'
printf '  ezload <link>           (MP4)\n'
printf '  ezload <link> --mp3     (MP3)\n\n'
printf 'Para desinstalar: uv tool uninstall ezload\n'
