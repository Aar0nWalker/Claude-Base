# Telegram Worker Bot

Локальный Telegram-бот для постановки задач Claude/Codex, статусов, вопросов и голосовых задач. На прод-сервере не запускается.

## Запуск

```bash
./scripts/start-worker-bot.sh
./scripts/worker-bot.sh check
./scripts/worker-bot.sh queue
```

Остановка:

```bash
./scripts/stop-worker-bot.sh
```

Бот работает в Docker Compose profile `worker-bot`, runtime хранится в `.agents/worker-bot/`.

## Переменные

- `WORKER_BOT_TOKEN` - токен Telegram-бота.
- `WORKER_BOT_ALLOWED_USER_IDS` - whitelist Telegram user ID через запятую (свой узнать через `@userinfobot`).
- `WORKER_BOT_ALLOWED_CHAT_ID` - опциональная жёсткая привязка к чату.
- `GOOGLE_API_KEY` - нужен для расшифровки голосовых.
- `WORKER_BOT_TRANSCRIBE_MODEL` - опционально, по умолчанию `gemini-2.5-flash`.
- `WORKER_BOT_GOOGLE_BASE_URL` - опционально, по умолчанию Google Generative Language API.
- `WORKER_BOT_PROXY_URL` - proxy для Docker-бота. Локально: `http://host.docker.internal:{{CLASH_PORT}}`.
- `WORKER_CODEX_REQUIRE_HEADROOM` - по умолчанию `1`: Codex dispatcher перед отправкой задачи поднимает/проверяет Headroom `127.0.0.1:8788` и не падает в прямой fallback.

`.env` не коммитится, потому что содержит секреты.

## Голосовые

Голосовые работают, если задан `GOOGLE_API_KEY`.

Поток:

1. Telegram присылает voice `file_id`.
2. Бот скачивает `.ogg` через Telegram API.
3. Отправляет аудио в Gemini.
4. Полученный текст добавляет как обычную задачу.

Если расшифровка упала, бот просит отправить задачу текстом.

## Кнопки

- `+ Claude` - отправить задачу Claude.
- `+ Codex` - отправить задачу Codex.
- `Статус` - задачи в работе, очередь, вопросы и последние статусы агентов.

Сейчас автоматический dispatcher настроен для Codex. `+ Claude` кладёт задачу в очередь Claude;
Claude забирает её через `./scripts/worker-bot.sh next Claude` или через свой hook/расширение.

В статусе и сообщениях о принятой задаче бот показывает inline-кнопки `Отменить #id`. Нажатие переводит задачу в `cancelled` и убирает её из очереди.

Вопросы от агентов приходят отдельным сообщением с именем агента, `Q{id}` и временем. Нажми в Telegram `Ответить` на это сообщение и отправь текст; бот привяжет ответ к нужному вопросу и поставит follow-up задачу агенту.

## Сообщения

Основной формат без номера задачи:

```text
Codex -- Bob

✅ Задачу принял и работает

Ответ от агента:
Текст ответа
```

Пока есть задача в статусе `claimed`, бот шлёт Telegram `typing` action как working heartbeat. Это не создаёт лишних сообщений.

## Agent CLI

```bash
./scripts/worker-bot.sh next Codex
./scripts/worker-bot.sh status Codex "Взял задачу #12"
./scripts/worker-bot.sh ask Codex "Нужен деплой?"
./scripts/worker-bot.sh done 12
./scripts/worker-bot.sh queue
./scripts/worker-bot.sh context Codex
```

## Чаты агентов

Бот хранит короткую историю агентских задач в runtime-директории `.agents/worker-bot/`.

- `.agents/worker-bot/agents/codex/chat.md` - общий чат и задачи Codex.
- `.agents/worker-bot/agents/claude/chat.md` - общий чат и задачи Claude.
- `.agents/worker-bot/context.md` - компактная общая лента последних событий по задачам.
- `.agents/worker-bot/inbox.md` - обзор очереди, статусов и вопросов.

`context.md`/`inbox.md` закоммичены как пустые шаблоны (см. `.gitignore`), чтобы бот не падал на
чистом чекауте; дальше бот их перезаписывает и они живут как runtime-состояние. `agents/*` и
`screenshots/*` — чистый runtime, гитигнорятся целиком. Dispatcher подмешивает `context` в prompt, чтобы новый агент не сканировал весь проект заново.

## Codex Dispatcher

`scripts/worker-dispatcher.sh` забирает задачи Codex и отправляет их через `scripts/codex-app-send.py`.
Перед отправкой dispatcher запускает `scripts/start-headroom.sh` и проверяет `http://127.0.0.1:8788/livez`.
Если Headroom недоступен, задача возвращается в очередь с ошибкой, а не отправляется напрямую.

Порядок:

1. Пробует `thread/resume` + `turn/start` для текущего Codex thread.
2. Если Headroom-режим отключён через `WORKER_CODEX_REQUIRE_HEADROOM=0`, при ошибке может создать новый app-server thread через `send-message-v2`.
3. В fallback добавляет короткий срез текущего чата как контекст.

Thread выбирается в таком порядке:

1. `WORKER_CODEX_THREAD_ID`.
2. `CODEX_THREAD_ID` из текущего Codex-чата расширения.
3. `.agents/worker-bot/codex-thread-id`.
4. Последняя подходящая сессия из `~/.codex/sessions`.

Текущий thread можно закрепить вручную через:

```bash
echo "<thread-id>" > .agents/worker-bot/codex-thread-id
```

или переменную:

```bash
WORKER_CODEX_THREAD_ID=<thread-id>
```

## Ограничения

- Бот не имеет магического доступа к UI-чату VS Code, если app-server не даёт resume.
- Не хранить секреты в `AGENT_SYNC.md`, docs или логах.
- Если бот привязался к неправильному чату, остановить его и удалить `.agents/worker-bot/state.json`.
