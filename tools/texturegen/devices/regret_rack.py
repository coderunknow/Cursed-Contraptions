"""The Regret Rack — a windlass bench: spoked wheels, creaking ropes, manacles.

Layout: a low platform the captive is stretched across, iron side rails with
manacle rings, a head post carrying the winding drum, and two spoked wheels
that turn while the device works. The ropes are their own bone so they can
visibly tighten and go slack.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    GOLD,
    IRON_BLACK,
    LEATHER,
    ROPE,
    ROPE_DARK,
    RUST,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    WOOD,
    WOOD_DARK,
    WOOD_LIGHT,
    chain,
    iron_bar,
    leather,
    planks,
    rope,
    steel_plate,
)
from model import Face, Model
from pipeline import DeviceArt
from _kit import finalize, flat_face, shared_face

CAPTURE_DELAY = 1.5
CLOSE_DURATION = 2.0
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 5.0
RELEASE_TIME = 1.2
BROKEN_TIME = 1.8


WHEEL_PATTERN = [
    "..####..",
    ".#....#.",
    "#..oo..#",
    "#.oHHo.#",
    "#.oHHo.#",
    "#..oo..#",
    ".#....#.",
    "..####..",
]


def _wheel():
    """An 8x8 spoked wheel. The gaps stay transparent for ``entity_alphatest``."""

    def paint(painter) -> None:
        from artkit import GOLD_LIGHT

        painter.stencil_map(
            WHEEL_PATTERN,
            {
                "#": STEEL_HIGHLIGHT,
                "o": STEEL_LIGHT,
                "H": GOLD,
                "h": GOLD_LIGHT,
            },
        )
        for row in range(painter.rect.height):
            for column in range(painter.rect.width):
                if painter.px_get(column, row)[3] == 0:
                    continue
                if painter.rng.below(0.12):
                    painter.blend_px(column, row, RUST, 0.35)

    return paint


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_regret_rack",
        texture_width=64,
        texture_height=64,
        visible_bounds=(2.4, 1.8),
        visible_offset=(0.0, 0.9, 0.0),
    )

    # ------------------------------------------------------------ platform --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-8, 0, -3], [16, 2, 6],
        {
            "up": shared_face(planks(WOOD, light=WOOD_LIGHT, dark=WOOD_DARK, count=4, knots=3), "rack_platform"),
            "north": shared_face(planks(WOOD_DARK, count=2, knots=1), "rack_side"),
            "south": shared_face(planks(WOOD_DARK, count=2, knots=1), "rack_side"),
            "east": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.2, rust=0.4), "rack_end"),
            "west": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.2, rust=0.4), "rack_end"),
            "down": flat_face(WOOD_DARK, "wood_dark"),
        },
    )
    # Iron corner feet.
    for column, row in ((-8, -3), (6, -3), (-8, 2), (6, 2)):
        base.cube(
            [column, 0, row], [2, 3, 1],
            {
                "north": shared_face(steel_plate(STEEL, rivets=True), "rack_foot"),
                "south": shared_face(steel_plate(STEEL, rivets=True), "rack_foot"),
                "east": flat_face(STEEL_DARK, "steel_dark"),
                "west": flat_face(STEEL_DARK, "steel_dark"),
                "up": flat_face(STEEL_LIGHT, "steel_flat"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Side rails with manacle rings.
    for column in (-8, 6):
        base.cube(
            [column, 2, -3], [2, 2, 6],
            {
                "up": shared_face(steel_plate(STEEL, rivets=True), "rack_rail"),
                "north": flat_face(STEEL_DARK, "steel_dark"),
                "south": flat_face(STEEL_DARK, "steel_dark"),
                "east": flat_face(STEEL_DARK, "steel_dark"),
                "west": flat_face(STEEL_DARK, "steel_dark"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Head post and winding drum.
    base.cube(
        [-2, 2, -5], [4, 12, 2],
        {
            "north": shared_face(planks(WOOD, count=2, knots=1), "rack_post"),
            "south": shared_face(planks(WOOD, count=2, knots=1), "rack_post"),
            "east": shared_face(planks(WOOD_DARK, count=2, knots=1), "rack_post_side"),
            "west": shared_face(planks(WOOD_DARK, count=2, knots=1), "rack_post_side"),
            "up": flat_face(WOOD_LIGHT, "wood_light"),
            "down": flat_face(WOOD_DARK, "wood_dark"),
        },
    )
    base.cube(
        [-5, 11, -5], [10, 3, 3],
        {
            "north": shared_face(steel_plate(STEEL, rivets=True, grime=0.2), "rack_drum"),
            "south": shared_face(steel_plate(STEEL, rivets=True, grime=0.2), "rack_drum"),
            "east": shared_face(chain(STEEL, dark=IRON_BLACK), "rack_drum_wrap"),
            "west": shared_face(chain(STEEL, dark=IRON_BLACK), "rack_drum_wrap"),
            "up": flat_face(STEEL_DARK, "steel_dark"),
            "down": flat_face(IRON_BLACK, "iron_black"),
        },
    )

    # -------------------------------------------------------------- wheels --
    wheel_paint = _wheel()
    for name, column in (("wheel_left", -10), ("wheel_right", 9)):
        bone = model.bone(name, [column + 0.5, 7, 0], parent="base")
        bone.cube(
            [column, 3, -3], [1, 8, 8],
            {
                "east": shared_face(wheel_paint, "rack_wheel"),
                "west": shared_face(wheel_paint, "rack_wheel_inner", flip_u=True),
                "north": flat_face(STEEL_DARK, "steel_dark"),
                "south": flat_face(STEEL_DARK, "steel_dark"),
                "up": flat_face(STEEL_DARK, "steel_dark"),
                "down": flat_face(STEEL_DARK, "steel_dark"),
            },
        )
        bone.cube(
            [column - 1, 6, -1], [3, 2, 2],
            {
                "north": shared_face(steel_plate(STEEL_LIGHT, rivets=False), "rack_axle"),
                "south": shared_face(steel_plate(STEEL_LIGHT, rivets=False), "rack_axle"),
                "east": flat_face(STEEL, "steel_flat"),
                "west": flat_face(STEEL, "steel_flat"),
                "up": flat_face(STEEL_LIGHT, "steel_flat"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )

    # --------------------------------------------------------------- ropes --
    ropes = model.bone("ropes", [0, 4, 0], parent="base")
    for row in (-2, 2):
        ropes.cube(
            [-8, 2, row], [4, 1, 1],
            {
                "up": shared_face(rope(), "rack_rope"),
                "north": shared_face(rope(), "rack_rope"),
                "south": shared_face(rope(), "rack_rope"),
                "down": shared_face(rope(), "rack_rope"),
                "east": flat_face(ROPE_DARK, "rope_dark"),
                "west": flat_face(ROPE_DARK, "rope_dark"),
            },
        )
    for row in (-2, 2):
        ropes.cube(
            [4, 2, row], [4, 1, 1],
            {
                "up": shared_face(rope(), "rack_rope"),
                "north": shared_face(rope(), "rack_rope"),
                "south": shared_face(rope(), "rack_rope"),
                "down": shared_face(rope(), "rack_rope"),
                "east": flat_face(ROPE_DARK, "rope_dark"),
                "west": flat_face(ROPE_DARK, "rope_dark"),
            },
        )

    # ------------------------------------------------------------ manacles --
    manacles = model.bone("manacles", [0, 3, 0], parent="base")
    for column, row in ((-8, -2), (-8, 1), (6, -2), (6, 1)):
        manacles.cube(
            [column, 3, row], [2, 1, 2],
            {
                "up": shared_face(steel_plate(STEEL_LIGHT, rivets=False), "rack_manacle"),
                "north": flat_face(STEEL, "steel_flat"),
                "south": flat_face(STEEL, "steel_flat"),
                "east": flat_face(STEEL, "steel_flat"),
                "west": flat_face(STEEL, "steel_flat"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )

    animations = _animations()
    art = DeviceArt(
        slug="regret_rack",
        display_name="The Regret Rack",
        model=model,
        animations=animations,
        state_animations={},
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:basic_crit_particle",
    )
    return finalize(art)


def _animations() -> list[Animation]:
    animations: list[Animation] = []

    idle = Animation("animation.cc_regret_rack.idle", 4.0, loop=True)
    idle.key("wheel_left", "rotation", 0.0, (0, 0, 0))
    idle.key("wheel_left", "rotation", 4.0, (0, 0, 360))
    idle.key("wheel_right", "rotation", 0.0, (0, 0, 0))
    idle.key("wheel_right", "rotation", 4.0, (0, 0, -360))
    idle.key("ropes", "position", 0.0, (0, 0, 0))
    idle.key("ropes", "position", 2.0, (0, 0.1, 0))
    idle.key("ropes", "position", 4.0, (0, 0, 0))
    idle.key("base", "rotation", 0.0, (0, 0, 0))
    idle.key("base", "rotation", 4.0, (0, 0, 0))
    animations.append(idle)

    detect = Animation("animation.cc_regret_rack.detect", CAPTURE_DELAY, loop=True)
    detect.key("wheel_left", "rotation", 0.0, (0, 0, 0))
    detect.key("wheel_left", "rotation", 0.5, (0, 0, 40))
    detect.key("wheel_left", "rotation", 1.0, (0, 0, 30))
    detect.key("wheel_left", "rotation", 1.5, (0, 0, 58))
    detect.key("wheel_right", "rotation", 0.0, (0, 0, 0))
    detect.key("wheel_right", "rotation", 0.5, (0, 0, -40))
    detect.key("wheel_right", "rotation", 1.0, (0, 0, -30))
    detect.key("wheel_right", "rotation", 1.5, (0, 0, -58))
    detect.key("ropes", "scale", 0.0, (1, 1, 1))
    detect.key("ropes", "scale", 0.7, (1.02, 1, 1))
    detect.key("ropes", "scale", 1.5, (1.05, 1, 1))
    detect.key("manacles", "scale", 0.0, (1, 1, 1))
    detect.key("manacles", "scale", 1.5, (1.02, 1.02, 1.02))
    animations.append(detect)

    close = Animation("animation.cc_regret_rack.close", CLOSE_DURATION, loop=False)
    close.key("wheel_left", "rotation", 0.0, (0, 0, 58))
    close.key("wheel_left", "rotation", 0.6, (0, 0, 150))
    close.key("wheel_left", "rotation", 1.1, (0, 0, 176))
    close.key("wheel_left", "rotation", CLOSE_DURATION, (0, 0, 180))
    close.key("wheel_right", "rotation", 0.0, (0, 0, -58))
    close.key("wheel_right", "rotation", 0.6, (0, 0, -150))
    close.key("wheel_right", "rotation", 1.1, (0, 0, -176))
    close.key("wheel_right", "rotation", CLOSE_DURATION, (0, 0, -180))
    close.key("ropes", "scale", 0.0, (1.05, 1, 1))
    close.key("ropes", "scale", 0.6, (1.18, 1, 1))
    close.key("ropes", "scale", 0.8, (1.15, 1, 1))
    close.key("ropes", "scale", CLOSE_DURATION, (1.16, 1, 1))
    close.key("base", "rotation", 0.0, (0, 0, 0))
    close.key("base", "rotation", 0.5, (0, 0, 1.5))
    close.key("base", "rotation", 0.9, (0, 0, -1))
    close.key("base", "rotation", CLOSE_DURATION, (0, 0, 0))
    animations.append(close)

    closed = Animation("animation.cc_regret_rack.closed", CLOSED_PAUSE, loop=True)
    closed.key("ropes", "scale", 0.0, (1.16, 1, 1))
    closed.key("ropes", "scale", 0.5, (1.165, 1, 1))
    closed.key("base", "rotation", 0.0, (0, 0, 0))
    closed.key("base", "rotation", 0.5, (0, 0, 0))
    animations.append(closed)

    torture = Animation("animation.cc_regret_rack.torture", TORTURE_INTERVAL, loop=True)
    # Ratchet: two hard cranks per cycle, rope creeps longer then springs back.
    torture.key("wheel_left", "rotation", 0.0, (0, 0, 0))
    torture.key("wheel_left", "rotation", 0.35, (0, 0, 62))
    torture.key("wheel_left", "rotation", 0.55, (0, 0, 48))
    torture.key("wheel_left", "rotation", 1.1, (0, 0, 128))
    torture.key("wheel_left", "rotation", 1.3, (0, 0, 112))
    torture.key("wheel_left", "rotation", 3.4, (0, 0, 320))
    torture.key("wheel_left", "rotation", 5.0, (0, 0, 360))
    torture.key("wheel_right", "rotation", 0.0, (0, 0, 0))
    torture.key("wheel_right", "rotation", 0.35, (0, 0, -62))
    torture.key("wheel_right", "rotation", 0.55, (0, 0, -48))
    torture.key("wheel_right", "rotation", 1.1, (0, 0, -128))
    torture.key("wheel_right", "rotation", 1.3, (0, 0, -112))
    torture.key("wheel_right", "rotation", 3.4, (0, 0, -320))
    torture.key("wheel_right", "rotation", 5.0, (0, 0, -360))
    torture.key("ropes", "scale", 0.0, (1.16, 1, 1))
    torture.key("ropes", "scale", 1.6, (1.24, 1, 1))
    torture.key("ropes", "scale", 2.1, (1.1, 1, 1))
    torture.key("ropes", "scale", 3.4, (1.2, 1, 1))
    torture.key("ropes", "scale", 4.2, (1.16, 1, 1))
    torture.key("ropes", "scale", 5.0, (1.16, 1, 1))
    torture.key("base", "rotation", 0.0, (0, 0, 0))
    torture.key("base", "rotation", 0.35, (0, 0, 2.2))
    torture.key("base", "rotation", 0.8, (0, 0, -1.4))
    torture.key("base", "rotation", 1.3, (0, 0, 0))
    torture.key("base", "rotation", 3.5, (0, 0, 1.6))
    torture.key("base", "rotation", 4.2, (0, 0, 0))
    torture.key("base", "rotation", 5.0, (0, 0, 0))
    torture.key("manacles", "scale", 0.0, (1, 1, 1))
    torture.key("manacles", "scale", 1.6, (1.05, 1.05, 1.05))
    torture.key("manacles", "scale", 2.1, (1, 1, 1))
    torture.key("manacles", "scale", 5.0, (1, 1, 1))
    animations.append(torture)

    strain = Animation("animation.cc_regret_rack.strain", 0.6, loop=False)
    for time, angle in ((0.0, 0), (0.08, 6), (0.16, -5), (0.26, 3.5), (0.36, -2.5), (0.5, 1), (0.6, 0)):
        strain.key("base", "rotation", time, (0, 0, angle))
    strain.key("ropes", "scale", 0.0, (1.16, 1, 1))
    strain.key("ropes", "scale", 0.1, (1.24, 1, 1))
    strain.key("ropes", "scale", 0.3, (1.12, 1, 1))
    strain.key("ropes", "scale", 0.6, (1.16, 1, 1))
    strain.key("wheel_left", "rotation", 0.0, (0, 0, 0))
    strain.key("wheel_left", "rotation", 0.2, (0, 0, 12))
    strain.key("wheel_left", "rotation", 0.45, (0, 0, -8))
    strain.key("wheel_left", "rotation", 0.6, (0, 0, 0))
    strain.key("wheel_right", "rotation", 0.0, (0, 0, 0))
    strain.key("wheel_right", "rotation", 0.2, (0, 0, -12))
    strain.key("wheel_right", "rotation", 0.45, (0, 0, 8))
    strain.key("wheel_right", "rotation", 0.6, (0, 0, 0))
    animations.append(strain)

    open_animation = Animation("animation.cc_regret_rack.open", RELEASE_TIME + 0.4, loop=False)
    open_animation.key("wheel_left", "rotation", 0.0, (0, 0, 0))
    open_animation.key("wheel_left", "rotation", 0.6, (0, 0, -120))
    open_animation.key("wheel_left", "rotation", RELEASE_TIME + 0.4, (0, 0, -108))
    open_animation.key("wheel_right", "rotation", 0.0, (0, 0, 0))
    open_animation.key("wheel_right", "rotation", 0.6, (0, 0, 120))
    open_animation.key("wheel_right", "rotation", RELEASE_TIME + 0.4, (0, 0, 108))
    open_animation.key("ropes", "scale", 0.0, (1.16, 1, 1))
    open_animation.key("ropes", "scale", 0.5, (0.86, 1, 1))
    open_animation.key("ropes", "scale", 0.9, (0.94, 1, 1))
    open_animation.key("ropes", "scale", RELEASE_TIME + 0.4, (0.92, 1, 1))
    open_animation.key("manacles", "scale", 0.0, (1, 1, 1))
    open_animation.key("manacles", "scale", 0.5, (0.95, 0.95, 0.95))
    open_animation.key("manacles", "scale", RELEASE_TIME + 0.4, (1, 1, 1))
    animations.append(open_animation)

    released = Animation("animation.cc_regret_rack.released", RELEASE_TIME, loop=False)
    released.key("ropes", "scale", 0.0, (0.92, 1, 1))
    released.key("ropes", "scale", 0.5, (0.98, 1, 1))
    released.key("ropes", "scale", RELEASE_TIME, (1, 1, 1))
    released.key("wheel_left", "rotation", 0.0, (0, 0, -108))
    released.key("wheel_left", "rotation", RELEASE_TIME, (0, 0, -90))
    released.key("wheel_right", "rotation", 0.0, (0, 0, 108))
    released.key("wheel_right", "rotation", RELEASE_TIME, (0, 0, 90))
    animations.append(released)

    broken = Animation("animation.cc_regret_rack.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("base", "rotation", 0.0, (0, 0, 0))
    broken.key("base", "rotation", 0.7, (6, 0, 8))
    broken.key("base", "rotation", BROKEN_TIME, (5, 0, 7))
    broken.key("base", "position", 0.0, (0, 0, 0))
    broken.key("base", "position", 1.0, (0, -2, 0))
    broken.key("base", "position", BROKEN_TIME, (0, -2, 0))
    broken.key("wheel_left", "rotation", 0.0, (0, 0, 0))
    broken.key("wheel_left", "rotation", 0.9, (0, 0, 140))
    broken.key("wheel_left", "rotation", BROKEN_TIME, (0, 0, 160))
    broken.key("wheel_left", "position", 0.0, (0, 0, 0))
    broken.key("wheel_left", "position", 1.2, (0, -6, -3))
    broken.key("wheel_left", "position", BROKEN_TIME, (0, -6, -3))
    broken.key("wheel_right", "rotation", 0.0, (0, 0, 0))
    broken.key("wheel_right", "rotation", 0.9, (0, 0, -150))
    broken.key("wheel_right", "rotation", BROKEN_TIME, (0, 0, -170))
    broken.key("wheel_right", "position", 0.0, (0, 0, 0))
    broken.key("wheel_right", "position", 1.2, (0, -6, 3))
    broken.key("wheel_right", "position", BROKEN_TIME, (0, -6, 3))
    broken.key("ropes", "scale", 0.0, (1, 1, 1))
    broken.key("ropes", "scale", 0.6, (0.7, 0.6, 0.6))
    broken.key("ropes", "scale", BROKEN_TIME, (0.7, 0.6, 0.6))
    broken.key("ropes", "position", 0.0, (0, 0, 0))
    broken.key("ropes", "position", 1.2, (0, -3, 0))
    broken.key("ropes", "position", BROKEN_TIME, (0, -3, 0))
    animations.append(broken)

    return animations
