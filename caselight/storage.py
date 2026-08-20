from __future__ import annotations

import json
import os
import shutil
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model import APP_NAME, DEFAULT_STATE, normalize_state

STATE_ENV = "CASELIGHT_STATE_DIR"
STATE_FOLDER_NAME = ".caselight"
STATE_FILE_NAME = "state.json"
LOCATOR_FILE_NAME = "state-location.json"


def local_config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "caselight"


def application_anchor() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(__file__).resolve().parents[1]


def volume_root(path: Path) -> Path:
    resolved = path.resolve()
    if sys.platform == "win32":
        return Path(resolved.anchor)
    current = resolved if resolved.is_dir() else resolved.parent
    while current.parent != current and not os.path.ismount(current):
        current = current.parent
    return current


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    try:
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        directory_fd = os.open(path.parent, directory_flags)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:
        # Directory fsync is unavailable on some Windows filesystems.  The
        # atomic replacement above still keeps the profile valid.
        pass


def resolve_state_dir(anchor: Path | None = None) -> tuple[Path, str]:
    override = os.environ.get(STATE_ENV)
    if override:
        return Path(override).expanduser().resolve(), f"{STATE_ENV} override"

    locator = local_config_dir() / LOCATOR_FILE_NAME
    try:
        data = _read_json(locator)
        selected = Path(str(data["path"])).expanduser()
        if selected.exists() and selected.is_dir():
            return selected.resolve(), "saved shared location"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        pass

    root = volume_root(anchor or application_anchor())
    if root != Path(root.anchor) or os.access(root, os.W_OK):
        return root / STATE_FOLDER_NAME, "same-volume shared profile"
    return local_config_dir() / "data", "per-user fallback"


def save_locator(path: Path) -> None:
    _atomic_json(
        local_config_dir() / LOCATOR_FILE_NAME,
        {"path": str(path.resolve()), "saved_at": datetime.now(UTC).isoformat()},
    )


def speechless_settings_candidates() -> tuple[Path, ...]:
    candidates = [
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "codex-assistant" / "settings.json",
    ]
    if sys.platform == "win32":
        candidates.append(Path(os.environ.get("APPDATA", Path.home())) / "codex-assistant" / "settings.json")
    return tuple(dict.fromkeys(candidates))


class StateStore:
    """Atomic, backup-backed state stored outside replaceable application files."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        anchor: Path | None = None,
        migrate_legacy: bool = True,
    ) -> None:
        if directory is None:
            self.directory, self.location_reason = resolve_state_dir(anchor)
        else:
            self.directory = Path(directory).expanduser().resolve()
            self.location_reason = "explicit location"
        self.path = self.directory / STATE_FILE_NAME
        self.backup_path = self.directory / f"{STATE_FILE_NAME}.backup"
        self.migrate_legacy = migrate_legacy
        self._io_lock = threading.RLock()

    def load(self) -> dict[str, Any]:
        with self._io_lock:
            if not self.path.exists():
                migrated = self._load_speechless_state() if self.migrate_legacy else None
                state = normalize_state(migrated if migrated is not None else DEFAULT_STATE)
                self.save(state)
                return state
            try:
                return normalize_state(_read_json(self.path))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                try:
                    recovered = normalize_state(_read_json(self.backup_path))
                    recovered["updated_at"] = datetime.now(UTC).isoformat()
                    _atomic_json(self.path, recovered)
                    return recovered
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    return normalize_state(DEFAULT_STATE)

    def save(self, state: dict[str, Any]) -> None:
        with self._io_lock:
            clean = normalize_state(state)
            clean["updated_at"] = datetime.now(UTC).isoformat()
            self.directory.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                temporary_backup = self.backup_path.with_name(f".{self.backup_path.name}.tmp")
                shutil.copy2(self.path, temporary_backup)
                os.replace(temporary_backup, self.backup_path)
            _atomic_json(self.path, clean)

    def move_to(self, directory: Path, state: dict[str, Any]) -> StateStore:
        resolved = Path(directory).expanduser().resolve()
        app_path = application_anchor()
        app_root = app_path if app_path.is_dir() else app_path.parent
        try:
            resolved.relative_to(app_root)
        except ValueError:
            pass
        else:
            raise ValueError("Choose a shared state folder outside the CaseLight application directory.")
        destination = StateStore(resolved)
        destination.save(state)
        save_locator(destination.directory)
        return destination

    def _load_speechless_state(self) -> Any | None:
        for candidate in speechless_settings_candidates():
            try:
                data = _read_json(candidate)
                if isinstance(data, dict) and isinstance(data.get("rgb_lighting"), dict):
                    return data["rgb_lighting"]
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return None
