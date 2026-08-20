from __future__ import annotations

import threading
import time
import unittest

from caselight.engine import LightingEngine
from caselight.model import DEFAULT_STATE, normalize_state


class RecordingController:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.first_started = threading.Event()
        self.release_first = threading.Event()

    def apply(self, commands) -> str:
        color = commands[0].color
        self.calls.append(color)
        if len(self.calls) == 1:
            self.first_started.set()
            self.release_first.wait(2.0)
        return "updated"


class EngineTests(unittest.TestCase):
    def test_latest_color_wins_over_an_in_flight_previous_update(self) -> None:
        controller = RecordingController()
        state = normalize_state(DEFAULT_STATE)
        state["brightness"] = 100
        engine = LightingEngine(
            state,
            lambda _state: None,
            ".",
            lambda _text, _error=False: None,
            lambda _bands: None,
            lambda callback: callback(),
            controller=controller,
        )

        engine.apply_solid("FF0000")
        self.assertTrue(controller.first_started.wait(1.0))
        engine.apply_solid("0000FF")
        controller.release_first.set()

        deadline = time.monotonic() + 2.0
        while len(controller.calls) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)

        self.assertEqual(controller.calls[-1], "0000FF")
        engine.shutdown()


if __name__ == "__main__":
    unittest.main()
