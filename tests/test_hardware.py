from __future__ import annotations

import unittest

from caselight.hardware import LightCommand


class HardwareValidationTests(unittest.TestCase):
    def test_command_is_normalized(self) -> None:
        command = LightCommand("LED1", "FIXED", "#ff2ba6", "NORMAL").validated()
        self.assertEqual(command.channel, "led1")
        self.assertEqual(command.color, "FF2BA6")

    def test_invalid_channel_is_rejected_before_usb_access(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown channel"):
            LightCommand("fan99", "fixed").validated()


if __name__ == "__main__":
    unittest.main()
