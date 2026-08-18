# Pipeline Architecture

## Поток

1. `telegram_listener` слушает входящие TG-сообщения и кладет события в Redis queue.
2. `runner` достает события и запускает `PipelineEngine.process`.
3. Этапы:
- `filter`: лид/не лид (`MODEL_FILTER`)
- `score`: `hot|warm|trash` + score (`MODEL_SCORE`)
- `summary`: карточка и факты (`MODEL_SUMMARY`)
- `dialog`: ответ в чат (`MODEL_DIALOG`), c эскалацией в `MODEL_HARD_DIALOG` только по триггерам
- `handoff`: при `hot`+высокий score
4. Данные сохраняются в Postgres (`messages`, `leads`, `memory_facts`, `playbook_snippets`).

## Компоненты

- API: `app/main.py`, `app/api/routes.py`
- Pipeline: `app/pipeline/engine.py`
- LLM Router: `app/services/llm_router.py`
- Ingest: `app/services/telegram_client.py`
- Queue: `app/services/queue.py`
- Workers: `app/workers/*.py`
- Playbook import: `scripts/ingest_playbook.py`

## Где менять модели

`.env`:
- `MODEL_FILTER`
- `MODEL_SCORE`
- `MODEL_SUMMARY`
- `MODEL_DIALOG`
- `MODEL_HARD_DIALOG`

## Цель диалога

Лид должен согласиться на созвон. Календарные ссылки не обязательны.
