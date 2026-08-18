from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def startup_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve()), "--minimized"]
    launcher = Path(__file__).resolve().parents[1] / "caselight_launcher.py"
    return [str(Path(sys.executable).resolve()), str(launcher), "--minimized"]


def startup_file() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "CaseLight.cmd"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart" / "caselight.desktop"


def set_start_with_system(enabled: bool, *, target: Path | None = None, command: list[str] | None = None) -> Path:
    path = target or startup_file()
    if not enabled:
        path.unlink(missing_ok=True)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    argv = command or startup_command()
    if sys.platform == "win32" or path.suffix.lower() == ".cmd":
        content = '@echo off\r\nstart "" ' + subprocess.list2cmdline(argv) + "\r\n"
    else:
        executable = " ".join(shlex.quote(part) for part in argv)
        content = "\n".join(
            (
                "[Desktop Entry]",
                "Type=Application",
                "Name=CaseLight",
                "Comment=Restore case lighting",
                f"Exec={executable}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            )
        )
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
    return path


def is_start_with_system_enabled(target: Path | None = None) -> bool:
    return (target or startup_file()).exists()
