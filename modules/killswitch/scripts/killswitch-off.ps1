#Requires -RunAsAdministrator
# {{PROJECT_NAME}} killswitch OFF. Run from an elevated PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\killswitch-off.ps1
# Removes firewall rules, WSL iptables rules and the git proxy set by killswitch-on.ps1.

$ErrorActionPreference = 'Stop'
$RulePrefix = "VSCodeProxyKillSwitch"
$ClashProxy = "http://127.0.0.1:{{CLASH_PORT}}"

Get-NetFirewallRule -DisplayName "$RulePrefix*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Write-Host "Firewall: $RulePrefix rules removed"

# Restore Public/Private firewall profiles to disabled (their state before the killswitch).
# Change here if you prefer to keep the firewall enabled after turning the killswitch off.
Set-NetFirewallProfile -Profile Public, Private -Enabled False
Write-Host "Firewall engine: Public/Private profiles disabled (restored)"

# Unset git proxy only if it is the one we set
$gitProxy = git config --global --get http.proxy 2>$null
if ($gitProxy -eq $ClashProxy) {
  git config --global --unset http.proxy
  Write-Host "git: global http.proxy removed"
}

$wslScript = wsl -d {{WSL_DISTRO}} -e wslpath -a "$PSScriptRoot\wsl-killswitch.sh"
wsl -d {{WSL_DISTRO}} -u root -- bash "$wslScript" off

Write-Host "KILLSWITCH OFF"
