"""Host-side checks of the 2026 runtime input workaround; no hardware needed."""

import builtins
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


PATH = Path(__file__).resolve().parents[1] / "badge" / "edge_controls.py"
SPEC = importlib.util.spec_from_file_location("edge_controls", PATH)
edge_controls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(edge_controls)


class Controls:
    def __init__(self):
        self.set_state(set(), set(), set(), set())

    def set_state(self, held, pressed, released, changed):
        self.states = tuple(set(group) for group in (held, pressed, released, changed))

    def held(self):
        return self.states[0]


class EdgeControlsTests(unittest.TestCase):
    def setUp(self):
        constants = {"BUTTON_" + name: name for name in
                     ("UP", "DOWN", "LEFT", "RIGHT")}
        self.constants = patch.multiple(builtins, create=True, **constants)
        self.constants.start()
        self.addCleanup(self.constants.stop)
        self.rotated = False
        self.physical = set()
        self.touch = set()
        self.polls = 0
        self.device = SimpleNamespace(
            buttons=Controls(), pad=Controls(), all=Controls(),
            rotate_180=lambda: self.rotated, poll=self.native_poll,
        )
        edge_controls.install(self.device)

    def native_poll(self):
        self.polls += 1
        self.device.buttons.set_state(self.physical, (), (), ())
        self.device.pad.set_state(self.touch, (), (), ())
        # The native runtime overwrites the combined state each poll.
        self.device.all.set_state(self.physical | self.touch, (), (), ())
        return "polled"

    def test_switch_directions_in_both_display_rotations(self):
        for rotated in (False, True):
            self.rotated = rotated
            for action, opposite in (("UP", "DOWN"), ("DOWN", "UP"),
                                     ("LEFT", "RIGHT"), ("RIGHT", "LEFT")):
                self.physical = {action}
                self.device.poll()
                self.assertEqual(self.device.all.held(), {opposite if rotated else action})
                self.assertEqual(self.device.buttons.held(), {action})

    def test_touch_and_non_directional_actions_are_preserved(self):
        self.rotated = True
        self.physical = {"SELECT", "HOME"}
        self.touch = {"LEFT", "UP", "BACK", "MENU"}
        self.device.poll()
        self.assertEqual(self.device.all.held(), self.physical | self.touch)
        self.assertEqual(self.device.pad.held(), self.touch)

    def test_press_hold_release(self):
        self.rotated = True
        self.physical = {"UP"}
        self.assertEqual(self.device.poll(), "polled")
        self.assertEqual(self.device.all.states, ({"DOWN"}, {"DOWN"}, set(), {"DOWN"}))
        self.device.poll()
        self.assertEqual(self.device.all.states, ({"DOWN"}, set(), set(), set()))
        self.physical = set()
        self.device.poll()
        self.assertEqual(self.device.all.states, (set(), set(), {"DOWN"}, {"DOWN"}))

    def test_rotating_held_switch_releases_old_direction(self):
        self.physical = {"LEFT"}
        self.device.poll()
        self.rotated = True
        self.device.poll()
        self.assertEqual(self.device.all.states,
                         ({"RIGHT"}, {"RIGHT"}, {"LEFT"}, {"LEFT", "RIGHT"}))
        self.rotated = False
        self.device.poll()
        self.assertEqual(self.device.all.states,
                         ({"LEFT"}, {"LEFT"}, {"RIGHT"}, {"LEFT", "RIGHT"}))

    def test_overlapping_sources_do_not_release_held_action(self):
        self.rotated = True
        self.physical = {"UP"}
        self.touch = {"DOWN"}
        self.device.poll()
        self.physical = set()
        self.device.poll()
        self.assertEqual(self.device.all.states, ({"DOWN"}, set(), set(), set()))
        self.touch = set()
        self.device.poll()
        self.assertEqual(self.device.all.states, (set(), set(), {"DOWN"}, {"DOWN"}))

    def test_install_is_idempotent(self):
        poll = self.device.poll
        edge_controls.install(self.device)
        self.assertIs(self.device.poll, poll)
        self.device.poll()
        self.assertEqual(self.polls, 1)


if __name__ == "__main__":
    unittest.main()
