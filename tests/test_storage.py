from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from caselight.storage import STATE_ENV, StateStore, resolve_state_dir


class StorageTests(unittest.TestCase):
    def test_state_survives_atomic_save_reload_and_backup_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(Path(temporary), migrate_legacy=False)
            state = store.load()
            state["brightness"] = 37
            store.save(state)
            state["brightness"] = 62
            store.save(state)
            self.assertEqual(StateStore(Path(temporary), migrate_legacy=False).load()["brightness"], 62)
            store.path.write_text("not json", encoding="utf-8")
            self.assertEqual(StateStore(Path(temporary), migrate_legacy=False).load()["brightness"], 37)
            self.assertFalse((Path(temporary) / ".state.json.tmp").exists())

    def test_environment_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {STATE_ENV: temporary}):
            directory, reason = resolve_state_dir(Path(temporary))
            self.assertEqual(directory, Path(temporary).resolve())
            self.assertIn(STATE_ENV, reason)

    def test_windows_system_drive_state_survives_reload(self) -> None:
        system_root = Path(Path.home().anchor)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(
            os.environ,
            {"APPDATA": temporary, STATE_ENV: ""},
            clear=False,
        ), mock.patch("caselight.storage.sys.platform", "win32"), mock.patch(
            "caselight.storage.volume_root", return_value=system_root
        ):
            first = StateStore(anchor=Path("/installed/CaseLight.exe"), migrate_legacy=False)
            self.assertEqual(first.directory.parts[-2:], ("CaseLight", "data"))
            self.assertEqual(first.location_reason, "per-user fallback")
            state = first.load()
            state["brightness"] = 37
            first.save(state)

            second = StateStore(anchor=Path("/installed/CaseLight.exe"), migrate_legacy=False)
            self.assertEqual(second.load()["brightness"], 37)

    def test_written_state_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(Path(temporary), migrate_legacy=False)
            store.save({"brightness": 44})
            self.assertEqual(json.loads(store.path.read_text(encoding="utf-8"))["brightness"], 44)


if __name__ == "__main__":
    unittest.main()
