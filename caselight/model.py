from __future__ import annotations

import copy
import re
from typing import Any

APP_NAME = "CaseLight"
APP_VERSION = "1.0.0"

CHANNELS = ("sync", "led1", "led2", "led3", "led4", "led5", "led6", "led7", "led8")
MODES = ("fixed", "pulse", "flash", "double-flash", "color-cycle", "off")
MODES_WITH_COLOR = {"fixed", "pulse", "flash", "double-flash"}
SPEEDS = ("slowest", "slower", "normal", "faster", "fastest", "ludicrous")

ZONES = (
    ("case_1", "Case 1", "led1", "00E5FF"),
    ("cooler", "Cooler", "led2", "8A5CFF"),
    ("case_2", "Case 2", "led3", "FF2BA6"),
)

COLOR_PRESETS = (
    ("Cyan", "00E5FF"),
    ("Aqua", "00FFD1"),
    ("Royal", "315CFF"),
    ("Violet", "8A5CFF"),
    ("Pink", "FF2BA6"),
    ("Red", "FF253A"),
    ("Amber", "FFB25C"),
    ("Lime", "A8FF4D"),
    ("Green", "21D97A"),
    ("Orange", "FF6B1A"),
    ("Gold", "FFD166"),
    ("White", "FFFFFF"),
)

THEMES = {
    "Neon Harbor": ("00E5FF", "8A5CFF", "FF2BA6"),
    "Ocean": ("006BFF", "00FFD1", "315CFF"),
    "Sunset": ("FF5A3C", "FFB25C", "FF2BA6"),
    "Aurora": ("00FF9A", "58A6FF", "A855F7"),
    "Synth": ("FF2BA6", "00E5FF", "7C3AED"),
    "Ember": ("FF2A1A", "FF7A1A", "FFD166"),
    "Ice": ("9AE6FF", "FFFFFF", "5C7CFF"),
    "Cyberpunk": ("FFE600", "FF00A8", "00F0FF"),
    "Vaporwave": ("FF71CE", "01CDFE", "B967FF"),
    "Galaxy": ("27187E", "758BFD", "F1A7FE"),
    "Midnight": ("071952", "0B666A", "35A29F"),
    "Miami": ("FF206E", "FBFF12", "41EAD4"),
    "Matrix": ("00FF41", "008F11", "003B00"),
    "Halloween": ("FF6D00", "6A00F4", "151515"),
    "Holiday": ("E63946", "2A9D55", "FFF4D6"),
    "Candy": ("FF6FB5", "7AF7FF", "FFF275"),
    "Solar": ("FFB703", "FB8500", "8ECAE6"),
    "Zen": ("84A98C", "CAD2C5", "52796F"),
}

EFFECTS = (
    "Static",
    "Breathing",
    "Rainbow wave",
    "Color chase",
    "Police",
    "Ember glow",
    "Aurora wave",
    "Tempo bounce",
    "Tempo chase",
    "Tempo rainbow",
    "Hardware pulse",
    "Hardware flash",
    "Hardware double flash",
    "Hardware rainbow",
)
HARDWARE_EFFECTS = {
    "Static": "fixed",
    "Hardware pulse": "pulse",
    "Hardware flash": "flash",
    "Hardware double flash": "double-flash",
    "Hardware rainbow": "color-cycle",
}
SOFTWARE_EFFECTS = tuple(name for name in EFFECTS if name not in HARDWARE_EFFECTS)
MUSIC_STYLES = ("Spectrum", "Three-band", "Bass pulse", "Rainbow energy", "Beat flash", "Heatmap")
BEAT_DIVISIONS = ("1/2 beat", "1 beat", "2 beats", "4 beats")

DEFAULT_STATE: dict[str, Any] = {
    "schema_version": 1,
    "brightness": 80,
    "power_on": True,
    "theme": "Neon Harbor",
    "solid_color": "00E5FF",
    "effect": "Rainbow wave",
    "tempo_bpm": 120,
    "beat_division": "1 beat",
    "animation_fps": 5,
    "restore_on_startup": True,
    "start_with_system": False,
    "active_mode": "theme",
    "last_active_mode": "theme",
    "music": {
        "style": "Spectrum",
        "sensitivity": 100,
        "smoothing": 72,
        "minimum_glow": 3,
        "fps": 5,
        "bass_gain": 100,
        "mid_gain": 100,
        "treble_gain": 100,
    },
    "zones": {
        key: {"name": label, "channel": channel, "mode": "fixed", "color": color, "speed": "normal"}
        for key, label, channel, color in ZONES
    },
    "window_geometry": "auto",
}


def clamp_number(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        number = fallback
    return max(low, min(high, number))


def normalize_hex(value: Any, fallback: str = "00E5FF") -> str:
    text = str(value or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", text):
        text = str(fallback).strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", text):
        text = "00E5FF"
    return text.upper()


def color_at_brightness(value: Any, brightness: Any, intensity: float = 1.0) -> str:
    color = normalize_hex(value)
    factor = clamp_number(brightness, 0, 100, 80) / 100.0
    factor *= max(0.0, min(1.0, float(intensity)))
    channels = (int(color[index : index + 2], 16) for index in (0, 2, 4))
    return "".join(f"{max(0, min(255, round(channel * factor))):02X}" for channel in channels)


def normalize_state(raw: Any) -> dict[str, Any]:
    incoming = raw if isinstance(raw, dict) else {}
    if isinstance(incoming.get("rgb_lighting"), dict):
        incoming = incoming["rgb_lighting"]
    state = copy.deepcopy(DEFAULT_STATE)

    state["brightness"] = clamp_number(incoming.get("brightness"), 0, 100, 80)
    state["power_on"] = bool(incoming.get("power_on", incoming.get("active_mode") != "off"))
    theme = str(incoming.get("theme") or state["theme"])
    state["theme"] = theme if theme in THEMES else state["theme"]
    state["solid_color"] = normalize_hex(incoming.get("solid_color"), state["solid_color"])
    effect = str(incoming.get("effect") or state["effect"])
    effect = {
        "Pulse": "Hardware pulse",
        "Flash": "Hardware flash",
        "Double flash": "Hardware double flash",
    }.get(effect, effect)
    state["effect"] = effect if effect in EFFECTS else state["effect"]
    state["tempo_bpm"] = clamp_number(incoming.get("tempo_bpm"), 40, 240, 120)
    division = str(incoming.get("beat_division") or state["beat_division"])
    state["beat_division"] = division if division in BEAT_DIVISIONS else state["beat_division"]
    state["animation_fps"] = clamp_number(incoming.get("animation_fps"), 2, 12, 5)
    state["restore_on_startup"] = bool(incoming.get("restore_on_startup", True))
    state["start_with_system"] = bool(incoming.get("start_with_system", False))
    active_mode = str(incoming.get("active_mode") or "theme").lower()
    state["active_mode"] = (
        active_mode if active_mode in {"theme", "solid", "effect", "music", "zones", "off"} else "theme"
    )
    last_active_mode = str(
        incoming.get("last_active_mode") or (active_mode if active_mode != "off" else "theme")
    ).lower()
    state["last_active_mode"] = (
        last_active_mode if last_active_mode in {"theme", "solid", "effect", "music", "zones"} else "theme"
    )
    geometry = str(incoming.get("window_geometry") or state["window_geometry"])
    state["window_geometry"] = (
        geometry if geometry == "auto" or re.fullmatch(r"\d+x\d+(?:[+-]\d+){0,2}", geometry) else "auto"
    )

    raw_music = incoming.get("music") if isinstance(incoming.get("music"), dict) else {}
    legacy_style = incoming.get("music_style")
    style = str(raw_music.get("style") or legacy_style or state["music"]["style"])
    style = "Spectrum" if style == "CAVA spectrum" else style
    state["music"]["style"] = style if style in MUSIC_STYLES else "Spectrum"
    for key, low, high, fallback in (
        ("sensitivity", 25, 250, 100),
        ("smoothing", 0, 95, 72),
        ("minimum_glow", 0, 30, 3),
        ("fps", 2, 12, 5),
        ("bass_gain", 25, 250, 100),
        ("mid_gain", 25, 250, 100),
        ("treble_gain", 25, 250, 100),
    ):
        state["music"][key] = clamp_number(raw_music.get(key), low, high, fallback)

    raw_zones = incoming.get("zones")
    if not isinstance(raw_zones, dict):
        raw_zones = incoming.get("sources") if isinstance(incoming.get("sources"), dict) else {}
    for key, label, default_channel, default_color in ZONES:
        zone = raw_zones.get(key) if isinstance(raw_zones.get(key), dict) else {}
        channel = str(zone.get("channel") or default_channel).lower()
        mode = str(zone.get("mode") or "fixed").lower()
        speed = str(zone.get("speed") or "normal").lower()
        state["zones"][key] = {
            "name": label,
            "channel": channel if channel in CHANNELS else default_channel,
            "mode": mode if mode in MODES else "fixed",
            "color": normalize_hex(zone.get("color"), default_color),
            "speed": speed if speed in SPEEDS else "normal",
        }
    return state
