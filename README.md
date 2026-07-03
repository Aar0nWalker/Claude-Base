# Oridium Code Base

Готовый к работе **шаблон-заготовка для SaaS**, извлечённый из боевого проекта. Клонируешь,
запускаешь `follow init.md` — и стартуешь не с пустой папки, а с рабочего скелета auth + admin,
с уже подключённым деплоем, инструментами для параллельной работы агентов и прокси-килсвитчем.

Он **обобщённый**: никакой доменной логики (нет видео/AI/маркетплейса), нет биллинга. Только
переиспользуемая инфраструктура, которую каждый SaaS переписывает заново.

## Что внутри

**Стек** — FastAPI + async SQLAlchemy + Postgres (бэкенд) · Next.js 16 + React 19 + TS (фронтенд) ·
ARQ + Redis (воркер) · Docker Compose + Nginx + certbot. Фронтенд → бэкенд через прокси `/backend/*`.

| Область | Что получаешь |
|---------|---------------|
| **Auth** | Регистрация / вход / подтверждение почты / сброс пароля, JWT (httpOnly-кука), bcrypt, инвалидация сессий. |
| **Admin** | Пользователи, настройки приложения, редактируемые системные промпты, лог ошибок — за `require_admin` (админ = `ADMIN_EMAIL`). |
| **Инфра бэкенда** | Идемпотентные миграции на старте (без Alembic), S3 + локальное хранилище, SMTP-почта, rate-limit (slowapi), скелет ARQ-воркера, опциональный Anthropic-хелпер для текста. |
| **Инфра фронтенда** | App-shell, дашборд, профиль, admin, минимальный лендинг, провайдеры toast/confirm/auth, UI-примитивы, CSS на дизайн-токенах, единый обёртка `apiFetch`. |
| **Ops** | `install.sh` (разовая настройка сервера: Docker/Nginx/UFW/TLS), `deploy.sh` (rsync + rolling-пересборка), `rollback.sh`, `start.sh` (локальное Docker-меню). |
| **Параллельные агенты** | Реестр `.agents/wip.md` + хендофф `AGENT_SYNC.md` + Telegram worker-bot для общего рабочего дерева Claude ↔ Codex. |
| **Прокси-килсвитч** | Скрипты для Windows + WSL, которые гонят весь dev-трафик через прокси (Clash) или роняют сеть — плюс опциональный Headroom (прокси со сжатием токенов). |
| **Конфиг агентов** | `AGENTS.md` / `.claude/CLAUDE.md` (правила, обратная совместимость, безопасность), пермишены, хуки, 7 базовых инженерных скиллов, команды `выкати` / `автопилот`. |

## Быстрый старт

```bash
# 1. Клонируешь в папку нового проекта
git clone https://github.com/Aar0nWalker/Oridium-Code-Base .

# 2. Заполняешь плейсхолдеры — открываешь Claude/Codex и запускаешь:
follow init.md
#    → спросит имя проекта / домен / пути, заменит каждый {{PLACEHOLDER}},
#      скопирует .env.example → .env, сгенерит MVP.md, удалит init.md.

# 3a. Локально
cp .env.example .env   # (это делает init.md) — задай JWT_SECRET, POSTGRES_PASSWORD, ADMIN_PASSWORD
bash start.sh          # → 1) Запуск

# 3b. Прод-сервер (Debian/Ubuntu, под root)
sudo bash install.sh   # Docker + Nginx + UFW + TLS, затем сборка образов
# потом со своей машины:
./deploy.sh            # rsync + rolling-пересборка
```

API не поднимется, пока `JWT_SECRET` не изменён с дефолтного — задай его в `.env`.

## Структура

```
├── AGENTS.md  .claude/CLAUDE.md      # правила агентов (общие) + специфика Claude
├── STACK.md  ARCH.md                 # дефолты стека + карта архитектуры
├── RTK.md  PLUGINS.md                # тулинг: RTK, ponytail, caveman, Headroom, uv
├── init.md                           # разовый прогон заполнения плейсхолдеров (удалить после)
├── .env.example                      # ключи env (без секретов) — скопировать в .env
├── docker-compose.yml                # web · api · worker-fast · redis · db · worker-bot
├── install.sh  deploy.sh  rollback.sh  start.sh
├── backend/   FastAPI-приложение (app/{main,db,models,routers/*,deps,storage,email,worker,ai_text})
├── frontend/  Next.js-приложение (app/, components/, lib/, styles/)
├── scripts/   worker-bot + killswitch + headroom
├── docs/      telegram-worker-bot.md · proxy-killswitch.md
├── .agents/   реестр wip.md + скелет worker-bot/
└── .claude/   settings.json · commands/ · skills/base/
```

## Что стоит знать

- **Миграции** идемпотентны и прогоняются на каждом старте (`backend/app/db.py`): `create_all` +
  список `ALTER ... IF NOT EXISTS`. Чтобы поменять схему — правишь `models.py` и дописываешь ещё
  один идемпотентный стейтмент. Alembic нет.
- **Параллельные агенты** делят одно рабочее дерево — перед правкой застолби строку в
  `.agents/wip.md`; коммить только свои файлы; деплой эксклюзивен. Полный протокол в [AGENTS.md](AGENTS.md).
- **Скиллы** лежат в `.claude/skills/base/` — грузи тот, что релевантен задаче (планирование, реализация,
  дебаг, безопасность, ревью, фронтенд, автопилот).
- **Килсвитч** (опционально) гонит dev-трафик через прокси, чтобы ничего не утекало напрямую — см.
  [scripts/KILLSWITCH.md](scripts/KILLSWITCH.md).

## Плагины и тулинг

Инструменты Claude Code / агентов, которые ускоряют работу в этом репо. **Claude-плагины ставятся
глобально в `~/.claude/` (один раз на машину) и НЕ коммитятся сюда.** Проект собирается и работает
без любого из них — это удобства для разработчика. Подробнее в [PLUGINS.md](PLUGINS.md).

| Плагин | Зачем | Ссылка |
|--------|-------|--------|
| **RTK** (Rust Token Killer) | Оборачивает shell-команды и возвращает компактный вывод (или пропускает как есть) — большая экономия токенов на билдах/тестах/git. | [github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk) · локальная обёртка в [RTK.md](RTK.md) |
| **ponytail** | Режим «ленивого сеньора» — форсит простейшее рабочее решение, борется с оверинжинирингом. | Маркетплейс плагинов Claude Code: `/plugin install ponytail` |
| **caveman** | Сжимает текстовые ответы Claude без потери технической точности. | [github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| **karpathy-skills** | Глобальный набор скиллов в `CLAUDE.md`, улучшающий поведение при кодинге. | [github.com/forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) |
| **Headroom** | MCP/HTTP-прокси со сжатием запросов к модели; умеет гнать трафик агента через твой прокси (Clash). Включай вместе с килсвитчем. | подключение в [PLUGINS.md](PLUGINS.md) и [docs/proxy-killswitch.md](docs/proxy-killswitch.md) |
| **uv / uvx** | Быстрый Python-раннер — локальный фоллбэк, когда Docker недоступен (напр. `uv run pytest`). | [astral.sh/uv](https://astral.sh/uv) |

## Что шаблон намеренно опускает

Биллинг и любую продуктовую/доменную логику — добавляй их поверх auth/admin-базы как новые роутеры +
модели + миграции, следуя правилам обратной совместимости в AGENTS.md. AI ограничен опциональным
Anthropic-хелпером для текста (`backend/app/ai_text.py`); image/video/другие провайдеры подключай под проект.
