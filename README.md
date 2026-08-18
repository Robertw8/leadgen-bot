# Leadgen Pipeline (Telegram)

Pipeline для автоматической обработки Telegram-чатов:

1. Ingest: чтение входящих сообщений (Telethon).
2. Filter: лид / не лид (дешевая модель).
3. Score: hot / warm / trash.
4. Memory: факты + история в Postgres/pgvector, быстрый контекст в Redis.
5. Dialog: генерация ответа в твоем стиле с RAG по скриптам/перепискам.
6. Handoff: уведомление тебе, когда лид готов к созвону.

### Переписки-sources находятся в data

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d
pip install -e .
python3 scripts/init_db.py
```

Импорт твоих скриптов и исторических чатов:

```bash
python3 scripts/ingest_playbook.py --dir ./data/playbook
```

Можно указывать папку, где лежат экспортированные Telegram-чаты в стандартном виде
(`css/`, `images/`, `js/`, `messages.html`) — импортер сам найдет все `messages.html`
в подпапках, вытащит чистый текст сообщений и загрузит в `playbook_snippets`.

Запуск воркера:

```bash
python3 -m app.workers.runner
```

В отдельном терминале:

```bash
uvicorn app.main:app --reload
```

Live ingest из Telegram:

```bash
python3 -m app.workers.telegram_listener
```

## Cost optimization

- `MODEL_DIALOG` используется по умолчанию.
- `MODEL_HARD_DIALOG` включается только по триггерам (`score`/keywords).
- В prompt подмешивается только короткое окно сообщений и ограниченный набор фактов.
