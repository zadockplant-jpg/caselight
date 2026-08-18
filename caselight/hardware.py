from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .model import CHANNELS, MODES, MODES_WITH_COLOR, SPEEDS, normalize_hex

VENDOR_ID = 0x048D
PRODUCT_ID = 0x5711
DEVICE_DESCRIPTION = "Gigabyte RGB Fusion 2.0 5711 Controller"
MATCH = (VENDOR_ID, PRODUCT_ID, DEVICE_DESCRIPTION, {})
MAX_BATCH_COMMANDS = 32


class ControllerError(RuntimeError):
    pass


@dataclass(frozen=True)
class LightCommand:
    channel: str
    mode: str
    color: str = "00E5FF"
    speed: str = "normal"

    def validated(self) -> LightCommand:
        channel = self.channel.lower()
        mode = self.mode.lower()
        speed = self.speed.lower()
        if channel not in CHANNELS:
            raise ValueError(f"Unknown channel: {channel}")
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        if speed not in SPEEDS:
            raise ValueError(f"Unknown speed: {speed}")
        return LightCommand(channel, mode, normalize_hex(self.color), speed)


class Gigabyte5711Controller:
    """Thread-safe adapter around liquidctl's RGB Fusion 2 driver."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    @staticmethod
    def _driver() -> Any:
        try:
            from liquidctl.driver.rgb_fusion2 import RgbFusion2
        except ImportError as exc:
            raise ControllerError("liquidctl is not installed. Install CaseLight dependencies first.") from exc
        if MATCH not in RgbFusion2._MATCHES:
            RgbFusion2._MATCHES.append(MATCH)
        return RgbFusion2

    def _devices(self) -> Iterable[Any]:
        return self._driver().find_supported_devices()

    def detect(self) -> str:
        failures: list[str] = []
        found = False
        for device in self._devices():
            found = True
            try:
                with device.connect():
                    info = device.initialize()
                details = ", ".join(f"{name}: {value}{unit}" for name, value, unit in info)
                return f"{device.description} • {details or 'ready'}"
            except Exception as exc:
                failures.append(f"{type(exc).__name__}: {exc}")
        if not found:
            raise ControllerError(f"No {DEVICE_DESCRIPTION} HID interface was found.")
        raise ControllerError("Controller found but unavailable: " + "; ".join(failures))

    def apply(self, commands: Iterable[LightCommand]) -> str:
        validated = [command.validated() for command in commands]
        if not 1 <= len(validated) <= MAX_BATCH_COMMANDS:
            raise ValueError(f"A batch must contain 1 to {MAX_BATCH_COMMANDS} commands")
        with self._lock:
            failures: list[str] = []
            for device in self._devices():
                try:
                    with device.connect():
                        device.initialize()
                        for command in validated:
                            colors = []
                            if command.mode in MODES_WITH_COLOR:
                                colors = [[int(command.color[index : index + 2], 16) for index in (0, 2, 4)]]
                            device.set_color(command.channel, command.mode, colors, speed=command.speed)
                    return f"Updated {len(validated)} lighting zone{'s' if len(validated) != 1 else ''}."
                except Exception as exc:
                    failures.append(f"{type(exc).__name__}: {exc}")
            if failures:
                raise ControllerError("Controller update failed: " + "; ".join(failures))
            raise ControllerError(f"No {DEVICE_DESCRIPTION} HID interface was found.")
