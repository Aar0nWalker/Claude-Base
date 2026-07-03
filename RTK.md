# RTK - Rust Token Killer

**Usage**: token-optimized CLI proxy for shell commands. Prefix commands with `rtk`
and it either applies a dedicated compact filter or passes through unchanged — so
it's always safe to use. Optional; install globally (see PLUGINS.md) or skip it.

## Rule

Always prefix shell commands with `rtk` when it's on PATH.

If `rtk` is not on PATH but a local wrapper exists at `.tools/bin/rtk`:

```bash
export PATH="$PWD/.tools/bin:$PATH"
```

Examples:

```bash
rtk git status
rtk pytest -q
rtk npm run build
rtk tsc --noEmit
```

## Meta Commands

```bash
rtk gain            # Token savings analytics
rtk gain --history  # Recent command savings history
rtk proxy <cmd>     # Run raw command without filtering
```
