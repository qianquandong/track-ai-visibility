#!/bin/sh
set -eu

skill_name="track-ai-visibility"
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skill_source="$repo_root/skills/$skill_name"
install_codex=false
install_claude=false

usage() {
  printf '%s\n' "Usage: ./install.sh [--all|--codex|--claude]"
  printf '%s\n' "With no option, the skill is installed for both Codex and Claude Code."
}

if [ "$#" -eq 0 ]; then
  install_codex=true
  install_claude=true
fi

for option in "$@"; do
  case "$option" in
    --all)
      install_codex=true
      install_claude=true
      ;;
    --codex)
      install_codex=true
      ;;
    --claude)
      install_claude=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$option" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ ! -f "$skill_source/SKILL.md" ]; then
  printf 'Skill source not found: %s\n' "$skill_source" >&2
  exit 1
fi

install_link() {
  product=$1
  target=$2
  target_parent=$(dirname -- "$target")
  stamp=$(date '+%Y%m%d-%H%M%S')

  mkdir -p "$target_parent"

  if [ -L "$target" ]; then
    current=$(readlink "$target")
    if [ "$current" = "$skill_source" ]; then
      printf '%s is already linked: %s\n' "$product" "$target"
      return
    fi
    backup="$target.backup.$stamp"
    mv "$target" "$backup"
    printf 'Moved the previous %s symlink to %s\n' "$product" "$backup"
  elif [ -e "$target" ]; then
    backup="$target.backup.$stamp"
    mv "$target" "$backup"
    printf 'Moved the previous %s skill to %s\n' "$product" "$backup"
  fi

  ln -s "$skill_source" "$target"
  printf 'Installed for %s: %s -> %s\n' "$product" "$target" "$skill_source"
}

if [ "$install_codex" = true ]; then
  codex_root=${CODEX_HOME:-"$HOME/.codex"}
  install_link "Codex" "$codex_root/skills/$skill_name"
fi

if [ "$install_claude" = true ]; then
  install_link "Claude Code" "$HOME/.claude/skills/$skill_name"
fi

printf '%s\n' "Installation complete. Restart the current app if this is its first personal skill."
