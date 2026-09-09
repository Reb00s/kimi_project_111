#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
FAIL=0

# 1. .env заполнен (обязательные переменные)
if [ ! -f .env ]; then echo "FAIL: нет .env"; FAIL=1;
elif ! grep -q '^LLM_MODEL=.\+' .env; then echo "FAIL: в .env не задан LLM_MODEL"; FAIL=1;
else echo "OK: .env"; fi
# Опциональные: API-ключ и MCP-источники (примеры в mcp_config.json)
[ -f .env ] && grep -q '^LLM_API_KEY=.\+' .env || echo "WARN: LLM_API_KEY пуст (нужен только для внешнего API)"

# 2. Структура папок
for d in config mcp workspace tasks memory; do
  [ -d "$d" ] && echo "OK: $d/" || { echo "FAIL: нет $d/"; FAIL=1; }
done

# 3. MCP-серверы отвечают (замени на реальные проверки)
# TODO: добавить пинги к твоим MCP-серверам

# 4. Evals проходят
# TODO: добавить прогон config/evals/

[ $FAIL -eq 0 ] && echo "=== Все проверки пройдены ===" || { echo "=== Есть проблемы ==="; exit 1; }
