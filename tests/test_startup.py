from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from caselight.startup import is_start_with_system_enabled, set_start_with_system


class StartupTests(unittest.TestCase):
    def test_startup_entry_can_be_created_and_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "caselight.desktop"
            set_start_with_system(True, target=target, command=["/opt/Case Light/caselight", "--minimized"])
            content = target.read_text(encoding="utf-8")
            self.assertIn("--minimized", content)
            self.assertTrue(is_start_with_system_enabled(target))
            set_start_with_system(False, target=target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
