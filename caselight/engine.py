from __future__ import annotations

import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from .audio import choose_audio_source
from .effects import effect_frame, music_frame
from .hardware import Gigabyte5711Controller, LightCommand
from .model import HARDWARE_EFFECTS, THEMES, ZONES, color_at_brightness

StatusCallback = Callable[[str, bool], None]
MeterCallback = Callable[[tuple[float, float, float]], None]


class LightingEngine:
    def __init__(
        self,
        state: dict[str, Any],
        save: Callable[[dict[str, Any]], None],
        state_directory: Any,
        status: StatusCallback,
        meter: MeterCallback,
        dispatch: Callable[[Callable[[], None]], None],
        controller: Gigabyte5711Controller | None = None,
    ) -> None:
        self.state = state
        self.save = save
        self.state_directory = state_directory
        self.status_callback = status
        self.meter_callback = meter
        self.dispatch = dispatch
        self.controller = controller or Gigabyte5711Controller()
        self.effect_stop = threading.Event()
        self.music_stop = threading.Event()
        self.timer_stop = threading.Event()
        self.effect_thread: threading.Thread | None = None
        self.music_thread: threading.Thread | None = None
        self.timer_thread: threading.Thread | None = None
        self.music_hue = 0.0
        self._music_ema = [0.0, 0.0, 0.0]
        self._hardware_lock = threading.Lock()
        self._generation_lock = threading.Lock()
        self._generation = 0
        self._shutdown = threading.Event()

    def _status(self, text: str, error: bool = False) -> None:
        self.dispatch(lambda: self.status_callback(text, error))

    def _meter(self, bands: Sequence[float]) -> None:
        values = tuple(float(value) for value in bands[:3])
        self.dispatch(lambda: self.meter_callback((values[0], values[1], values[2])))

    def _persist(self) -> None:
        self.save(self.state)

    def _next_generation(self) -> int:
        with self._generation_lock:
            self._generation += 1
            return self._generation

    def _current_generation(self) -> int:
        with self._generation_lock:
            return self._generation

    def _is_current(self, generation: int) -> bool:
        with self._generation_lock:
            return not self._shutdown.is_set() and generation == self._generation

    def _channels(self) -> tuple[str, str, str]:
        return tuple(self.state["zones"][key]["channel"] for key, _label, _channel, _color in ZONES)  # type: ignore[return-value]

    def _scaled(self, color: str, intensity: float = 1.0) -> str:
        return color_at_brightness(color, self.state["brightness"], intensity)

    def _run_async(self, action: Callable[[], str], success: str | None = None) -> None:
        def run() -> None:
            try:
                with self._hardware_lock:
                    result = action()
                self._status(success or result)
            except Exception as exc:
                self._status(str(exc), True)

        threading.Thread(target=run, name="caselight-command", daemon=True).start()

    def _apply(self, commands: Sequence[LightCommand], generation: int, success: str | None = None) -> bool:
        """Apply a current lighting frame without allowing stale frames to win."""

        if not self._is_current(generation):
            return False
        try:
            with self._hardware_lock:
                if not self._is_current(generation):
                    return False
                self.controller.apply(commands)
            if success and self._is_current(generation):
                self._status(success)
            return True
        except Exception as exc:
            if self._is_current(generation):
                self._status(str(exc), True)
            return False

    def _submit(self, commands: Sequence[LightCommand], generation: int, success: str) -> None:
        threading.Thread(
            target=self._apply,
            args=(commands, generation, success),
            name="caselight-command",
            daemon=True,
        ).start()

    def detect(self) -> None:
        self._status("Looking for the lighting controller…")
        self._run_async(self.controller.detect)

    def stop_dynamic(self) -> int:
        self.effect_stop.set()
        self.music_stop.set()
        return self._next_generation()

    def power_off(self) -> None:
        generation = self.stop_dynamic()
        if self.state.get("active_mode") != "off":
            self.state["last_active_mode"] = self.state.get("active_mode", "theme")
        self.state["power_on"] = False
        self.state["active_mode"] = "off"
        self._persist()
        self._submit([LightCommand("sync", "off")], generation, "Case lights off")

    def restore(self) -> None:
        if not self.state.get("power_on", True):
            self.power_off()
            return
        if self.state.get("active_mode") == "off":
            self.state["active_mode"] = self.state.get("last_active_mode", "theme")
        if self.state["active_mode"] == "solid":
            self.apply_solid(self.state["solid_color"])
        elif self.state["active_mode"] == "effect":
            self.start_effect()
        elif self.state["active_mode"] == "music":
            self.start_music()
        elif self.state["active_mode"] == "zones":
            self.apply_zones()
        else:
            self.apply_theme(self.state["theme"])

    def apply_theme(self, name: str) -> None:
        colors = THEMES.get(name)
        if not colors:
            return
        generation = self.stop_dynamic()
        self.state["theme"] = name
        self.state["power_on"] = True
        self.state["active_mode"] = "theme"
        self.state["last_active_mode"] = "theme"
        commands = []
        for index, (key, _label, default_channel, _default_color) in enumerate(ZONES):
            zone = self.state["zones"][key]
            zone["color"] = colors[index % len(colors)]
            zone["mode"] = "fixed"
            commands.append(LightCommand(zone.get("channel", default_channel), "fixed", self._scaled(zone["color"])))
        self._persist()
        self._submit(commands, generation, f"{name} theme applied")

    def apply_solid(self, color: str) -> None:
        generation = self.stop_dynamic()
        self.state["solid_color"] = color
        self.state["power_on"] = True
        self.state["active_mode"] = "solid"
        self.state["last_active_mode"] = "solid"
        self._persist()
        command = LightCommand("sync", "fixed", self._scaled(color))
        self._submit([command], generation, f"Solid #{color} applied")

    def apply_zones(self) -> None:
        generation = self.stop_dynamic()
        self.state["power_on"] = True
        self.state["active_mode"] = "zones"
        self.state["last_active_mode"] = "zones"
        commands = []
        for key, _label, default_channel, _default_color in ZONES:
            zone = self.state["zones"][key]
            mode = zone["mode"]
            commands.append(
                LightCommand(
                    zone.get("channel", default_channel),
                    mode,
                    self._scaled(zone["color"]),
                    zone["speed"],
                )
            )
        self._persist()
        self._submit(commands, generation, "Zone settings applied")

    def start_effect(self) -> None:
        generation = self.stop_dynamic()
        name = self.state["effect"]
        self.state["power_on"] = True
        self.state["active_mode"] = "effect"
        self.state["last_active_mode"] = "effect"
        self._persist()
        if name in HARDWARE_EFFECTS:
            mode = HARDWARE_EFFECTS[name]
            color = self.state["zones"][ZONES[0][0]]["color"]
            speed = self.state["zones"][ZONES[0][0]].get("speed", "normal")
            command = LightCommand("sync", mode, self._scaled(color), speed)
            self._submit([command], generation, f"{name} running in hardware")
            return
        stop = threading.Event()
        self.effect_stop = stop
        thread = threading.Thread(
            target=self._effect_loop,
            args=(name, stop, generation),
            name="caselight-effect",
            daemon=True,
        )
        self.effect_thread = thread
        self._status(f"{name} starting…")
        thread.start()

    def _effect_loop(self, name: str, stop: threading.Event, generation: int) -> None:
        started = time.monotonic()
        frame_count = 0
        try:
            while not stop.is_set() and self._is_current(generation):
                colors = THEMES[self.state["theme"]]
                frame = effect_frame(
                    name,
                    time.monotonic() - started,
                    colors,
                    int(self.state["tempo_bpm"]),
                    self.state["beat_division"],
                )
                commands = [
                    LightCommand(channel, "fixed", self._scaled(color, intensity))
                    for channel, (color, intensity) in zip(self._channels(), frame)
                ]
                if not self._apply(commands, generation):
                    break
                frame_count += 1
                if frame_count == 1:
                    self._status(f"{name} • {self.state['tempo_bpm']} BPM")
                fps = max(2, min(12, int(self.state["animation_fps"])))
                if stop.wait(1.0 / fps):
                    break
        except Exception as exc:
            if not stop.is_set():
                self._status(str(exc), True)

    def stop_effect(self) -> None:
        if self.state.get("active_mode") == "effect":
            self.effect_stop.set()
            self._next_generation()
            self.state["active_mode"] = "zones"
            self._persist()
        self._status("Effect stopped")

    def start_music(self) -> None:
        generation = self.stop_dynamic()
        stop = threading.Event()
        self.music_stop = stop
        self.state["power_on"] = True
        self.state["active_mode"] = "music"
        self.state["last_active_mode"] = "music"
        self._music_ema = [0.0, 0.0, 0.0]
        self._persist()
        thread = threading.Thread(
            target=self._music_loop,
            args=(stop, generation),
            name="caselight-music",
            daemon=True,
        )
        self.music_thread = thread
        self._status("Music visualizer starting…")
        thread.start()

    def _music_loop(self, stop: threading.Event, generation: int) -> None:
        try:
            source = choose_audio_source(self.state_directory)
            self._status(f"Listening through {source.name}")
            config = self.state["music"]
            for raw in source.frames(stop, int(config["fps"])):
                if stop.is_set() or not self._is_current(generation):
                    break
                config = self.state["music"]
                gains = (
                    config["bass_gain"] / 100.0,
                    config["mid_gain"] / 100.0,
                    config["treble_gain"] / 100.0,
                )
                sensitivity = config["sensitivity"] / 100.0
                decay = config["smoothing"] / 100.0
                minimum = config["minimum_glow"] / 100.0
                bands = []
                for index, value in enumerate(raw):
                    adjusted = max(0.0, min(1.0, value * sensitivity * gains[index]))
                    smoothed = max(adjusted, self._music_ema[index] * decay)
                    self._music_ema[index] = smoothed
                    bands.append(smoothed)
                frame, self.music_hue = music_frame(
                    config["style"], bands, THEMES[self.state["theme"]], self.music_hue, minimum
                )
                commands = [
                    LightCommand(channel, "fixed", self._scaled(color, intensity))
                    for channel, (color, intensity) in zip(self._channels(), frame)
                ]
                if not self._apply(commands, generation):
                    break
                if not self._is_current(generation):
                    break
                self._meter(bands)
                self._status(f"{source.name} • {round(max(bands) * 100)}% energy")
        except Exception as exc:
            if not stop.is_set():
                self._status(str(exc), True)
        finally:
            if self._is_current(generation):
                self._meter((0.0, 0.0, 0.0))

    def stop_music(self) -> None:
        if self.state.get("active_mode") == "music":
            self.music_stop.set()
            self._next_generation()
            self.state["active_mode"] = "zones"
            self._persist()
        self._meter((0.0, 0.0, 0.0))
        self._status("Music visualizer stopped")

    def start_timer(self, minutes: float, action: str) -> None:
        self.timer_stop.set()
        stop = threading.Event()
        self.timer_stop = stop

        def run() -> None:
            if stop.wait(max(0.01, minutes) * 60.0):
                return
            if action == "Turn off":
                self.power_off()
            else:
                self.restore()
            self._status(f"Timer finished • {action.lower()}")

        self.timer_thread = threading.Thread(target=run, name="caselight-timer", daemon=True)
        self.timer_thread.start()
        self._status(f"Timer set for {minutes:g} minutes")

    def cancel_timer(self) -> None:
        self.timer_stop.set()
        self._status("Timer cancelled")

    def shutdown(self) -> None:
        self.effect_stop.set()
        self.music_stop.set()
        self.timer_stop.set()
        self._shutdown.set()
        self._next_generation()
