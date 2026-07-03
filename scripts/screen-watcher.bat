@echo off
rem Start the Telegram screen watcher detached (no console window).
rem Put a shortcut to this file into shell:startup for autostart.
start "" /min pythonw "%~dp0screen-watcher.py"
