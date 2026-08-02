#!/usr/bin/env bash
# Narrow check for the zone you touched — the routine-turn companion to the full gate.
#
#   bash scripts/ci/check.sh backend     # fast lane, if the project defines that zone
#   bash scripts/ci/check.sh             # same as the full gate
#
# There is deliberately no separate "tier" mechanism: a narrow check is just the gate with a
# smaller zone, so it keeps every guard (hang timeout, full logs, verdict line). Zones live in
# scripts/ci/zones/ — see the README there.
#
# A deploy always runs the FULL zone. Narrowing it for a release is the user's call to make,
# never the agent's (AGENTS.md → Mandatory quality floor).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec env GATE_ZONE="${1:-full}" bash "$ROOT/scripts/ci/test-gate.sh"
