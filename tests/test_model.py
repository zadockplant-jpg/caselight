from __future__ import annotations

import unittest

from caselight.model import color_at_brightness, normalize_hex, normalize_state


class ModelTests(unittest.TestCase):
    def test_color_normalization_and_brightness_preserve_hue(self) -> None:
        self.assertEqual(normalize_hex("#ff8040"), "FF8040")
        self.assertEqual(normalize_hex("broken", "8a5cff"), "8A5CFF")
        self.assertEqual(color_at_brightness("FF8040", 50), "804020")
        self.assertEqual(color_at_brightness("FF8040", 80, 0.25), "331A0D")

    def test_speechless_lighting_shape_migrates(self) -> None:
        state = normalize_state(
            {
                "rgb_lighting": {
                    "brightness": 37,
                    "theme": "Cyberpunk",
                    "effect": "Rainbow wave",
                    "music_style": "CAVA spectrum",
                    "active_mode": "effect",
                    "sources": {"case_1": {"channel": "led7", "color": "123456"}},
                }
            }
        )
        self.assertEqual(state["brightness"], 37)
        self.assertEqual(state["theme"], "Cyberpunk")
        self.assertEqual(state["music"]["style"], "Spectrum")
        self.assertEqual(state["zones"]["case_1"]["channel"], "led7")

    def test_invalid_values_are_clamped(self) -> None:
        state = normalize_state({"brightness": 200, "tempo_bpm": 2, "animation_fps": 90})
        self.assertEqual(state["brightness"], 100)
        self.assertEqual(state["tempo_bpm"], 40)
        self.assertEqual(state["animation_fps"], 12)


if __name__ == "__main__":
    unittest.main()
