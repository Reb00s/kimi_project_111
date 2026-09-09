    #!/usr/bin/env bash
    set -euo pipefail
    cd "$(dirname "$0")/.."
    set -a; [ -f .env ] && . ./.env; set +a

    if [ -z "${1:-}" ]; then
      echo "Использование: bash scripts/run.sh '<задача для агента>'"
      exit 1
    fi

    # --- Сбор стартового контекста (аналог автоподхвата AGENTS.md) ---
    CONTEXT=$(cat AGENTS.md)
    CONTEXT+=$'

=== TASKS/CURRENT.MD ===
'
    CONTEXT+=$(cat tasks/current.md 2>/dev/null || echo "нет активной задачи")
    CONTEXT+=$'

=== ПОСЛЕДНЯЯ ЗАМЕТКА КОНТЕКСТА (конец context_log.md) ===
'
    CONTEXT+=$(tail -n 30 memory/context_log.md 2>/dev/null || echo "лог пуст")
    CONTEXT+=$'

=== MCP-ИСТОЧНИКИ ===
'
    CONTEXT+=$(cat mcp/mcp_config.json 2>/dev/null || echo "нет конфига MCP")

    RUN_DIR="workspace/runs/$(date +%Y-%m-%d)_$(echo "$1" | tr ' ' '_' | cut -c1-30)"
    mkdir -p "$RUN_DIR/input" "$RUN_DIR/output" "$RUN_DIR/logs"

    echo "$1" > "$RUN_DIR/input/prompt.txt"
    echo "$CONTEXT" > "$RUN_DIR/input/context.md"

    echo "Запуск: $RUN_DIR"
    echo "Контекст собран: AGENTS.md + current.md + context_log + mcp_config"
    # TODO: подставь команду запуска твоего агента, например:
    #   claude -p "$(cat "$RUN_DIR/input/context.md")" --append-system-prompt "$1"
    #   или: agent run --context-file "$RUN_DIR/input/context.md" --task "$1"
