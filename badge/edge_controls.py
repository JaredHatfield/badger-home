"""Work around unrotated edge switches in the Universe 2026 input API."""

import builtins


class EdgeControls:
    def __init__(self, device):
        self.device = device
        self.native_poll = device.poll
        self.opposites = {
            builtins.BUTTON_UP: builtins.BUTTON_DOWN,
            builtins.BUTTON_DOWN: builtins.BUTTON_UP,
            builtins.BUTTON_LEFT: builtins.BUTTON_RIGHT,
            builtins.BUTTON_RIGHT: builtins.BUTTON_LEFT,
        }
        self.previous = self.held()

    def held(self):
        device = self.device
        buttons = device.buttons.held()
        # Follow the actual display rotation, including manual rotation and
        # disabled autorotation. The touch pad is already orientation-aware.
        if device.rotate_180():
            buttons = (self.opposites.get(action, action) for action in buttons)
        return set(buttons) | set(device.pad.held())

    def poll(self):
        result = self.native_poll()
        held = self.held()
        previous = self.previous
        # Derive edges after mapping and merging. This also handles rotating
        # while holding a switch, or releasing one of two sources of an action.
        self.device.all.set_state(
            held, held - previous, previous - held, held ^ previous
        )
        self.previous = held
        return result


def install(device):
    # Keep the raw switch and touch views intact for diagnostics and apps that
    # intentionally distinguish sources. Normal badge input uses badge.all.
    if not hasattr(device, "_edge_controls"):
        device._edge_controls = EdgeControls(device)
        device.poll = device._edge_controls.poll
