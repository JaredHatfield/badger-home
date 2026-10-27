# Rotated edge-switch workaround

Proposed fix for [badger/home#134](https://github.com/badger/home/issues/134).
The reported behavior is that the display and capacitive gaming controls
rotate correctly, while the four directional edge switches keep their upright
directions.

`badge/main.py` installs `badge/edge_controls.py` before launching any app.
After each native `badge.poll()`, the workaround swaps Up/Down and Left/Right
from `badge.buttons.held()` when `badge.rotate_180()` is true. It merges those
actions with the already-mapped `badge.pad.held()` and updates `badge.all`.
The combined input's pressed, released, and changed events are derived from
successive held states, so rotating a held switch releases the old direction
and presses the new one. Releasing a switch does not release an action still
held on the touch pad. Select, Home, Back, and Menu keep their existing actions.

This targets normal `badge.held()`, `pressed()`, `released()`, `changed()`, and
`direction()` consumers of the combined controls. The separate `badge.buttons`
and `badge.pad` views remain unchanged for diagnostics and apps that explicitly
distinguish the two sources. Display rotation is used rather than physical
orientation so disabling autorotation or manually rotating remains consistent.

The custom 2026 firmware implementation is not included in this repository.
The workaround uses its separate controls and `set_state()` interface, already
used by `badge/apps/merge_conflict/replay.py`. It assumes that the firmware's
normal input methods read `badge.all`, and that the switch view is unrotated,
as reported. Remove the workaround when firmware maps the switches itself;
otherwise the directions would be swapped twice.

## Validation

Run the host checks with:

```bash
python -m unittest discover -s tests -p 'test_edge_controls.py' -v
```

These checks use a runtime double and do not verify the firmware or hardware.
The stock simulator uses a compatibility layer for the custom 2026 inputs, so
it cannot establish that the workaround fixes the physical device.

Hardware verification remains outstanding:

1. Install both `main.py` and `edge_controls.py` in `/system` using the
   [USB mass-storage workflow](USB_SERIAL.md), then reboot normally.
2. In the launcher and Input Test app, check all four edge-switch directions
   upright and inverted. Input Test's PHYSICAL indicators intentionally show
   raw switches; use its direction dial to check the combined logical input.
3. Check the touch D-pad and Select, Back, Menu, and Home in both orientations.
4. Hold an edge switch while rotating, then release it. Confirm that the old
   direction does not stick. Hold the equivalent logical touch direction and
   switch together, then release each source separately.
5. With an app that controls autorotation, verify manual display rotation and
   disabled autorotation, then return to the launcher and check input again.
