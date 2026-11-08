#!/usr/bin/env bash
set -euo pipefail

if ! command -v makepkg >/dev/null 2>&1; then
    echo "This installer requires Arch Linux and makepkg (pacman-contrib/base-devel)." >&2
    exit 1
fi

cd "$(dirname "$(realpath "$0")")"
makepkg -si
