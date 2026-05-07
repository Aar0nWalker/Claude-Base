# Project Init

You are initializing a new project from templates. Follow the steps below exactly.

---

## Step 1 — Ask questions

Ask the user ALL of the following questions in a single message, numbered list. Wait for answers before doing anything else.

1. **Project name** — used in file headers, script titles, nginx conf name.
2. **Mission** — 1-2 sentences: what does it do and who uses it?
3. **Off-limits** — deferred features or hard constraints for this MVP. (or "none")
4. **Server** — SSH address for deploy (e.g. `root@1.2.3.4`).
5. **Remote project path** — folder on server (e.g. `/root/myproject`).
6. **WinSCP session name** — name of the saved session in WinSCP app.
7. **Folders to sync** — which local dirs to upload (e.g. `backend`, `frontend`). Files `.env`, `docker-compose.yml`, `install.sh`, `start.sh` are always included.

---

## Step 2 — Defaults (never ask about these)

Defaults live in `STACK.md` — read it now. Apply silently when a module is needed in a future request. Do not pre-populate ARCH.md with modules that haven't been requested yet.

---

## Step 3 — Fill the templates

Read each file, fill every `TODO` and `[Project Name]` placeholder.

### CLAUDE.md
- Replace `[Project Name]` in the title.
- Fill `## Off-Limits` from Q3. If "none" — write `<!-- none for this project -->`.

### ARCH.md
- **Mission**: Q2 answer.
- **Stack**: leave as TODO comment — filled as modules are added.
- **Layer Map**: leave as TODO — filled as modules are added.
- **Key Modules**: leave placeholder row.
- **Runtime Constraints**: fill universal rules only (no sync sessions, secrets from env, no hardcoded model names). Leave project-specific ones as TODO.
- **Testing**: leave as TODO.

### start.sh and start.bat
- Set `PROJECT_NAME` to Q1 answer.

### install.sh
- Set `PROJECT_NAME` to Q1 answer.
- Set `NGINX_CONF` to slugified project name + `.conf` (lowercase, spaces → hyphens).
- Leave `ENV_OVERRIDES=()` empty — add entries when frontend is added (e.g. `NEXT_PUBLIC_API_URL`, `COOKIE_SECURE`).

### STACK.md
- No changes needed — it is the permanent defaults reference.

### .env (create new file)
Create `.env` in project root with deploy variables:

```
DEPLOY_SERVER=<Q4>
DEPLOY_WINSCP_SITE=<Q6>
DEPLOY_PATH=<Q5>
```

Replace `<Q4>` with Q4 answer, `<Q5>` with Q5 answer, `<Q6>` with Q6 answer.

### deploy.bat
Update to read `DEPLOY_WINSCP_SITE` from `.env` and pass it to WinSCP as parameter:

```batch
@echo off

for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0.env") do (
    if "%%a"=="DEPLOY_WINSCP_SITE" set "DEPLOY_WINSCP_SITE=%%b"
    if "%%a"=="DEPLOY_PATH" set "DEPLOY_PATH=%%b"
)

del "%~dp0deploy.log" 2>nul

echo [1/2] Uploading files...
"TODO: C:\path\to\WinSCP.com" /script="%~dp0deploy.winscp" /parameter "%DEPLOY_WINSCP_SITE%" "%DEPLOY_PATH%" /log="%~dp0deploy.log" /console
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Deploy failed. See deploy.log for details.
    exit /b 1
)

echo.
echo [OK] Deploy complete.
```

### deploy.ps1 (create new file)
Generate `deploy.ps1` in project root using this exact structure:

```powershell
$ErrorActionPreference = "Stop"
$plink  = "C:\Program Files\PuTTY\plink.exe"  # TODO: adjust if PuTTY installed elsewhere
$winscp = "TODO: C:\path\to\WinSCP.com"

# Read deploy vars from .env
Get-Content "$PSScriptRoot\.env" | Where-Object { $_ -match '^[^#].+=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    Set-Variable -Name $k.Trim() -Value $v.Trim()
}

Remove-Item "$PSScriptRoot\deploy.log" -ErrorAction SilentlyContinue

Write-Host "[1/2] Uploading files..."
& $winscp /script="$PSScriptRoot\deploy.winscp" /parameter "$DEPLOY_WINSCP_SITE" "$DEPLOY_PATH" /log="$PSScriptRoot\deploy.log"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Upload failed. See deploy.log for details."
    exit 1
}
Write-Host "[1/2] Upload complete."
Write-Host ""

Write-Host "[2/2] Deploying on server..."
$is_fresh = (& $plink -ssh $DEPLOY_SERVER -batch "command -v docker &>/dev/null && echo NO || echo YES").Trim()

if ($is_fresh -eq "YES") {
    Write-Host "First deploy — running install.sh (may take 5-10 min)..."
    & $plink -ssh $DEPLOY_SERVER -batch "chmod +x $DEPLOY_PATH/*.sh && echo Y | bash $DEPLOY_PATH/install.sh"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] install.sh failed."
        exit 1
    }
    Write-Host ""
    Write-Host "Starting project..."
    & $plink -ssh $DEPLOY_SERVER -batch "cd $DEPLOY_PATH && docker compose up -d"
} else {
    Write-Host "Rebuilding on server (this may take a few minutes)..."
    & $plink -ssh $DEPLOY_SERVER -batch @"
cd $DEPLOY_PATH && BUILDKIT_PROGRESS=plain bash start.sh --rebuild > /tmp/deploy_build.log 2>&1; EC=`$?; cat /tmp/deploy_build.log; exit `$EC
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] Rebuild failed. Fetching service logs..."
        Write-Host ""
        & $plink -ssh $DEPLOY_SERVER -batch "cd $DEPLOY_PATH && docker compose logs --tail=100 --no-color 2>&1"
        exit 1
    }
}

Write-Host ""
Write-Host "[OK] Deploy complete."
```

Leave `$winscp` as TODO — user fills it.

### deploy.winscp (create new file)
Generate `deploy.winscp` in project root:

```
option batch abort
option confirm off
open %1%

<sync lines for each folder from Q7>
put "<LOCAL_PATH>\.env"               %2%/
put "<LOCAL_PATH>\docker-compose.yml" %2%/
put "<LOCAL_PATH>\install.sh"         %2%/
put "<LOCAL_PATH>\start.sh"           %2%/

exit
```

- `%1%` = session name (`DEPLOY_WINSCP_SITE` from `.env`), passed via `/parameter`.
- `%2%` = remote path (`DEPLOY_PATH` from `.env`), passed as second `/parameter` value.
- For each folder in Q7: `synchronize remote -delete "<LOCAL_PATH>\<folder>" %2%/<folder>`
- `<LOCAL_PATH>` = absolute local project path (ask user if not obvious from context — write as literal path).

---

## Step 4 — Write MVP plan

Write `MVP.md` in the project root. Structure:

```
# [Project Name] — MVP Plan

## Goal
One sentence: what the MVP proves or delivers.

## Scope
Bulleted list of features included in MVP.

## Out of scope
Bulleted list from Q3 (off-limits / deferred).

## Milestones
Ordered list of implementation phases, each with a 1-line description.
```

Base content on Q2 (mission) and Q3 (off-limits). Keep it short and concrete — no fluff.

---

## Step 5 — Confirm and delete

After writing all files, output a single summary:

```
✓ CLAUDE.md
✓ ARCH.md
✓ STACK.md  (defaults reference — do not delete)
✓ start.sh / start.bat
✓ install.sh
✓ MVP.md
✓ .env  (fill other app secrets as needed)
✓ deploy.ps1  (fill $winscp path, adjust $plink if non-default)
✓ deploy.winscp
✓ deploy.bat  (fill WinSCP.com path)

Project: [name]
```

Then delete this file (`init.md`).
