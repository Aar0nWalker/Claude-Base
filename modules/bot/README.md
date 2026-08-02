# Telegram Worker Bot

Локальный Telegram-бот: ставить агентам задачи с телефона, получать статусы и отвечать на их
вопросы, в том числе голосом. На прод-сервере не запускается.

Опциональная часть заготовки. Не пользуетесь — удалите бота, его скрипты и этот файл на
бутстрапе: мёртвая обвязка читается как живая и стоит следующей сессии времени.

## Установка

1. Создать бота у `@BotFather`, забрать токен.
2. Узнать свой Telegram user id (например, через `@userinfobot`).
3. Прописать в `.env` (см. переменные ниже):
   ```
   WORKER_BOT_TOKEN=...
   WORKER_BOT_ALLOWED_USER_IDS=...
   ```
4. Запустить.

Зависимостей нет: `worker_bot.py` написан на голой стандартной библиотеке, нужен только Python 3.

## Запуск

```bash
bash modules/bot/scripts/start-worker-bot.sh     # фоном, pid в .agents/worker-bot/bot.pid
bash modules/bot/scripts/worker-bot.sh check
bash modules/bot/scripts/worker-bot.sh queue
bash modules/bot/scripts/stop-worker-bot.sh
```

Runtime (очередь, статусы, история) хранится в `.agents/worker-bot/` и не коммитится.

## Хук сессии

`modules/bot/scripts/agent-task-hook.sh` подмешивает взятую задачу в контекст новой сессии —
он прописан в `.claude/settings.json` на `SessionStart` и `UserPromptSubmit`. Если модуль
удалить, хук тихо ничего не делает: сессия из-за него не сломается.

## Переменные

- `WORKER_BOT_TOKEN` - токен Telegram-бота.
- `WORKER_BOT_ALLOWED_USER_IDS` - whitelist Telegram user ID через запятую (свой узнать через `@userinfobot`).
- `WORKER_BOT_ALLOWED_CHAT_ID` - опциональная жёсткая привязка к чату.
- `GOOGLE_API_KEY` - нужен для расшифровки голосовых.
- `WORKER_BOT_TRANSCRIBE_MODEL` - опционально, по умолчанию `gemini-2.5-flash`.
- `WORKER_BOT_GOOGLE_BASE_URL` - опционально, по умолчанию Google Generative Language API.
- `WORKER_BOT_PROXY_URL` - proxy, если Telegram напрямую недоступен (см. модуль killswitch).

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

- `+ Claude` - положить задачу в очередь агента.
- `Статус` - задачи в работе, очередь, вопросы и последние статусы агентов.

Автоматического диспетчера нет: задача лежит в очереди, пока агент не заберёт её сам —
`./scripts/worker-bot.sh next Claude` или через хук сессии. Очередь рассчитана на несколько
агентов: имя агента задаётся аргументом, добавить второго — значит просто разбирать очередь
под другим именем.

В статусе и сообщениях о принятой задаче бот показывает inline-кнопки `Отменить #id`. Нажатие переводит задачу в `cancelled` и убирает её из очереди.

Вопросы от агентов приходят отдельным сообщением с именем агента, `Q{id}` и временем. Нажми в Telegram `Ответить` на это сообщение и отправь текст; бот привяжет ответ к нужному вопросу и поставит follow-up задачу агенту.

## Сообщения

Основной формат без номера задачи:

```text
Claude -- Bob

✅ Задачу принял и работает

Ответ от агента:
Текст ответа
```

Пока есть задача в статусе `claimed`, бот шлёт Telegram `typing` action как working heartbeat. Это не создаёт лишних сообщений.

## Agent CLI

```bash
./scripts/worker-bot.sh next Claude
./scripts/worker-bot.sh status Claude "Взял задачу #12"
./scripts/worker-bot.sh ask Claude "Нужен деплой?"
./scripts/worker-bot.sh done 12
./scripts/worker-bot.sh queue
./scripts/worker-bot.sh context Claude
```

## Чаты агентов

Бот хранит короткую историю агентских задач в runtime-директории `.agents/worker-bot/`.

- `.agents/worker-bot/agents/<имя>/chat.md` - чат и задачи конкретного агента.
- `.agents/worker-bot/context.md` - компактная общая лента последних событий по задачам.
- `.agents/worker-bot/inbox.md` - обзор очереди, статусов и вопросов.

`context.md`/`inbox.md` закоммичены как пустые шаблоны (см. `.gitignore`), чтобы бот не падал на
чистом чекауте; дальше бот их перезаписывает и они живут как runtime-состояние. `agents/*` и
`screenshots/*` — чистый runtime, гитигнорятся целиком. `context.md` нужен, чтобы агент,
взявший задачу, не сканировал весь проект заново.

## Как агент забирает задачи

Автоматического диспетчера в шаблоне нет — очередь разбирает интерактивная сессия агента:

```bash
./scripts/worker-bot.sh next Claude      # взять следующую задачу
./scripts/worker-bot.sh status|ask|done|queue
```

Мост к Codex через app-server был удалён вместе с диспетчером: он завязан на конкретную
локальную установку расширения и ломался чаще, чем работал. Если нужен автоматический разбор
очереди без человека — поднимать его отдельно поверх `worker-bot.sh` и описывать здесь.

## Ограничения

- Бот не имеет магического доступа к UI-чату VS Code, если app-server не даёт resume.
- Не хранить секреты в `AGENT_SYNC.md`, docs или логах.
- Если бот привязался к неправильному чату, остановить его и удалить `.agents/worker-bot/state.json`.
