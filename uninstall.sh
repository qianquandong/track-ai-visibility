#!/bin/sh
set -eu

skill_name="track-ai-visibility"
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skill_source="$repo_root/skills/$skill_name"
remove_codex=false
remove_claude=false

usage() {
  printf '%s\n' "Usage: ./uninstall.sh [--all|--codex|--claude]"
  printf '%s\n' "Only symlinks pointing to this repository are removed. Backups are preserved."
}

if [ "$#" -eq 0 ]; then
  remove_codex=true
  remove_claude=true
fi

for option in "$@"; do
  case "$option" in
    --all)
      remove_codex=true
      remove_claude=true
      ;;
    --codex)
      remove_codex=true
      ;;
    --claude)
      remove_claude=true
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

remove_link() {
  product=$1
  target=$2

  if [ ! -L "$target" ]; then
    printf 'Skipped %s: no managed symlink at %s\n' "$product" "$target"
    return
  fi

  current=$(readlink "$target")
  if [ "$current" != "$skill_source" ]; then
    printf 'Skipped %s: %s points elsewhere\n' "$product" "$target" >&2
    return
  fi

  unlink "$target"
  printf 'Uninstalled from %s: %s\n' "$product" "$target"
}

if [ "$remove_codex" = true ]; then
  codex_root=${CODEX_HOME:-"$HOME/.codex"}
  remove_link "Codex" "$codex_root/skills/$skill_name"
fi

if [ "$remove_claude" = true ]; then
  remove_link "Claude Code" "$HOME/.claude/skills/$skill_name"
fi
