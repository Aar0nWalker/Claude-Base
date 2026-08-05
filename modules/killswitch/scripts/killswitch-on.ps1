#Requires -RunAsAdministrator
# {{PROJECT_NAME}} killswitch ON. Run from an elevated PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\killswitch-on.ps1
#
# What it does:
#  1. Windows Firewall: blocks direct internet (+DNS) for VS Code and common
#     dev binaries, so they can only reach the net through Clash (127.0.0.1:{{CLASH_PORT}}).
#     claude.exe is deliberately NOT blocked (Claude works direct for now).
#     ssh.exe is NOT blocked (prod deploy needs it; it carries no AI traffic).
#  2. git: sets global http.proxy so git works without env vars.
#  3. WSL ({{WSL_DISTRO}}): applies iptables killswitch via scripts/wsl-killswitch.sh.
#  4. Verifies the whole chain and prints PASS/FAIL.
#
# Docs: scripts/KILLSWITCH.md

$ErrorActionPreference = 'Stop'
$RulePrefix = "VSCodeProxyKillSwitch"
$ClashProxy = "http://127.0.0.1:{{CLASH_PORT}}"

# --- 0. Enable firewall engine (rules do nothing if the profile is disabled) --
# Keep default actions = Allow both ways, so ONLY our explicit block rules change
# behaviour. Inbound stays open (WSL->Clash on {{CLASH_PORT}}, Radmin, local servers unaffected).
Set-NetFirewallProfile -Profile Public, Private, Domain -Enabled True -DefaultInboundAction Allow -DefaultOutboundAction Allow
Write-Host "Firewall engine: enabled (default in/out = Allow; only killswitch block rules apply)"

# --- 1. Firewall rules -------------------------------------------------------
Get-NetFirewallRule -DisplayName "$RulePrefix*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule

$AppPaths = @(
  "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe",
  "$env:ProgramFiles\Microsoft VS Code\Code.exe"
)

# ssh.exe intentionally absent: prod deploy (rsync/ssh) must keep working.
# claude.exe IS blocked: Claude Code is routed via HTTPS_PROXY=127.0.0.1:{{CLASH_PORT}} (Clash)
# in ~/.claude/settings.json, so it only needs loopback. Blocking direct closes the
# fallback hole.
$Commands = @(
  "node.exe", "git.exe", "python.exe", "python3.exe", "curl.exe",
  "npm.cmd", "npx.cmd", "pnpm.cmd", "yarn.cmd", "bun.exe", "deno.exe",
  "claude.exe"
)

foreach ($cmd in $Commands) {
  $found = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($found -and $found.Source -and (Test-Path $found.Source)) {
    $AppPaths += $found.Source
  }
}

# nvm-windows exposes node via a symlink (C:\Program Files\nodejs -> versioned dir).
# Windows Firewall matches the REAL image path, so add every node.exe under nvm too,
# and resolve any symlink to its target. Otherwise node (what agents spawn) leaks.
foreach ($nvmRoot in @("$env:APPDATA\nvm", "$env:ProgramFiles\nvm", "$env:NVM_HOME")) {
  if ($nvmRoot -and (Test-Path $nvmRoot)) {
    Get-ChildItem -Path $nvmRoot -Recurse -Filter node.exe -ErrorAction SilentlyContinue | ForEach-Object { $AppPaths += $_.FullName }
  }
}
# Claude Code ships its own claude.exe inside the VS Code extension (versioned path);
# that is the binary the extension host runs, not (only) the one on PATH. Add every
# version so a Claude update doesn't reopen the hole.
Get-ChildItem -Path "$env:USERPROFILE\.vscode\extensions" -Recurse -Filter claude.exe -ErrorAction SilentlyContinue | ForEach-Object { $AppPaths += $_.FullName }

# Every toolchain (Git, Anaconda, scoop, choco, ...) bundles its OWN curl/node/python.
# Get-Command finds only the first on PATH, so the others leak on --noproxy. Sweep the
# common install roots by binary name and block every copy found. Not provably
# exhaustive (see KILLSWITCH.md "Windows: остаточный риск"), but closes the real ones.
$SweepRoots = @(
  "$env:ProgramFiles\Git", "${env:ProgramFiles(x86)}\Git", "$env:LOCALAPPDATA\Programs\Git",
  "$env:USERPROFILE\anaconda3", "$env:USERPROFILE\miniconda3",
  "$env:LOCALAPPDATA\Continuum", "$env:ProgramData\Anaconda3",
  "$env:USERPROFILE\scoop", "$env:ProgramData\chocolatey",
  "$env:USERPROFILE\.cargo\bin", "$env:LOCALAPPDATA\Programs"
)
$NetBins = @("curl.exe", "wget.exe", "node.exe", "python.exe", "pythonw.exe")
foreach ($root in ($SweepRoots | Sort-Object -Unique)) {
  if ($root -and (Test-Path $root)) {
    Get-ChildItem -Path $root -Recurse -Include $NetBins -ErrorAction SilentlyContinue | ForEach-Object { $AppPaths += $_.FullName }
  }
}

# Expand each path to itself + its resolved symlink target.
$expanded = @()
foreach ($p in $AppPaths) {
  if (-not (Test-Path $p)) { continue }
  $expanded += $p
  $tgt = (Get-Item $p -ErrorAction SilentlyContinue).Target
  if ($tgt) { if ([System.IO.Path]::IsPathRooted($tgt)) { $expanded += $tgt } else { $expanded += (Join-Path (Split-Path $p) $tgt) } }
}
$AppPaths = $expanded | Where-Object { Test-Path $_ } | Sort-Object -Unique

# All public IPv4, excluding loopback (127/8), RFC1918 private, link-local (169.254/16).
# Block rules take precedence over allow; loopback stays open so 127.0.0.1:{{CLASH_PORT}} (Clash) works.
$PublicV4 = @(
  "0.0.0.0-9.255.255.255",
  "11.0.0.0-126.255.255.255",
  "128.0.0.0-169.253.255.255",
  "169.255.0.0-172.15.255.255",
  "172.32.0.0-192.167.255.255",
  "192.169.0.0-223.255.255.255"
)
# Public IPv6 (global unicast). Loopback ::1, link-local fe80::/10, ULA fc00::/7 stay open.
$PublicV6 = "2000::/3"

$i = 0
foreach ($app in $AppPaths) {
  $i++
  $exe = [System.IO.Path]::GetFileName($app)
  New-NetFirewallRule -DisplayName "$RulePrefix $i Internet Block v4 $exe" -Direction Outbound -Program $app -Action Block -RemoteAddress $PublicV4 -Profile Any | Out-Null
  New-NetFirewallRule -DisplayName "$RulePrefix $i Internet Block v6 $exe" -Direction Outbound -Program $app -Action Block -RemoteAddress $PublicV6 -Profile Any | Out-Null
}
Write-Host "Firewall: blocked direct internet for:"
$AppPaths | ForEach-Object { Write-Host "  $_" }

# --- 2. git global proxy (so blocked git.exe still works via Clash) ----------
$gitProxy = git config --global --get http.proxy 2>$null
if (-not $gitProxy) {
  git config --global http.proxy $ClashProxy
  Write-Host "git: set global http.proxy = $ClashProxy"
} elseif ($gitProxy -ne $ClashProxy) {
  Write-Host "git: global http.proxy already set to '$gitProxy' - left untouched"
}

# --- 3. WSL part --------------------------------------------------------------
$wslScript = wsl -d {{WSL_DISTRO}} -e wslpath -a "$PSScriptRoot\wsl-killswitch.sh"
wsl -d {{WSL_DISTRO}} -u root -- bash "$wslScript" on

# --- 4. Verification ----------------------------------------------------------
Write-Host ""
Write-Host "=== Verification ==="
$fail = 0

# Clash up and exiting through the expected proxy
$exitIp = curl.exe -s -m 10 -x $ClashProxy https://api.ipify.org
if ($exitIp) { Write-Host "PASS clash exit IP: $exitIp" } else { Write-Host "FAIL clash unreachable on {{CLASH_PORT}} - is Clash Verge running?"; $fail++ }

# Windows leak test: every curl.exe on the box must NOT reach the internet directly
# (system32 + git-bundled). Each is a separate binary and needs its own block rule.
$curls = @("C:\WINDOWS\system32\curl.exe")
$curls += (& where.exe curl.exe 2>$null)
foreach ($gitRoot in @("$env:ProgramFiles\Git", "$env:LOCALAPPDATA\Programs\Git")) {
  if (Test-Path $gitRoot) { $curls += (Get-ChildItem $gitRoot -Recurse -Filter curl.exe -EA SilentlyContinue).FullName }
}
foreach ($cx in ($curls | Where-Object { $_ -and (Test-Path $_) } | Sort-Object -Unique)) {
  $winLeak = & $cx -s -m 8 --noproxy '*' https://api.ipify.org 2>&1
  if ([string]::IsNullOrWhiteSpace($winLeak) -or $winLeak -match 'timed out|Failed|refused|unreachable|Recv failure') { Write-Host "PASS direct blocked: $cx" } else { Write-Host "FAIL leaks direct ($winLeak): $cx"; $fail++ }
}
$nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
if ($nodeExe) {
  $nodeLeak = & $nodeExe -e "require('https').get({host:'api.ipify.org',timeout:7000},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>console.log('LEAK '+d))}).on('error',e=>console.log('BLOCKED')).on('timeout',function(){this.destroy();console.log('BLOCKED')})" 2>&1
  if ($nodeLeak -match 'BLOCKED') { Write-Host "PASS Windows node.exe direct blocked" } else { Write-Host "FAIL Windows node.exe leaks direct ($nodeLeak) - nvm symlink not resolved?"; $fail++ }
}

# WSL leak test: direct internet from WSL must be blocked
$wslLeak = wsl -d {{WSL_DISTRO}} -u {{WSL_USER}} -- bash -c "curl -s -m 8 --noproxy '*' https://api.ipify.org 2>/dev/null; exit 0"
if ([string]::IsNullOrWhiteSpace($wslLeak)) { Write-Host "PASS WSL direct internet blocked" } else { Write-Host "FAIL WSL leaks directly (got $wslLeak)"; $fail++ }

# WSL via Clash must work (login shell = same path agents use, proxy from ~/.profile)
$wslViaClash = wsl -d {{WSL_DISTRO}} -u {{WSL_USER}} -- bash -lc 'curl -s -m 10 https://api.ipify.org 2>/dev/null; exit 0'
if ($wslViaClash) { Write-Host "PASS WSL via Clash: $wslViaClash" } else { Write-Host "FAIL WSL cannot reach Clash (Allow LAN / firewall inbound rule?)"; $fail++ }

# Agent path: model API must be reachable through Clash (401 = route alive, no tokens spent)
$anthCode = curl.exe -s -o NUL -w "%{http_code}" -m 10 -x $ClashProxy https://api.anthropic.com/v1/messages -H "x-api-key: killswitch-probe" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" -d '{"model":"claude-3-5-haiku-20241022","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}'
if ($anthCode -eq '401') { Write-Host "PASS model API reachable via Clash" } else { Write-Host "FAIL model API via Clash returned $anthCode"; $fail++ }

# Prod reachable from WSL (deploy path)
$prod = wsl -d {{WSL_DISTRO}} -u {{WSL_USER}} -- bash -c "timeout 5 bash -c '</dev/tcp/{{PROD_IP}}/22' 2>/dev/null && echo ok; exit 0"
if ($prod -match 'ok') { Write-Host "PASS prod {{PROD_IP}}:22 reachable from WSL" } else { Write-Host "FAIL prod unreachable from WSL"; $fail++ }

Write-Host ""
if ($fail -eq 0) { Write-Host "KILLSWITCH ON - all checks passed" } else { Write-Host "KILLSWITCH ON with $fail failed check(s) - see above" }
