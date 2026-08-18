from __future__ import annotations

import math
import struct
import unittest

from caselight.effects import SAMPLE_RATE, effect_frame, music_frame, pcm_spectrum_bands
from caselight.model import SOFTWARE_EFFECTS, THEMES


class SpectrumTests(unittest.TestCase):
    @staticmethod
    def sine(frequency: float) -> bytes:
        samples = [int(24000 * math.sin(2.0 * math.pi * frequency * index / SAMPLE_RATE)) for index in range(2048)]
        return struct.pack("<" + "h" * len(samples), *samples)

    def test_silence_is_silent(self) -> None:
        self.assertEqual(pcm_spectrum_bands(bytes(4096)), (0.0, 0.0, 0.0))

    def test_frequency_bands_are_separated(self) -> None:
        for expected, frequency in enumerate((90.0, 500.0, 3000.0)):
            bands = pcm_spectrum_bands(self.sine(frequency))
            self.assertGreater(bands[expected], 0.65)
            self.assertEqual(max(range(3), key=bands.__getitem__), expected)


class EffectTests(unittest.TestCase):
    def test_every_software_effect_produces_three_clean_zones(self) -> None:
        for name in SOFTWARE_EFFECTS:
            frame = effect_frame(name, 1.25, THEMES["Neon Harbor"], 128, "1 beat")
            self.assertEqual(len(frame), 3)
            for color, intensity in frame:
                self.assertRegex(color, r"^[0-9A-F]{6}$")
                self.assertGreaterEqual(intensity, 0.0)
                self.assertLessEqual(intensity, 1.0)

    def test_music_styles_return_three_zones(self) -> None:
        for style in ("Spectrum", "Three-band", "Bass pulse", "Rainbow energy", "Beat flash", "Heatmap"):
            frame, hue = music_frame(style, (0.2, 0.5, 0.8), THEMES["Ocean"], 0.2, 0.03)
            self.assertEqual(len(frame), 3)
            self.assertGreaterEqual(hue, 0.0)
            self.assertLessEqual(hue, 1.0)


if __name__ == "__main__":
    unittest.main()
