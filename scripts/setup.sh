#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { cp .env.example .env; echo "Создан .env — заполни его!"; }

echo "Структура проверена. Далее:"
echo "  1. Заполни .env"
echo "  2. bash scripts/health_check.sh"
echo "  3. Запиши задачу в tasks/current.md"
