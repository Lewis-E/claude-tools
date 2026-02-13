#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_TARGET="$HOME/.claude/skills"

mkdir -p "$SKILLS_TARGET"

for skill in "$REPO_DIR"/skills/*/; do
    [ -d "$skill" ] || continue
    name=$(basename "$skill")
    ln -sfn "$skill" "$SKILLS_TARGET/$name"
    echo "Linked: $name"
done

echo "Done."
