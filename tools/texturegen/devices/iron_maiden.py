"""Iron Maiden — hand-authored model, atlas art, and animations.

The upright coffin: a riveted shell with two swinging doors, an inner
screaming plate, a bed of nails that extends when the cycle starts, and a
soul ember that flares while the device works.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    IRON_BLACK,
    RUST,
    SOUL,
    SOUL_LIGHT,
    SOUL_PALE,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    flat,
    soul_glow,
    spike as spike_art,
    steel_face,
    steel_plate,
)
from model import Face, Model
from pipeline import DeviceArt

# Timings mirrored from behavior_pack/scripts/config.js (20 ticks = 1 second).
CAPTURE_DELAY = 1.0
CLOSE_DURATION = 1.5
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 3.0
RELEASE_TIME = 1.0
BROKEN_TIME = 1.5


def face(paint, **kwargs) -> Face:
    return Face(paint=paint, **kwargs)


def flat_face(color, key: str) -> Face:
    """A shared 1x1 flat patch: costs a single texel no matter how often it is used."""
    return Face(paint=flat(color), size=(1, 1), share=f"flat:{key}")


IRON_FLAT = lambda: flat_face(IRON_BLACK, "iron_black")  # noqa: E731
STEEL_FLAT = lambda: flat_face(STEEL_DARK, "steel_dark")  # noqa: E731


def door_outer(painter) -> None:
    """Riveted door leaf with a carved brow, an empty socket, and an ember rune.

    Painted once and mirrored onto the second door with ``flip_u``: the left
    edge of the patch is the seam between the two doors.
    """
    steel_plate(STEEL, rivets=False, grime=0.3, scratches=3, rust=0.4)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.outline(STEEL_DARK, inset=0)
    painter.outline(_lighten(STEEL_LIGHT), inset=1)
    for column in (2, width - 3):
        if 0 <= column < width:
            for row in range(3, height - 3, 4):
                painter.px(column, row, STEEL_HIGHLIGHT)
                painter.px(column, row + 1, STEEL_DARK)
    brow_row = max(2, height // 3)
    eye_row = brow_row + 2
    # Brow ridge sweeping in from the seam.
    painter.box(0, brow_row, width, 1, _darken(STEEL_DARK, 0.2))
    painter.box(2, brow_row + 1, max(1, width - 4), 1, _darken(STEEL_DARK, 0.05))
    # Empty socket: the lid is welded shut; only a shadow looks back.
    painter.box(3, eye_row, max(1, width - 6), max(2, height // 8), _darken(IRON_BLACK, 0.3))
    painter.px(3, eye_row + max(2, height // 8) - 1, _lighten(STEEL))
    painter.px(max(0, width - 4), eye_row + 1, SOUL_LIGHT)
    # Nose bridge along the seam.
    painter.vline(0, brow_row + 1, max(2, height // 4), _darken(STEEL_LIGHT, 0.05))
    painter.vline(min(width - 1, 1), brow_row + 2, max(2, height // 5), STEEL_DARK)
    # Mouth grille across the lower third.
    mouth_row = height - max(3, height // 4)
    painter.box(0, mouth_row, width, 1, _darken(STEEL_DARK, 0.25))
    grille_height = max(2, height // 6)
    for column in range(0, width, 2):
        painter.box(column, mouth_row, 1, grille_height, _lighten(IRON_BLACK))
    painter.box(0, mouth_row + grille_height, width, 1, _darken(STEEL_DARK, 0.25))
    # Ember rune by the latch, the only light on the door.
    rune_column = max(0, width - 3)
    rune_row = height // 2 - 3
    for offset, row in ((0, 0), (1, 1), (0, 2), (1, 3)):
        painter.px(min(width - 1, rune_column + offset), rune_row + row, SOUL_LIGHT)
    painter.px(min(width - 1, rune_column), rune_row + 2, SOUL_PALE)
    painter.bevel(STEEL_LIGHT, STEEL_DARK, alpha=140)


def door_inner(painter) -> None:
    """Dark inner face of a door: grooves, blood, and nail points."""
    painter.gradient_v(_darken(STEEL_DARK, 0.06), _darken(IRON_BLACK, 0.1))
    painter.noise(STEEL_DARK, [RUST, IRON_BLACK], density=0.3)
    width, height = painter.rect.width, painter.rect.height
    for row in range(0, height, 3):
        painter.hline(0, row, width, _lighten(IRON_BLACK, 0.05))
    # Nails pointing at the captive.
    for column in range(1, width - 1, 2):
        for row in range(2, height - 2, 5):
            painter.px(column, row, STEEL_LIGHT)
            painter.px(column, row + 1, _lighten(STEEL_DARK, 0.15))
    for _ in range(3):
        column = painter.rng.between(0, max(0, width - 1))
        top = painter.rng.between(0, max(0, height - 4))
        for row in range(top, min(height, top + painter.rng.between(2, 5))):
            painter.px(column, row, (92, 26, 24, painter.rng.between(70, 150)))
    painter.bevel(STEEL, IRON_BLACK, alpha=90)


def _lighten(color, amount: float = 0.18):
    return tuple(min(255, round(color[index] + (255 - color[index]) * amount)) for index in range(3)) + (color[3],)


def _darken(color, amount: float = 0.2):
    return tuple(max(0, round(color[index] * (1 - amount))) for index in range(3)) + (color[3],)


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_iron_maiden",
        texture_width=64,
        texture_height=128,
        visible_bounds=(1.6, 2.2),
        visible_offset=(0.0, 1.1, 0.0),
    )

    # ---------------------------------------------------------------- base --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-6, 0, -6], [12, 2, 12],
        {
            "up": face(steel_plate(STEEL, rivets=True, grime=0.15)),
            "north": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3, rust=0.5)),
            "south": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3, rust=0.5), share="base_side"),
            "east": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3, rust=0.5), share="base_side"),
            "west": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3, rust=0.5), share="base_side"),
            "down": IRON_FLAT(),
        },
    )

    # ---------------------------------------------------------------- body --
    body = model.bone("body", [0, 2, 0], parent="base")
    body.cube(
        [-6, 2, 4], [12, 21, 2],
        {
            "north": face(steel_plate(STEEL_DARK, rivets=False, grime=0.35, bands=3)),
            "south": face(steel_plate(STEEL, rivets=True, grime=0.25, rust=0.3)),
            "east": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3), share="wall_edge"),
            "west": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3), share="wall_edge"),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )
    body.cube(
        [-6, 2, -3], [2, 21, 7],
        {
            "north": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3), share="wall_edge"),
            "south": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3), share="wall_edge"),
            "east": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3, bands=2), share="wall_inner"),
            "west": face(steel_plate(STEEL, rivets=True, grime=0.25, rust=0.35)),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )
    body.cube(
        [4, 2, -3], [2, 21, 7],
        {
            "north": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3), share="wall_edge"),
            "south": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3), share="wall_edge"),
            "east": face(steel_plate(STEEL, rivets=True, grime=0.25, rust=0.35)),
            "west": face(steel_plate(STEEL_DARK, rivets=False, grime=0.3, bands=2), share="wall_inner"),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )
    # The plate behind the captive: the maiden's real face.
    body.cube(
        [-4, 6, 1], [8, 13, 1],
        {
            "north": face(steel_face(STEEL, eye_glow=SOUL_LIGHT)),
            "south": IRON_FLAT(),
            "east": IRON_FLAT(),
            "west": IRON_FLAT(),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )

    # -------------------------------------------------------------- spikes --
    spikes = model.bone("spikes", [0, 2, 1], parent="body")
    for column in (-4, -2, 0, 2):
        for row in (7, 13, 17):
            spikes.cube(
                [column, row, -2], [1, 1, 3],
                {
                    "north": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="spike"),
                    "south": IRON_FLAT(),
                    "east": IRON_FLAT(),
                    "west": IRON_FLAT(),
                    "up": IRON_FLAT(),
                    "down": IRON_FLAT(),
                },
            )

    # ------------------------------------------------------------ lid/top --
    top = model.bone("top", [0, 23, 0], parent="body")
    top.cube(
        [-6, 23, -6], [12, 2, 12],
        {
            "up": face(steel_plate(STEEL, rivets=True, grime=0.2, rust=0.3)),
            "north": face(steel_plate(STEEL, rivets=True, grime=0.2, rust=0.3), share="lid_side"),
            "south": face(steel_plate(STEEL, rivets=True, grime=0.2, rust=0.3), share="lid_side"),
            "east": face(steel_plate(STEEL, rivets=True, grime=0.2, rust=0.3), share="lid_side"),
            "west": face(steel_plate(STEEL, rivets=True, grime=0.2, rust=0.3), share="lid_side"),
            "down": IRON_FLAT(),
        },
    )
    crown = model.bone("crown", [0, 25, 0], parent="top")
    crown.cube(
        [-1, 25, -1], [2, 4, 2],
        {
            "north": face(spike_art(STEEL, light=STEEL_HIGHLIGHT)),
            "south": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="crown_spike"),
            "east": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="crown_spike"),
            "west": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="crown_spike"),
            "up": face(spike_art(STEEL_HIGHLIGHT, light=(230, 236, 245, 255))),
            "down": IRON_FLAT(),
        },
    )

    # --------------------------------------------------------------- doors --
    left = model.bone("door_left", [-6, 2, -5], parent="body")
    left.cube(
        [-6, 2, -5], [6, 22, 2],
        {
            "north": face(door_outer),
            "south": face(door_inner),
            "east": face(steel_plate(STEEL_DARK, rivets=True, grime=0.35), share="door_edge"),
            "west": face(steel_plate(STEEL_DARK, rivets=True, grime=0.35), share="door_edge"),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )
    for row in (4, 18):
        left.cube(
            [-6, row, -6], [2, 3, 1],
            {
                "north": face(steel_plate(STEEL, rivets=True, grime=0.2)),
                "south": IRON_FLAT(),
                "east": IRON_FLAT(),
                "west": IRON_FLAT(),
                "up": STEEL_FLAT(),
                "down": IRON_FLAT(),
            },
        )
    left.cube(
        [-1, 10, -6], [1, 3, 1],
        {
            "north": face(steel_plate(STEEL_LIGHT, rivets=False, grime=0.15)),
            "south": IRON_FLAT(),
            "east": IRON_FLAT(),
            "west": IRON_FLAT(),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )

    right = model.bone("door_right", [6, 2, -5], parent="body")
    right.cube(
        [0, 2, -5], [6, 22, 2],
        {
            "north": face(door_outer, flip_u=True),
            "south": face(door_inner, flip_u=True),
            "east": face(steel_plate(STEEL_DARK, rivets=True, grime=0.35), share="door_edge"),
            "west": face(steel_plate(STEEL_DARK, rivets=True, grime=0.35), share="door_edge"),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )
    for row in (4, 18):
        right.cube(
            [4, row, -6], [2, 3, 1],
            {
                "north": face(steel_plate(STEEL, rivets=True, grime=0.2), flip_u=True),
                "south": IRON_FLAT(),
                "east": IRON_FLAT(),
                "west": IRON_FLAT(),
                "up": STEEL_FLAT(),
                "down": IRON_FLAT(),
            },
        )
    right.cube(
        [0, 10, -6], [1, 3, 1],
        {
            "north": face(steel_plate(STEEL_LIGHT, rivets=False, grime=0.15), flip_u=True),
            "south": IRON_FLAT(),
            "east": IRON_FLAT(),
            "west": IRON_FLAT(),
            "up": STEEL_FLAT(),
            "down": IRON_FLAT(),
        },
    )

    # --------------------------------------------------------------- ember --
    ember = model.bone("ember", [0, 21, 1], parent="body")
    ember.cube(
        [-1, 18, 0], [2, 2, 2],
        {
            "north": face(soul_glow(SOUL)),
            "south": face(soul_glow(SOUL), share="ember_back"),
            "east": face(soul_glow(SOUL), share="ember_back"),
            "west": face(soul_glow(SOUL), share="ember_back"),
            "up": face(soul_glow(SOUL_PALE, light=SOUL_PALE, pale=(255, 255, 255, 255))),
            "down": face(soul_glow(SOUL, light=SOUL, pale=SOUL_LIGHT), share="ember_down"),
        },
    )

    animations = _animations()
    art = DeviceArt(
        slug="iron_maiden",
        display_name="Iron Maiden",
        model=model,
        animations=animations,
        state_animations={
        "idle": ["idle"],
        "detecting": ["detect"],
        "capturing": ["close"],
        "closed": ["closed"],
        "torturing": ["torture"],
        "opening": ["open"],
        "released": ["released"],
        "broken": ["broken"],
        "closed_strain": ["strain"],
        "torture_strain": ["strain"],
        },
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:basic_flame_particle",
        strain={"closed": ("closed_strain", 0.6), "torturing": ("torture_strain", 0.6)},
    )
    return art


def _animations() -> list[Animation]:
    animations: list[Animation] = []

    # Idle: closed, breathing metal, ember hidden.
    idle = Animation("animation.cc_iron_maiden.idle", 4.0, loop=True)
    idle.key("door_left", "rotation", 0.0, (0, 0, 0))
    idle.key("door_left", "rotation", 2.0, (0, 1.2, 0))
    idle.key("door_left", "rotation", 4.0, (0, 0, 0))
    idle.key("door_right", "rotation", 0.0, (0, 0, 0))
    idle.key("door_right", "rotation", 2.0, (0, -1.2, 0))
    idle.key("door_right", "rotation", 4.0, (0, 0, 0))
    idle.key("body", "position", 0.0, (0, 0, 0))
    idle.key("body", "position", 2.0, (0, 0.1, 0))
    idle.key("body", "position", 4.0, (0, 0, 0))
    idle.key("crown", "rotation", 0.0, (0, 0, 0))
    idle.key("crown", "rotation", 2.0, (1.5, 0, 0))
    idle.key("crown", "rotation", 4.0, (0, 0, 0))
    idle.key("spikes", "scale", 0.0, (1, 1, 0.18))
    idle.key("spikes", "scale", 4.0, (1, 1, 0.18))
    idle.key("ember", "scale", 0.0, (0, 0, 0))
    idle.key("ember", "scale", 4.0, (0, 0, 0))
    animations.append(idle)

    # Detecting: the doors creak open and the ember kindles.
    detect = Animation("animation.cc_iron_maiden.detect", CAPTURE_DELAY, loop=True)
    detect.key("door_left", "rotation", 0.0, (0, 0, 0))
    detect.key("door_left", "rotation", 0.5, (0, -34, 0))
    detect.key("door_left", "rotation", 1.0, (0, -29, 0))
    detect.key("door_right", "rotation", 0.0, (0, 0, 0))
    detect.key("door_right", "rotation", 0.5, (0, 34, 0))
    detect.key("door_right", "rotation", 1.0, (0, 29, 0))
    detect.key("body", "rotation", 0.0, (0, 0, 0))
    detect.key("body", "rotation", 0.6, (-2.5, 0, 0))
    detect.key("body", "rotation", 1.0, (-2, 0, 0))
    detect.key("spikes", "scale", 0.0, (1, 1, 0.18))
    detect.key("spikes", "scale", 1.0, (1, 1, 0.3))
    detect.key("ember", "scale", 0.0, (0, 0, 0))
    detect.key("ember", "scale", 0.5, (0.5, 0.5, 0.5))
    detect.key("ember", "scale", 1.0, (0.75, 0.75, 0.75))
    detect.key("ember", "position", 0.0, (0, 0, 0))
    detect.key("ember", "position", 0.5, (0, -0.4, 0))
    detect.key("ember", "position", 1.0, (0, -0.7, 0))
    animations.append(detect)

    # Close: slam with overshoot, latch, spikes fire.
    close = Animation("animation.cc_iron_maiden.close", CLOSE_DURATION, loop=False)
    close.key("door_left", "rotation", 0.0, (0, -29, 0))
    close.key("door_left", "rotation", 0.55, (0, 4, 0))
    close.key("door_left", "rotation", 0.75, (0, -2.5, 0))
    close.key("door_left", "rotation", 1.0, (0, 0, 0))
    close.key("door_left", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("door_right", "rotation", 0.0, (0, 29, 0))
    close.key("door_right", "rotation", 0.55, (0, -4, 0))
    close.key("door_right", "rotation", 0.75, (0, 2.5, 0))
    close.key("door_right", "rotation", 1.0, (0, 0, 0))
    close.key("door_right", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("body", "rotation", 0.0, (-2, 0, 0))
    close.key("body", "rotation", 0.55, (1.5, 0, 0))
    close.key("body", "rotation", 1.0, (0, 0, 0))
    close.key("body", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("spikes", "scale", 0.0, (1, 1, 0.3))
    close.key("spikes", "scale", 0.6, (1, 1, 1.05))
    close.key("spikes", "scale", 1.0, (1, 1, 1))
    close.key("spikes", "scale", CLOSE_DURATION, (1, 1, 1))
    close.key("ember", "scale", 0.0, (0.75, 0.75, 0.75))
    close.key("ember", "scale", 0.4, (1.35, 1.35, 1.35))
    close.key("ember", "scale", 0.9, (0, 0, 0))
    close.key("ember", "scale", CLOSE_DURATION, (0, 0, 0))
    animations.append(close)

    # Closed: the pause before the first turn of the screw.
    closed = Animation("animation.cc_iron_maiden.closed", CLOSED_PAUSE, loop=True)
    closed.key("door_left", "rotation", 0.0, (0, 0, 0))
    closed.key("door_left", "rotation", 0.25, (0, 0.8, 0))
    closed.key("door_left", "rotation", 0.5, (0, 0, 0))
    closed.key("door_right", "rotation", 0.0, (0, 0, 0))
    closed.key("door_right", "rotation", 0.25, (0, -0.8, 0))
    closed.key("door_right", "rotation", 0.5, (0, 0, 0))
    closed.key("spikes", "scale", 0.0, (1, 1, 1))
    closed.key("spikes", "scale", 0.5, (1, 1, 1))
    closed.key("ember", "scale", 0.0, (0, 0, 0))
    closed.key("ember", "scale", 0.5, (0, 0, 0))
    animations.append(closed)

    # Torture: the shell shudders, the ember pulses, nails grind.
    torture = Animation("animation.cc_iron_maiden.torture", TORTURE_INTERVAL, loop=True)
    for time, angle in ((0.0, 0), (0.3, 1.6), (0.6, -1.4), (0.9, 1.2), (1.2, -0.8), (1.5, 0), (3.0, 0)):
        torture.key("body", "rotation", time, (0, 0, angle))
    torture.key("body", "position", 0.0, (0, 0, 0))
    torture.key("body", "position", 0.4, (0.3, 0, 0))
    torture.key("body", "position", 0.8, (-0.3, 0, 0))
    torture.key("body", "position", 1.2, (0, 0, 0))
    torture.key("body", "position", 3.0, (0, 0, 0))
    torture.key("door_left", "rotation", 0.0, (0, 0, 0))
    torture.key("door_left", "rotation", 0.5, (0, -2.6, 0))
    torture.key("door_left", "rotation", 1.0, (0, 0.6, 0))
    torture.key("door_left", "rotation", 1.6, (0, 0, 0))
    torture.key("door_left", "rotation", 3.0, (0, 0, 0))
    torture.key("door_right", "rotation", 0.0, (0, 0, 0))
    torture.key("door_right", "rotation", 0.5, (0, 2.6, 0))
    torture.key("door_right", "rotation", 1.0, (0, -0.6, 0))
    torture.key("door_right", "rotation", 1.6, (0, 0, 0))
    torture.key("door_right", "rotation", 3.0, (0, 0, 0))
    torture.key("spikes", "scale", 0.0, (1, 1, 0.55))
    torture.key("spikes", "scale", 0.6, (1, 1, 1))
    torture.key("spikes", "scale", 1.8, (1, 1, 1))
    torture.key("spikes", "scale", 2.4, (1, 1, 0.55))
    torture.key("spikes", "scale", 3.0, (1, 1, 0.55))
    torture.key("ember", "scale", 0.0, (0.55, 0.55, 0.55))
    torture.key("ember", "scale", 1.5, (0.95, 0.95, 0.95))
    torture.key("ember", "scale", 3.0, (0.55, 0.55, 0.55))
    torture.key("ember", "position", 0.0, (0, 0, 0))
    torture.key("ember", "position", 1.5, (0, 0.8, 0))
    torture.key("ember", "position", 3.0, (0, 0, 0))
    torture.key("ember", "rotation", 0.0, (0, 0, -7))
    torture.key("ember", "rotation", 1.5, (0, 0, 9))
    torture.key("ember", "rotation", 3.0, (0, 0, -7))
    torture.key("crown", "rotation", 0.0, (0, 0, 0))
    torture.key("crown", "rotation", 0.4, (3, 0, 2))
    torture.key("crown", "rotation", 1.2, (-2, 0, -3))
    torture.key("crown", "rotation", 3.0, (0, 0, 0))
    animations.append(torture)

    # Strain: a short rattle layered on the occupied states.
    strain = Animation("animation.cc_iron_maiden.strain", 0.6, loop=False)
    for time, angle in ((0.0, 0), (0.08, 4.5), (0.16, -4), (0.24, 3.5), (0.32, -3), (0.4, 2), (0.5, -1), (0.6, 0)):
        strain.key("body", "rotation", time, (0, 0, angle))
    strain.key("body", "position", 0.0, (0, 0, 0))
    strain.key("body", "position", 0.08, (0.7, 0, 0))
    strain.key("body", "position", 0.16, (-0.7, 0, 0))
    strain.key("body", "position", 0.3, (0.4, 0, 0))
    strain.key("body", "position", 0.6, (0, 0, 0))
    strain.key("door_left", "rotation", 0.0, (0, 0, 0))
    strain.key("door_left", "rotation", 0.1, (0, -3.4, 0))
    strain.key("door_left", "rotation", 0.24, (0, 1.6, 0))
    strain.key("door_left", "rotation", 0.42, (0, 0, 0))
    strain.key("door_left", "rotation", 0.6, (0, 0, 0))
    strain.key("door_right", "rotation", 0.0, (0, 0, 0))
    strain.key("door_right", "rotation", 0.1, (0, 3.4, 0))
    strain.key("door_right", "rotation", 0.24, (0, -1.6, 0))
    strain.key("door_right", "rotation", 0.42, (0, 0, 0))
    strain.key("door_right", "rotation", 0.6, (0, 0, 0))
    strain.key("spikes", "scale", 0.0, (1, 1, 0.75))
    strain.key("spikes", "scale", 0.2, (1, 1, 1))
    strain.key("spikes", "scale", 0.6, (1, 1, 0.75))
    animations.append(strain)

    # Open: doors swing wide to free the captive.
    open_animation = Animation("animation.cc_iron_maiden.open", RELEASE_TIME + 0.5, loop=False)
    open_animation.key("door_left", "rotation", 0.0, (0, 0, 0))
    open_animation.key("door_left", "rotation", 0.35, (0, 52, 0))
    open_animation.key("door_left", "rotation", 0.6, (0, 97, 0))
    open_animation.key("door_left", "rotation", 0.9, (0, 88, 0))
    open_animation.key("door_left", "rotation", RELEASE_TIME + 0.5, (0, 92, 0))
    open_animation.key("door_right", "rotation", 0.0, (0, 0, 0))
    open_animation.key("door_right", "rotation", 0.35, (0, -52, 0))
    open_animation.key("door_right", "rotation", 0.6, (0, -97, 0))
    open_animation.key("door_right", "rotation", 0.9, (0, -88, 0))
    open_animation.key("door_right", "rotation", RELEASE_TIME + 0.5, (0, -92, 0))
    open_animation.key("body", "rotation", 0.0, (0, 0, 0))
    open_animation.key("body", "rotation", 0.5, (1.6, 0, 0))
    open_animation.key("body", "rotation", RELEASE_TIME + 0.5, (0, 0, 0))
    open_animation.key("spikes", "scale", 0.0, (1, 1, 0.55))
    open_animation.key("spikes", "scale", 0.5, (1, 1, 0.2))
    open_animation.key("spikes", "scale", RELEASE_TIME + 0.5, (1, 1, 0.18))
    open_animation.key("ember", "scale", 0.0, (0.55, 0.55, 0.55))
    open_animation.key("ember", "scale", 0.6, (0, 0, 0))
    open_animation.key("ember", "scale", RELEASE_TIME + 0.5, (0, 0, 0))
    animations.append(open_animation)

    # Released: settled bounce, doors come to rest.
    released = Animation("animation.cc_iron_maiden.released", RELEASE_TIME, loop=False)
    released.key("door_left", "rotation", 0.0, (0, 92, 0))
    released.key("door_left", "rotation", 0.4, (0, 86, 0))
    released.key("door_left", "rotation", 0.75, (0, 94, 0))
    released.key("door_left", "rotation", RELEASE_TIME, (0, 92, 0))
    released.key("door_right", "rotation", 0.0, (0, -92, 0))
    released.key("door_right", "rotation", 0.4, (0, -86, 0))
    released.key("door_right", "rotation", 0.75, (0, -94, 0))
    released.key("door_right", "rotation", RELEASE_TIME, (0, -92, 0))
    released.key("spikes", "scale", 0.0, (1, 1, 0.18))
    released.key("spikes", "scale", RELEASE_TIME, (1, 1, 0.18))
    released.key("ember", "scale", 0.0, (0, 0, 0))
    released.key("ember", "scale", RELEASE_TIME, (0, 0, 0))
    animations.append(released)

    # Broken: doors hang crooked, the crown falls, the shell tips back.
    broken = Animation("animation.cc_iron_maiden.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("body", "rotation", 0.0, (0, 0, 0))
    broken.key("body", "rotation", 0.7, (-4, 0, 3))
    broken.key("body", "rotation", 1.2, (-6, 0, 2))
    broken.key("body", "rotation", BROKEN_TIME, (-6, 0, 2))
    broken.key("body", "position", 0.0, (0, 0, 0))
    broken.key("body", "position", 1.2, (0, -1, 0.5))
    broken.key("body", "position", BROKEN_TIME, (0, -1, 0.5))
    broken.key("door_left", "rotation", 0.0, (0, 0, 0))
    broken.key("door_left", "rotation", 0.8, (0, 64, 0))
    broken.key("door_left", "rotation", BROKEN_TIME, (0, 47, 0))
    broken.key("door_right", "rotation", 0.0, (0, 0, 0))
    broken.key("door_right", "rotation", 0.8, (0, -58, 0))
    broken.key("door_right", "rotation", BROKEN_TIME, (0, -70, 0))
    broken.key("top", "rotation", 0.0, (0, 0, 0))
    broken.key("top", "rotation", 0.9, (2, 0, -5))
    broken.key("top", "rotation", BROKEN_TIME, (3, 0, -4))
    broken.key("crown", "position", 0.0, (0, 0, 0))
    broken.key("crown", "position", 1.0, (0, -3, 0))
    broken.key("crown", "position", BROKEN_TIME, (0, -29, 0))
    broken.key("crown", "rotation", 1.0, (0, 0, 0))
    broken.key("crown", "rotation", BROKEN_TIME, (0, 0, 78))
    broken.key("spikes", "scale", 0.0, (1, 1, 0.18))
    broken.key("spikes", "scale", BROKEN_TIME, (1, 1, 0.05))
    broken.key("ember", "scale", 0.0, (0, 0, 0))
    broken.key("ember", "scale", BROKEN_TIME, (0, 0, 0))
    animations.append(broken)

    return animations
