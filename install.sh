#!/usr/bin/env bash
# Instalador de HUM para equipos SIN JFlowOS: Linux, macOS (Intel o chip Apple) y Windows con WSL.
# En JFlowOS no hace falta: HUM ya viene incluido desde la 12.1 «Chacayes».
#
#   bash install.sh                      desde una copia del repo
#   HUM_REPO=<url git> bash install.sh   desde otro origen
#
# Instala el código en ~/.local/share/hum-app, el comando `hum` en ~/.local/bin y un acceso en el
# menú (Linux) o la app HUM en ~/Applications (macOS). No pide sudo. Lo que HUM aprende de vos
# queda aparte, en ~/.local/share/hum (sobrevive a actualizaciones y reinstalaciones).
set -euo pipefail

DEST="${HUM_DEST:-$HOME/.local/share/hum-app}"
BIN="$HOME/.local/bin"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
REPO="${HUM_REPO:-}"

paso() { printf '\033[35m▶\033[0m %s\n' "$*"; }
falla() { printf '\033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }
es_mac() { [ "$(uname -s)" = Darwin ]; }
es_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }

command -v git >/dev/null || falla "Falta git. En la Mac: xcode-select --install · En Debian/Ubuntu: sudo apt install git"
command -v curl >/dev/null || falla "Falta curl."

# 1. El código: actualizar si ya está; si no, copiar esta copia del repo o clonar
if [ -d "$DEST/.git" ]; then
  paso "HUM ya está instalado: lo actualizo"
  git -C "$DEST" pull --ff-only --quiet || falla "No pude actualizar $DEST (¿cambios locales?)"
else
  mkdir -p "$(dirname "$DEST")"
  if [ -z "$REPO" ] && [ -n "$AQUI" ] && [ -f "$AQUI/backend/main.py" ] && [ -d "$AQUI/.git" ]; then
    paso "Copiando HUM desde $AQUI"
    git clone --quiet "$AQUI" "$DEST"
    origen="$(git -C "$AQUI" remote get-url origin 2>/dev/null || true)"
    [ -n "$origen" ] && git -C "$DEST" remote set-url origin "$origen"
  else
    REPO="${REPO:-https://github.com/ideasdevops/hum.git}"
    paso "Bajando HUM de $REPO"
    git clone --quiet --depth 1 "$REPO" "$DEST" \
      || git clone --quiet --depth 1 git@github.com:ideasdevops/hum.git "$DEST" \
      || falla "No pude bajar HUM. Si el repositorio es privado, necesitás acceso con tu cuenta de GitHub."
  fi
fi

# 2. Entorno de Python y dependencias
paso "Preparando HUM (la primera vez tarda unos minutos)"
bash "$DEST/bin/hum" instalar

# 3. Comando `hum`
mkdir -p "$BIN"
ln -sf "$DEST/bin/hum" "$BIN/hum"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    perfil="$HOME/.profile"; es_mac && perfil="$HOME/.zprofile"
    grep -qs 'HOME/.local/bin' "$perfil" || printf '\n# HUM\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$perfil"
    echo "   (agregué ~/.local/bin al PATH en $perfil: abrí una terminal nueva para usar «hum»)"
    ;;
esac

# 4. Acceso en el escritorio
if es_mac; then
  paso "App HUM en ~/Applications"
  APP="$HOME/Applications/HUM.app"
  rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
  cat > "$APP/Contents/MacOS/HUM" <<EOF
#!/bin/bash
# Las apps de macOS arrancan con un PATH mínimo
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:\$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
exec "$DEST/bin/hum" abrir
EOF
  chmod 755 "$APP/Contents/MacOS/HUM"
  cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>HUM</string>
  <key>CFBundleDisplayName</key><string>HUM</string>
  <key>CFBundleIdentifier</key><string>com.ideasdevops.hum</string>
  <key>CFBundleVersion</key><string>$(cat "$DEST/VERSION")</string>
  <key>CFBundleShortVersionString</key><string>$(cat "$DEST/VERSION")</string>
  <key>CFBundleExecutable</key><string>HUM</string>
  <key>CFBundleIconFile</key><string>hum</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSMicrophoneUsageDescription</key><string>HUM te escucha cuando le hablás.</string>
</dict></plist>
EOF
  # Ícono .icns a partir del PNG (herramientas que trae macOS)
  set_icn="$(mktemp -d)/hum.iconset"; mkdir -p "$set_icn"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$DEST/packaging/hum-1024.png" --out "$set_icn/icon_${s}x${s}.png" >/dev/null 2>&1 || true
    sips -z $((s*2)) $((s*2)) "$DEST/packaging/hum-1024.png" --out "$set_icn/icon_${s}x${s}@2x.png" >/dev/null 2>&1 || true
  done
  iconutil -c icns "$set_icn" -o "$APP/Contents/Resources/hum.icns" 2>/dev/null || true
  touch "$APP"
elif es_wsl; then
  : # En Windows se abre con el comando «hum» desde la terminal de WSL (usa el navegador de Windows)
else
  paso "Acceso en el menú de aplicaciones"
  mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
  cp "$DEST/packaging/hum.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/hum.svg"
  sed "s|^Exec=hum|Exec=$BIN/hum|" "$DEST/packaging/hum.desktop" > "$HOME/.local/share/applications/hum.desktop"
  command -v update-desktop-database >/dev/null && update-desktop-database -q "$HOME/.local/share/applications" || true
fi

echo
printf '\033[32m✓ HUM %s instalado.\033[0m\n' "$(cat "$DEST/VERSION")"
if es_mac; then echo "  Abrilo desde Aplicaciones → HUM (o Spotlight: «HUM»), o con el comando: hum"
elif es_wsl; then echo "  Abrilo con el comando: hum   (se abre en el navegador de Windows)"
else echo "  Abrilo desde el menú (HUM) o con el comando: hum"; fi
cat <<'EOF'

  Para conversar, HUM necesita con qué pensar (se elige en Ajustes, dentro de HUM):
    · Claude Code con tu cuenta (si usás Ideas Box ya lo tenés), o
    · una clave de la API de Anthropic, o
    · Ollama con un modelo local.
  Actualizar: hum actualizar · Desinstalar: hum desinstalar
EOF
