#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Validating examples..."

# Validate docker compose files if present
find . -maxdepth 3 \( -name "docker-compose.yml" -o -name "docker-compose.yaml" \) | while read -r f; do
  echo "  Validating $(dirname "$f")/..."
  (cd "$(dirname "$f")" && docker compose config >/dev/null 2>&1) || {
    echo "    ⚠ Docker compose validation failed (docker may not be available)"
  }
done

# Validate executable scripts have proper shebang
for script in devops-agent/scripts/*.sh multi-agent/scripts/*.sh; do
  if [[ -f "$script" ]]; then
    if head -1 "$script" | grep -q '^#!/'; then
      echo "  ✓ $script has shebang"
    else
      echo "  ⚠ $script missing shebang"
    fi
  fi
done

# Optional smoke demos (slower, opt-in)
if [[ "${RUN_EXAMPLES_DEMO:-0}" == "1" ]]; then
  if [[ -x "devops-agent/scripts/demo.sh" ]]; then
    echo "Running devops-agent demo..."
    (cd devops-agent && ./scripts/demo.sh)
  fi
fi

echo "Examples validation complete."
