# Сетевой киллсвитч: VS Code + агенты + WSL только через прокси

> Полная картина, troubleshooting и как перенести технологию на нового агента:
> [../docs/proxy-killswitch.md](../docs/proxy-killswitch.md). Этот файл — краткий операционный.


Весь трафик инструментов разработки идёт через Clash Verge Rev (`127.0.0.1:{{CLASH_PORT}}` на Windows) и дальше через купленный прокси. Если Clash выключен — инструменты **теряют сеть полностью**, в обход не ходят.

## Схема

```
VS Code / расширения / терминалы (Windows) ──┐
                                             ├─→ Clash Verge (127.0.0.1:{{CLASH_PORT}}) ─→ купленный прокси ─→ интернет
Codex → Headroom (127.0.0.1:8788, WSL) ──────┤       (выход: 203.0.113.10)
WSL-шеллы / агенты (через 172.17.x.x:{{CLASH_PORT}}) ──┘
```

Блокировки (два уровня):
- **Windows Firewall**: `Code.exe`, `node.exe`, `git.exe`, `python.exe`, `curl.exe`, npm/pnpm/yarn/bun/deno — прямой интернет и DNS запрещены; работать могут только через прокси.
- **WSL ({{WSL_DISTRO}}) iptables**: весь прямой исходящий трафик отклоняется (REJECT). Открыто: localhost, приватные сети (в т.ч. Windows-хост с Clash и DNS), прод-сервер `{{PROD_IP}}`. Правила переживают перезапуск WSL (systemd-юнит `{{PROJECT_SLUG}}-killswitch`).

## Включить / выключить

Из **PowerShell от администратора**:

```powershell
powershell -ExecutionPolicy Bypass -File {{PROJECT_PATH_WIN}}\scripts\killswitch-on.ps1
powershell -ExecutionPolicy Bypass -File {{PROJECT_PATH_WIN}}\scripts\killswitch-off.ps1
```

`killswitch-on.ps1` в конце сам прогоняет проверки (утечка из WSL, выход через Clash, Headroom, доступ к проду) и печатает PASS/FAIL.

Статус WSL-части отдельно:

```bash
wsl -d {{WSL_DISTRO}} -u root -- bash {{PROJECT_PATH_WSL}}/scripts/wsl-killswitch.sh status
```

## Как поменять прокси

Купленный прокси прописан **только в Clash** — киллсвитч привязан к порту {{CLASH_PORT}}, а не к адресу прокси. Поэтому:

1. Clash Verge → Профили/Прокси → добавить новый сервер, выбрать его в активной группе.
2. Всё. Скрипты, конфиги, env трогать не нужно.
3. Проверка: `curl.exe -x http://127.0.0.1:{{CLASH_PORT}} https://api.ipify.org` → должен показать IP нового прокси.

Если меняется **порт** Clash (не {{CLASH_PORT}}) — поменять его в: `settings.json` VS Code (`http.proxy`, `terminal.integrated.env.windows`), `~/.profile` в WSL (блок {{PROJECT_NAME}} killswitch), `scripts/start-headroom.sh`, `scripts/killswitch-*.ps1`.

Если меняется **IP прод-сервера** — обновить `ALLOW_IPS` в `scripts/wsl-killswitch.sh` и `NO_PROXY` в `~/.profile` (WSL), затем перезапустить: `killswitch-on.ps1`.

## Кто как ходит в сеть

| Компонент | Путь | Заблокирован напрямую? |
|---|---|---|
| VS Code (обновления, маркетплейс) | `http.proxy` → Clash | да (firewall) |
| Codex extension (WSL) | Headroom `127.0.0.1:8788` → Clash | да (iptables) |
| Codex OAuth-refresh | `~/.profile` env → Clash | да (iptables) |
| Headroom → OpenAI | env `172.17.192.1:{{CLASH_PORT}}` → Clash | да (iptables) |
| Терминалы Windows (git, curl, node, python) | env из `terminal.integrated.env.windows` → Clash | да (firewall) |
| git.exe вне терминалов VS Code | global `http.proxy` → Clash | да (firewall) |
| WSL-шеллы и агенты | env из `~/.profile` → Clash | да (iptables) |
| deploy.sh (ssh/rsync на прод) | напрямую на `{{PROD_IP}}` | нет — исключение |
| Claude Code (claude.exe, Windows) | `ANTHROPIC_BASE_URL` → Headroom `127.0.0.1:8788` → Clash; прочее → `HTTPS_PROXY` Clash | да (firewall) |
| Docker Desktop контейнеры (worker-bot и т.п.) | напрямую через `com.docker.backend` | нет — вне киллсвитча |

## Claude Code через Headroom

Claude Code (`claude.exe`) настроен в `~/.claude/settings.json` (блок `env`):
- `ANTHROPIC_BASE_URL=http://127.0.0.1:8788` — модельные запросы идут в Headroom (сжатие токенов) → Clash → Anthropic. Тот же путь, что у Codex.
- `HTTP_PROXY`/`HTTPS_PROXY=http://127.0.0.1:{{CLASH_PORT}}` — прочий трафик Claude (обновления, плагины) → Clash.
- `NO_PROXY=127.0.0.1,localhost,::1` — loopback к Headroom/Clash не заворачивается.

`claude.exe` (и бинарь в расширении, и `.local\bin`) заблокирован в firewall напрямую — работает только через loopback. Правило `env` применяется к **новой** сессии Claude, не к текущей.

## Windows: остаточный риск (важно понимать)

Windows Firewall блокирует **по конкретному .exe**. Каждый тулчейн тащит свой `curl`/`node`/`python` (system32, Git `mingw64\bin`+`usr\bin`, Anaconda `Library\bin`, scoop, choco, cargo…). Скрипт свипит эти корни по именам сетевых бинарников и блокирует все найденные копии — проверено на всех трёх curl. Но:

- Это **не доказуемо-полный** список: портативный или свеже-скачанный `curl.exe` в непросвипанной папке, или бинарник с сетевым стеком, игнорирующий `HTTP_PROXY`, теоретически может уйти напрямую при явном `--noproxy`.
- **На практике риск мал**: (1) агенты (Claude, Codex) ходят через Headroom/Clash, не через эти бинарники; (2) WSL — default-deny (iptables), там утечь нечем; (3) терминалы VS Code получают `HTTP_PROXY` из `terminal.integrated.env.windows`, поэтому обычный запуск инструмента идёт через Clash **даже без** firewall-правила — утечка возможна только при осознанном обходе прокси.
- Новый тулчейн со своим `curl` → добавь его корень в `$SweepRoots` в `killswitch-on.ps1` и перезапусти.
- Абсолютный ноль-дыр на Windows даёт только глобальный default-deny (блок всего исходящего кроме Clash) — но это затронет браузеры и все приложения, поэтому не делаем (ты просил не глобально).

## Известные дыры (осознанные)

1. **Docker Desktop** — контейнеры (worker-bot → Telegram) живут в отдельном дистрибутиве `docker-desktop`, iptables {{WSL_DISTRO}} их не касается. Закрыть можно firewall-правилом на `com.docker.backend.exe`, но это отрежет контейнерам весь интернет.
3. **Произвольный exe в Windows-терминале** — блокируются только перечисленные бинарники (Code.exe, node, git, python, curl, npm/npx/pnpm/yarn/bun/deno + все node из nvm). Новый инструмент со своим сетевым стеком надо добавить в `$Commands` в `killswitch-on.ps1` и перезапустить. Полный блок «всё кроме Clash» не делаем — отрежет браузеры и прочие Windows-приложения.
4. **DNS Windows-системы** — сами DNS-запросы системы идут напрямую (стандартно для HTTP-прокси); у заблокированных программ DNS отрезан, имена резолвит прокси через CONNECT.

## Диагностика

```bash
# WSL: не утекает?
wsl -d {{WSL_DISTRO}} -u {{WSL_USER}} -- curl -s -m 8 --noproxy '*' https://api.ipify.org   # должно молчать/падать
# WSL: через Clash работает?
wsl -d {{WSL_DISTRO}} -u {{WSL_USER}} -- bash -lc 'curl -s -m 10 https://api.ipify.org'      # должен показать IP прокси
# Headroom жив?
curl.exe --noproxy "*" -fsS http://127.0.0.1:8788/livez
# Codex ходит? (лог Headroom в WSL)
wsl -u {{WSL_USER}} -- bash -c "tail -f ~/.headroom/logs/proxy.log | grep responses"
```

Особенности реализации (почему так):
- **Windows Firewall был выключен** для профилей Public/Private — при выключенном профиле block-правила не действуют. `killswitch-on.ps1` включает движок с `DefaultInboundAction Allow` / `DefaultOutboundAction Allow`, поэтому меняется только поведение наших block-правил, входящие соединения (WSL→Clash, Radmin, локальные серверы) не затрагиваются. `killswitch-off.ps1` возвращает Public/Private в disabled.
- **node.exe под nvm-windows** — это симлинк (`C:\Program Files\nodejs` → версионная папка). Firewall матчит реальный путь образа, поэтому скрипт резолвит симлинки и блокирует все `node.exe` во всех версиях nvm. Иначе node (его спавнят агенты) утекает напрямую.
- Блок задан явными публичными диапазонами IPv4/IPv6 (не ключевым словом `Internet`, которое ненадёжно и молча не срабатывает).

Типовые проблемы:
- **Всё умерло** → Clash выключен или упал. Включи Clash, проверь `curl.exe -x http://127.0.0.1:{{CLASH_PORT}} https://api.ipify.org`.
- **WSL не видит Clash** → в Clash должен быть включён Allow LAN + inbound-правило firewall для порта {{CLASH_PORT}} (vEthernet WSL).
- **Codex: «stream disconnected / error sending request»** → перезапусти окно VS Code (респавн codex с env из `~/.profile`); проверь Headroom (`scripts/start-headroom.sh`).
- **Codex просит перелогиниться** → OAuth-refresh не прошёл; проверь, что `~/.profile` содержит блок «{{PROJECT_NAME}} killswitch» и Clash работает.
