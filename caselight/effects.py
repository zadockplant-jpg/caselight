from __future__ import annotations

import array
import colorsys
import math
import sys
from collections.abc import Sequence

SAMPLE_RATE = 11025
CHUNK_BYTES = 4096


def pcm_spectrum_bands(chunk: bytes, sample_rate: int = SAMPLE_RATE) -> tuple[float, float, float]:
    """Estimate bass, middle, and treble energy with a dependency-free FFT."""
    usable = chunk[: len(chunk) - (len(chunk) % 2)]
    samples = array.array("h")
    samples.frombytes(usable)
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) < 64:
        return 0.0, 0.0, 0.0

    count = min(2048, 1 << (len(samples).bit_length() - 1))
    selected = samples[-count:]
    mean = sum(selected) / count
    spectrum = [
        complex((sample - mean) * (0.5 - 0.5 * math.cos(2.0 * math.pi * index / max(1, count - 1))), 0.0)
        for index, sample in enumerate(selected)
    ]
    swap = 0
    for index in range(1, count):
        bit = count >> 1
        while swap & bit:
            swap ^= bit
            bit >>= 1
        swap ^= bit
        if index < swap:
            spectrum[index], spectrum[swap] = spectrum[swap], spectrum[index]

    length = 2
    while length <= count:
        step = complex(math.cos(-2.0 * math.pi / length), math.sin(-2.0 * math.pi / length))
        half = length // 2
        for start in range(0, count, length):
            phase = 1.0 + 0.0j
            for offset in range(half):
                even = spectrum[start + offset]
                odd = spectrum[start + offset + half] * phase
                spectrum[start + offset] = even + odd
                spectrum[start + offset + half] = even - odd
                phase *= step
        length <<= 1

    def level(low_hz: float, high_hz: float) -> float:
        low_bin = max(1, int(low_hz * count / sample_rate))
        high_bin = min(count // 2, math.ceil(high_hz * count / sample_rate))
        peak = max((abs(spectrum[index]) for index in range(low_bin, high_bin)), default=0.0)
        amplitude = 2.0 * peak / (count * 32768.0)
        return min(1.0, math.log1p(amplitude * 55.0) / math.log(56.0))

    return level(40.0, 220.0), level(220.0, 1600.0), level(1600.0, 5200.0)


def hsv_hex(hue: float, saturation: float = 1.0, value: float = 1.0) -> str:
    return "".join(f"{round(channel * 255):02X}" for channel in colorsys.hsv_to_rgb(hue % 1.0, saturation, value))


def beat_multiplier(division: str) -> float:
    return {"1/2 beat": 2.0, "1 beat": 1.0, "2 beats": 0.5, "4 beats": 0.25}.get(division, 1.0)


def effect_frame(
    name: str,
    elapsed: float,
    theme: Sequence[str],
    bpm: int = 120,
    division: str = "1 beat",
) -> tuple[tuple[str, float], tuple[str, float], tuple[str, float]]:
    colors = tuple(theme) or ("00E5FF", "8A5CFF", "FF2BA6")
    beat = elapsed * max(40, min(240, bpm)) / 60.0 * beat_multiplier(division)
    phase = beat % 1.0

    if name == "Breathing":
        intensity = 0.08 + 0.92 * (0.5 - 0.5 * math.cos(phase * 2.0 * math.pi))
        return tuple((colors[index % len(colors)], intensity) for index in range(3))  # type: ignore[return-value]
    if name == "Rainbow wave":
        return tuple((hsv_hex(elapsed * 0.12 + index / 3.0), 1.0) for index in range(3))  # type: ignore[return-value]
    if name == "Color chase":
        active = int(beat * 3.0) % 3
        return tuple(
            (colors[(int(beat) + index) % len(colors)], 1.0 if index == active else 0.08) for index in range(3)
        )  # type: ignore[return-value]
    if name == "Police":
        first, second = ("FF1010", "125CFF") if int(beat * 2.0) % 2 == 0 else ("125CFF", "FF1010")
        return ((first, 1.0), (second, 0.14), (first, 1.0))
    if name == "Ember glow":
        ember = ("FF1700", "FF4D00", "FF8C1A", "FFD166")
        return tuple(
            (
                ember[(int(beat * 4) + index) % len(ember)],
                0.35 + 0.6 * (0.5 + 0.5 * math.sin(elapsed * 5.1 + index * 2.17)),
            )
            for index in range(3)
        )  # type: ignore[return-value]
    if name == "Tempo bounce":
        intensity = 0.08 + 0.92 * math.pow(max(0.0, 1.0 - phase), 2.4)
        return tuple((colors[index % len(colors)], intensity) for index in range(3))  # type: ignore[return-value]
    if name == "Tempo chase":
        active = int(beat) % 3
        return tuple((colors[index % len(colors)], 1.0 if index == active else 0.04) for index in range(3))  # type: ignore[return-value]
    if name == "Tempo rainbow":
        return tuple((hsv_hex((int(beat) / 12.0) + index / 3.0), 1.0) for index in range(3))  # type: ignore[return-value]
    return tuple(
        (colors[(int(beat) + index) % len(colors)], 0.42 + 0.58 * (0.5 + 0.5 * math.sin(elapsed * 2.8 + index * 2.1)))
        for index in range(3)
    )  # type: ignore[return-value]


def music_frame(
    style: str,
    bands: Sequence[float],
    theme: Sequence[str],
    hue: float,
    minimum_glow: float,
) -> tuple[tuple[tuple[str, float], ...], float]:
    bass, middle, treble = (max(0.0, min(1.0, float(value))) for value in bands[:3])
    levels = (bass, middle, treble)
    colors = tuple(theme) or ("00E5FF", "8A5CFF", "FF2BA6")
    floor = max(0.0, min(0.3, minimum_glow))
    energy = max(levels)
    if style == "Bass pulse":
        return (((colors[0], max(floor, bass)),) * 3, hue)
    if style == "Rainbow energy":
        next_hue = (hue + 0.01 + middle * 0.025 + treble * 0.04) % 1.0
        color = hsv_hex(next_hue)
        return (((color, max(floor, energy)),) * 3, next_hue)
    if style == "Beat flash":
        flash = max(floor, math.pow(bass, 1.7))
        return (tuple((colors[index % len(colors)], flash) for index in range(3)), hue)
    if style == "Heatmap":
        palette = ("FF253A", "FFB25C", "FFFFFF")
        return (tuple((palette[index], max(floor, levels[index])) for index in range(3)), hue)
    palette = ("FF2BA6", "8A5CFF", "00E5FF") if style == "Spectrum" else colors
    return (tuple((palette[index % len(palette)], max(floor, levels[index])) for index in range(3)), hue)
