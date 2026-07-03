# Прокси-киллсвитч: VS Code, расширения, терминалы, WSL — только через прокси

Мастер-документ. Весь трафик инструментов разработки и AI-агентов (Claude, Codex)
идёт **только** через купленный прокси; прямой выход физически заблокирован. Если
прокси недоступен — инструменты теряют сеть полностью, в обход не идут (killswitch).

Операционный quick-ref: [../scripts/KILLSWITCH.md](../scripts/KILLSWITCH.md).
Этот файл — полная картина + troubleshooting + как перенести технологию.

---

## 1. Архитектура

```
┌─ Windows ────────────────────────────────────────────────────────────────┐
│  VS Code, node, git, python, curl (system32/Git/Anaconda) ─┐             │
│  Claude Code (claude.exe)  ── ANTHROPIC_BASE_URL ─┐         │             │
│                             ── HTTPS_PROXY ────────┤         │             │
│                                                    ▼         ▼             │
│                                        Clash Verge Rev  127.0.0.1:{{CLASH_PORT}} ──┐ │
│  ┌─ WSL ({{WSL_DISTRO}}) ──────────────────────────────────┐        ▲           │ │
│  │  Codex (расширение + бот) → Headroom 127.0.0.1:8788 ──────┤ (через    │ │
│  │  Claude-модель ─────────────→ Headroom 127.0.0.1:8788 ────┤  host_ip  │ │
│  │  WSL-шеллы/агенты ── HTTP_PROXY(host_ip:{{CLASH_PORT}}) ────────────┘  :{{CLASH_PORT}})   │ │
│  │  iptables: default-deny прямого выхода (REJECT)             │         │ │
│  └────────────────────────────────────────────────────────────┘         │ │
└──────────────────────────────────────────────────────────────────────────┘ │
                                                                              ▼
                                              купленный прокси 203.0.113.10 ─→ интернет
```

**Ключевой принцип:** ничего не знает про адрес купленного прокси, кроме Clash.
Все указывают на **порт {{CLASH_PORT}}** (Clash) или на **Headroom 8788** (который сам ходит
через Clash). Сменить прокси = поменять сервер в Clash, конфиги не трогать.

---

## 2. Компоненты и адреса

| Компонент | Адрес / путь | Роль |
|---|---|---|
| Clash Verge Rev | `127.0.0.1:{{CLASH_PORT}}` (Windows) | локальный прокси → купленный прокси |
| Купленный прокси (exit) | `203.0.113.10` (пример — IP вашего купленного прокси) | реальный выход в интернет |
| Реальный IP компа | `198.51.100.20` | **не должен светиться наружу** |
| Headroom | `127.0.0.1:8788` (WSL) | AI-прокси (сжатие токенов) → Clash |
| Headroom binary | `{{PROJECT_PATH_WSL}}/.venv-headroom/bin/headroom` | |
| Headroom request-логи | `~/.headroom/logs/proxy.log` (WSL) | реальные запросы |
| Headroom stdout-лог | `.headroom/proxy.log` (в проекте) | только запуск/ошибки старта |
| WSL host_ip (Clash изнутри WSL) | `172.17.192.1` (из `/etc/resolv.conf`) | **может меняться**, не хардкодить |
| Прод-сервер | `{{PROD_IP}}` | исключение (deploy напрямую) |

---

## 3. Что через что ходит

| Клиент | Путь | Заблокирован напрямую |
|---|---|---|
| Claude Code (claude.exe, Win) | `ANTHROPIC_BASE_URL` → Headroom → Clash; прочее → `HTTPS_PROXY` Clash | да (firewall) |
| Codex (расширение, WSL) | Codex app-server → Headroom → Clash | да (iptables) |
| Codex (бот-диспетчер, WSL) | `codex-app-send.py` → тот же app-server → Headroom → Clash | да (iptables) |
| Headroom → OpenAI/Anthropic | env `HTTP_PROXY=host_ip:{{CLASH_PORT}}` → Clash | да (iptables) |
| Терминалы VS Code (Win) | `terminal.integrated.env.windows` → Clash | да (firewall) |
| WSL-шеллы и агенты | `~/.profile` → Clash (host_ip:{{CLASH_PORT}}) | да (iptables) |
| git вне терминалов (Win) | git global `http.proxy` → Clash | да (firewall) |
| deploy.sh (ssh/rsync) | напрямую на `{{PROD_IP}}` | нет — исключение |
| Docker-контейнеры (worker-bot) | напрямую (дистрибутив `docker-desktop`) | **нет — вне киллсвитча** |

---

## 4. Файлы конфигурации (фактическое состояние)

### 4.1 Windows Firewall + git — `scripts/killswitch-on.ps1` / `killswitch-off.ps1`
Блокирует прямой выход по конкретным .exe (VS Code, node+все nvm, git, python,
curl из system32/Git/Anaconda, claude.exe в т.ч. в расширении). Включает
firewall-движок (`Set-NetFirewallProfile -Enabled True -DefaultInbound/Outbound Allow`),
ставит git global `http.proxy`, дёргает WSL-часть, в конце — self-verification.

### 4.2 WSL iptables — `scripts/wsl-killswitch.sh`
Default-deny прямого исходящего (REJECT). Разрешено: loopback, приватные сети
(Clash+DNS), прод `{{PROD_IP}}`. Переживает рестарт WSL через systemd-юнит
`{{PROJECT_SLUG}}-killswitch`. Исключения — массив `ALLOW_IPS`.

### 4.3 WSL прокси-env — `~/.profile` (у пользователя {{WSL_USER}}, НЕ в репозитории)
```bash
if [ -z "${HTTP_PROXY:-}" ] || [ "$HTTP_PROXY" = "http://127.0.0.1:{{CLASH_PORT}}" ]; then
    _wip=$(grep -m1 nameserver /etc/resolv.conf | awk '{print $2}')
    export HTTP_PROXY="http://$_wip:{{CLASH_PORT}}" HTTPS_PROXY="http://$_wip:{{CLASH_PORT}}"
    unset _wip
fi
export NO_PROXY="localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,{{PROD_IP}}"
export http_proxy="$HTTP_PROXY" https_proxy="$HTTPS_PROXY" no_proxy="$NO_PROXY"
```
Чинит и баг расширения Codex (оно инжектит мёртвый `127.0.0.1:{{CLASH_PORT}}` в WSL).

### 4.4 Claude Code — `C:\Users\1\.claude\settings.json` (НЕ в репозитории)
```json
"env": {
  "ANTHROPIC_BASE_URL": "http://127.0.0.1:8788",
  "HTTP_PROXY": "http://127.0.0.1:{{CLASH_PORT}}",
  "HTTPS_PROXY": "http://127.0.0.1:{{CLASH_PORT}}",
  "NO_PROXY": "127.0.0.1,localhost,::1"
}
```
Применяется к **новой** сессии Claude (после reload окна).

### 4.5 Codex — `~/.codex/config.toml` (WSL, НЕ в репозитории)
```toml
model_provider = "headroom"
openai_base_url = "http://127.0.0.1:8788/v1"

[model_providers.headroom]
name = "Headroom init proxy"
base_url = "http://127.0.0.1:8788/v1"
supports_websockets = false
requires_openai_auth = true
```

### 4.6 VS Code — `C:\Users\1\AppData\Roaming\Code\User\settings.json`
```json
"http.proxy": "http://127.0.0.1:{{CLASH_PORT}}",
"http.proxySupport": "on",
"http.noProxy": ["localhost", "127.0.0.1", "::1"],
"terminal.integrated.env.windows": {
  "HTTP_PROXY": "http://127.0.0.1:{{CLASH_PORT}}",
  "HTTPS_PROXY": "http://127.0.0.1:{{CLASH_PORT}}",
  "NO_PROXY": "localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
}
```

### 4.7 Headroom запуск — `scripts/start-headroom.sh`
Автоопределяет host_ip из resolv.conf, экспортит `HTTP_PROXY=host_ip:{{CLASH_PORT}}`,
запускает `headroom proxy --port 8788 --mode token --backend anthropic`. Healthcheck
`curl --noproxy "*" http://127.0.0.1:8788/livez`.

---

## 5. Включить / выключить

**Windows (PowerShell от администратора):**
```powershell
powershell -ExecutionPolicy Bypass -File {{PROJECT_PATH_WIN}}\scripts\killswitch-on.ps1
powershell -ExecutionPolicy Bypass -File {{PROJECT_PATH_WIN}}\scripts\killswitch-off.ps1
```
`on` в конце сам гоняет проверки (утечки curl/node, WSL, Headroom, прод) → PASS/FAIL.

**Headroom (WSL), если не поднят:**
```bash
{{PROJECT_PATH_WSL}}/scripts/start-headroom.sh
```

**Только WSL-часть / статус:**
```bash
wsl -d {{WSL_DISTRO}} -u root -- bash {{PROJECT_PATH_WSL}}/scripts/wsl-killswitch.sh status
```

---

## 6. Как поменять прокси

Купленный прокси прописан **только в Clash**. Киллсвитч привязан к порту {{CLASH_PORT}}.
1. Clash Verge → Proxies/Profiles → добавить сервер, выбрать в активной группе.
2. Всё. Конфиги/скрипты/env не трогать.
3. Проверка: `curl.exe -x http://127.0.0.1:{{CLASH_PORT}} https://ipinfo.io/ip` → новый IP.

**Если меняется порт Clash** (не {{CLASH_PORT}}) — поменять в: VS Code `settings.json`
(`http.proxy` + `terminal.integrated.env.windows`), `~/.profile` (WSL),
`scripts/start-headroom.sh`, `scripts/killswitch-*.ps1`.

**Если меняется IP прода** — `ALLOW_IPS` в `wsl-killswitch.sh` + `NO_PROXY` в
`~/.profile`, затем перезапустить `killswitch-on.ps1`.

---

## 7. Проверка (правильные команды)

**Главное правило: loopback (Headroom/Clash на 127.0.0.1) тестировать ТОЛЬКО с
`--noproxy '*'`.** Иначе `curl` отдаёт запрос в прокси, тот стучится в свой
localhost — ложный «не отвечает».

**С Windows:**
```powershell
curl.exe -x http://127.0.0.1:{{CLASH_PORT}} https://ipinfo.io/ip        # -> 203.0.113.10
curl.exe --noproxy "*" -fsS http://127.0.0.1:8788/livez       # -> healthy
& C:\WINDOWS\system32\curl.exe -s --noproxy "*" https://api.ipify.org  # пусто = блок
```

**С WSL:**
```bash
curl --noproxy '*' -s -m5 http://127.0.0.1:8788/livez          # healthy
bash -lc 'curl -s -m10 https://api.ipify.org'                  # -> 203.0.113.10
curl -s -m5 --noproxy '*' https://api.ipify.org; echo $?       # пусто, exit!=0 = блок
WIP=$(grep -m1 nameserver /etc/resolv.conf|awk '{print $2}')
curl -s -x "http://$WIP:{{CLASH_PORT}}" https://api.ipify.org            # -> 203.0.113.10
```

**Агенты ходят через Headroom (в WSL):**
```bash
grep 'path=/v1/messages.*status=200'  ~/.headroom/logs/proxy.log | tail   # Claude
grep 'path=/v1/responses.*status=200' ~/.headroom/logs/proxy.log | tail   # Codex
```

**Тест киллсвитча (выключить Clash):** выключаешь Clash → Claude, Codex, терминалы
перестают отвечать, наружу мимо прокси не идут. Включаешь → снова `203.0.113.10`.

---

## 8. Troubleshooting (все реальные грабли)

| Симптом | Причина | Решение |
|---|---|---|
| Всё умерло разом | Clash выключен/упал | Включить Clash; `curl.exe -x http://127.0.0.1:{{CLASH_PORT}} https://ipinfo.io/ip` |
| Claude/Codex молчит, сеть вроде есть | Headroom не поднят | `scripts/start-headroom.sh`; проверить livez |
| `curl.exe` напрямую отдал реальный IP | firewall-правил нет ИЛИ бинарник не в списке | см. ниже «утечка» |
| **Firewall-правил `0`, но профили Enabled** | `killswitch-on.ps1` оборвался на середине (UAC/окно закрыли) | перезапустить `killswitch-on.ps1` целиком от админа |
| **Firewall не блокирует вообще** | профили Public/Private были **выключены** (Enabled False) | `killswitch-on.ps1` включает их с `DefaultInbound/Outbound Allow` |
| **node утекает, curl нет** | node под nvm — это **симлинк**; firewall матчит реальный путь | скрипт резолвит симлинки + свипит все nvm-версии |
| **git-bash/Anaconda curl утекает** | каждый тулчейн везёт свой `curl.exe` | скрипт свипит `$SweepRoots` по именам бинарников |
| Codex: «Headroom не отвечает» из WSL | тест без `--noproxy` → ушёл в прокси | тестировать `curl --noproxy '*' http://127.0.0.1:8788/livez` |
| Codex: «Clash 172.17.192.1 не отвечает» | захардкожен старый host_ip | брать из `resolv.conf`; в env — брать динамически |
| Codex: «stream disconnected / error sending request» | старый env расширения (мёртвый `127.0.0.1:{{CLASH_PORT}}`) | reload окна VS Code (respawn codex с `~/.profile`) |
| WSL не видит Clash | нет Allow LAN в Clash / нет inbound-правила firewall на {{CLASH_PORT}} | включить Allow LAN + inbound-правило для vEthernet WSL |
| Codex/Claude просит перелогиниться | OAuth-refresh не прошёл | проверить блок «killswitch» в `~/.profile` + что Clash жив |
| host_ip сменился после ребута | WSL NAT выдаёт новый IP | `~/.profile` и `start-headroom.sh` берут его динамически — просто перезапустить Headroom |

**Аварийное отключение всего** (если киллсвитч мешает):
```powershell
powershell -ExecutionPolicy Bypass -File {{PROJECT_PATH_WIN}}\scripts\killswitch-off.ps1
```

---

## 9. Как перенести технологию на нового клиента (Claude/Codex/любой)

Рецепт «завернуть новый AI-инструмент в Headroom + Clash»:

1. **Определи, где он бежит** — Windows или WSL (`ps aux | grep <tool>`, смотри путь
   бинарника). От этого зависит, каким слоем блокировать (firewall vs iptables).
2. **Определи, какой конфиг он читает** — часто расширение и CLI читают разные файлы.
   Проверь env процесса: `tr '\0' '\n' < /proc/<pid>/environ | grep -i proxy`.
3. **Направь его API-эндпоинт в Headroom:**
   - OpenAI-совместимый (Codex): `openai_base_url = http://127.0.0.1:8788/v1` + provider-блок.
   - Anthropic (Claude): `ANTHROPIC_BASE_URL=http://127.0.0.1:8788`.
   - Headroom роутит по пути (`/v1/responses` → OpenAI, `/v1/messages` → Anthropic).
4. **Прочий трафик клиента** (обновления, плагины) → `HTTP(S)_PROXY=<Clash>`,
   `NO_PROXY=127.0.0.1,localhost,::1` (чтобы loopback к Headroom не заворачивался).
5. **Заблокируй прямой выход бинарника:**
   - Windows: добавь .exe в `$Commands`/`$SweepRoots` в `killswitch-on.ps1`, резолвь симлинки.
   - WSL: уже покрыт default-deny (`wsl-killswitch.sh`), ничего не надо.
6. **Проверь маршрут без трат:** запрос в Headroom с фейковым ключом → ждёшь `401`
   от upstream (значит роут до провайдера через Clash жив):
   ```bash
   curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -X POST \
     http://127.0.0.1:8788/v1/messages -H 'x-api-key: test' \
     -H 'anthropic-version: 2023-06-01' \
     -d '{"model":"claude-3-5-haiku-20241022","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}'
   ```
7. **Перезапусти клиент** (новый процесс подхватит env) и убедись в логе Headroom,
   что появились его запросы со `status=200`.
8. **Закрой фолбэк:** перезапусти `killswitch-on.ps1` — прямой выход бинарника заблокируется.

> ВАЖНО при блокировке живой сессии Claude: если клиент уже идёт через Headroom
> (loopback), firewall его не рвёт. Если ещё напрямую — блокировка оборвёт его на
> следующем запросе. Сначала переведи на Headroom (reload), потом блокируй.

---

## 10. Известный остаточный риск

- **Windows firewall блокирует по .exe** — не доказуемо-полно. Новый портативный
  `curl.exe`/тулчейн в непросвипанной папке может утечь при явном `--noproxy`.
  На практике мало: агенты через Headroom, WSL default-deny, терминалы получают
  `HTTP_PROXY`. Новый тулчейн → добавить корень в `$SweepRoots` + перезапуск.
- **Docker Desktop** — контейнеры (worker-bot → Telegram) в дистрибутиве
  `docker-desktop`, iptables {{WSL_DISTRO}} их не касается. Для проксирования бота-трафика
  задать `WORKER_BOT_PROXY_URL` в env compose (переменные уже проброшены в
  `docker-compose.yml`). Модельные запросы бота к Codex уже идут через Headroom.
- **Абсолютный ноль-дыр на Windows** = глобальный default-deny (блок всего кроме
  Clash), но он рубит браузеры и все приложения — **не делаем** (не глобально).

---

## 11. Хронология решённых проблем (чтобы не повторять)

1. Codex не доходил до Headroom — VS Code пробрасывал `http.proxy=127.0.0.1:{{CLASH_PORT}}`
   с пустым `NO_PROXY`, в WSL этот адрес мёртв. Фикс: `~/.profile` переписывает на host_ip.
2. Windows Firewall был **выключен** для Public/Private — правила не действовали.
3. `-RemoteAddress Internet` ненадёжен — заменён на явные публичные диапазоны IPv4/IPv6.
4. node под nvm — симлинк, firewall не матчил → добавлен резолв симлинков + свип nvm.
5. git-bash и Anaconda везут свой `curl` → добавлен свип тулчейн-корней.
6. Claude переведён с прямого выхода на Headroom (`ANTHROPIC_BASE_URL`) + блок claude.exe.
7. Codex-само-диагностика врала: тест Headroom без `--noproxy` + хардкод host_ip.
