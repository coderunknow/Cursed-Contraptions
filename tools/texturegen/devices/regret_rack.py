"""The Regret Rack — a timber stretching frame with a working winch.

v0.1.4 rebuild: roughly 1.7 x 2.2 x 1.2 blocks. A stone-and-timber bed, two
braced posts, a top beam, a ratcheted winch drum with a spoked crank, rope
loops that pull taut on capture, iron manacles that clamp shut, and a soul
lantern that swings over the victim.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    BLOOD,
    IRON_BLACK,
    LEATHER,
    ROPE,
    ROPE_DARK,
    RUST,
    SOUL,
    SOUL_LIGHT,
    SOUL_PALE,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    STEEL_MID,
    WOOD,
    WOOD_DARK,
    WOOD_LIGHT,
    WOOD_MID,
    chain,
    cracks,
    flat,
    leather,
    rope,
    soul_glow,
    spoked_wheel,
    steel_panel,
    steel_plate,
    stone_brick,
    wood_frame,
)
from canvas import mix, rgba, shade
from model import Face, Model
from pipeline import DeviceArt, scale_device

CAPTURE_DELAY = 1.5
CLOSE_DURATION = 2.0
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 5.0
RELEASE_TIME = 1.0
BROKEN_TIME = 1.5
STRAIN_TIME = 0.7
BURST_TIME = 0.45

# World size: authored scale x1.5 (1 unit = 1/16 block) -> ~2.2 blocks tall.
SCALE = 1.5

HIDDEN = rgba("#1a140e")

MANACLE_SHUT = 0.0
MANACLE_OPEN = -62.0


def face(paint, **kwargs) -> Face:
    return Face(paint=paint, **kwargs)


def patch(color, key: str, size=(1, 1)) -> Face:
    return Face(paint=flat(color), size=size, share=f"flat:{key}")


HIDDEN_FLAT = lambda: patch(HIDDEN, "hidden")  # noqa: E731
DARK_FLAT = lambda: patch(IRON_BLACK, "iron_black")  # noqa: E731


def clear(painter) -> None:
    painter.clear()


CLEAR_FLAT = lambda: Face(paint=clear, size=(1, 1), share="flat:clear")  # noqa: E731


def bed_boards(painter) -> None:
    """Stained timber bed with iron reinforcement."""
    wood_frame(WOOD, light=WOOD_LIGHT, dark=WOOD_DARK, braces=2)(painter)
    width, height = painter.rect.width, painter.rect.height
    for column in range(2, width, 5):
        painter.vline(column, 1, height - 1, shade(WOOD_DARK, 0.1))
        painter.vline(min(width - 1, column + 1), 1, height - 1, shade(WOOD_LIGHT, 0.1))
    for _ in range(3):
        column = painter.rng.between(1, max(1, width - 3))
        row = painter.rng.between(1, max(1, height - 4))
        painter.box(column, row, painter.rng.between(2, 3), painter.rng.between(2, 5),
                    shade(BLOOD, painter.rng.between(80, 160) / 255.0))
    painter.bevel(WOOD_LIGHT, WOOD_DARK, alpha=120)


def post(painter) -> None:
    """Braced timber post with iron bands."""
    wood_frame(WOOD_MID, light=WOOD_LIGHT, dark=WOOD_DARK, braces=3)(painter)
    width, height = painter.rect.width, painter.rect.height
    for row in range(2, height, 5):
        painter.hline(0, row, width, shade(WOOD_DARK, 0.05))
        painter.hline(0, min(height - 1, row + 1), width, shade(WOOD_LIGHT, 0.08))
    for row in (max(2, height // 4), height - max(3, height // 4)):
        painter.box(0, row, width, 1, shade(STEEL_DARK, -0.1))
        painter.box(0, row + 1, width, 1, STEEL_MID)
        painter.px(max(1, width // 2), row, STEEL_HIGHLIGHT)
    painter.bevel(WOOD_LIGHT, WOOD_DARK, alpha=120)


def rope_coil(painter) -> None:
    rope(ROPE, dark=ROPE_DARK)(painter)


def manacle(painter) -> None:
    """An iron cuff, drawn as a band with rivets and a hinge."""
    width, height = painter.rect.width, painter.rect.height
    painter.fill(shade(STEEL_DARK, -0.1))
    painter.gradient_v(shade(STEEL_MID, 0.1), shade(STEEL_DARK, -0.15))
    painter.hline(0, 0, width, STEEL_HIGHLIGHT)
    painter.hline(0, height - 1, width, IRON_BLACK)
    for column in range(0, width, 3):
        painter.px(column, max(0, height // 2), STEEL_LIGHT)
    painter.bevel(STEEL_LIGHT, IRON_BLACK, alpha=150)


def lantern(painter) -> None:
    """Iron lantern head with soul fire behind the bars."""
    width, height = painter.rect.width, painter.rect.height
    painter.fill(STEEL_DARK)
    inner_width = max(1, width - 2)
    inner_height = max(1, height - 4)
    painter.box(1, 2, inner_width, inner_height, shade(SOUL, -0.25))
    painter.box(1, 2, inner_width, max(1, inner_height - 2), mix(SOUL, SOUL_PALE, 0.4))
    painter.vline(max(1, width // 2), 2, inner_height, SOUL_PALE)
    painter.box(0, 0, width, 1, STEEL_MID)
    painter.box(0, 1, width, 1, STEEL_LIGHT)
    painter.box(0, height - 1, width, 1, IRON_BLACK)
    painter.bevel(STEEL_LIGHT, IRON_BLACK, alpha=140)


def cracked_timber(seed: int, count: int = 5):
    return cracks(seed, count=count, color=IRON_BLACK, glow=shade(RUST, 0.05))


def winch_barrel(painter) -> None:
    """Rope wound around the winch drum."""
    rope(ROPE, dark=ROPE_DARK)(painter)
    width, height = painter.rect.width, painter.rect.height
    for row in range(1, height, 2):
        painter.px(0, row, shade(ROPE_DARK, -0.2))
        painter.px(max(0, width - 1), row, shade(ROPE, 0.15))


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_regret_rack",
        texture_width=128,
        texture_height=128,
    )

    # ---------------------------------------------------------------- base --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-8, 0, -7], [16, 3, 14],
        {
            "up": face(stone_brick()),
            "north": face(stone_brick(), share="plinth"),
            "south": face(stone_brick(), share="plinth"),
            "east": face(stone_brick(), share="plinth"),
            "west": face(stone_brick(), share="plinth"),
            "down": HIDDEN_FLAT(),
        },
    )
    base.cube(
        [-7, 3, -6], [14, 3, 12],  # the rack bed
        {
            "up": face(bed_boards),
            "north": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
            "south": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
            "east": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
            "west": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- posts --
    for sign, key in ((-1, "left"), (1, "right")):
        post_x = -8 if sign < 0 else 5
        base.cube(
            [post_x, 6, -4], [3, 16, 3],  # upright
            {
                "up": DARK_FLAT(),
                "north": face(post, size=(3, 16), share="post_side"),
                "south": face(post, size=(3, 16), share="post_side"),
                "east": face(post, size=(3, 16), share="post_side"),
                "west": face(post, size=(3, 16), share="post_side"),
                "down": HIDDEN_FLAT(),
            },
        )
        base.cube(
            [post_x, 6, 3], [3, 8, 2],  # rear batten
            {
                "up": HIDDEN_FLAT(),
                "north": face(post, size=(3, 8), share="batten_side"),
                "south": face(post, size=(3, 8), share="batten_side"),
                "east": face(post, size=(2, 8), share="batten_edge"),
                "west": face(post, size=(2, 8), share="batten_edge"),
                "down": HIDDEN_FLAT(),
            },
        )
    base.cube(
        [-8, 12, -7], [16, 3, 2],  # front cross brace
        {
            "up": face(wood_frame(WOOD_LIGHT, braces=2)),
            "north": face(post, size=(16, 3), share="brace_side"),
            "south": face(post, size=(16, 3), share="brace_side"),
            "east": face(post, size=(2, 3), share="brace_end"),
            "west": face(post, size=(2, 3), share="brace_end"),
            "down": face(wood_frame(WOOD_DARK, braces=1), size=(16, 2), share="brace_under"),
        },
    )

    beam = model.bone("beam", [0, 20, 0], parent="base")
    beam.cube(
        [-9, 20, -5], [18, 3, 8],
        {
            "up": face(wood_frame(WOOD_LIGHT, braces=3)),
            "north": face(post, size=(18, 3), share="beam_side"),
            "south": face(post, size=(18, 3), share="beam_side"),
            "east": face(post, size=(8, 3), share="beam_end"),
            "west": face(post, size=(8, 3), share="beam_end"),
            "down": face(wood_frame(WOOD_DARK, braces=2), size=(18, 8), share="beam_under"),
        },
    )
    beam.cube(
        [-3, 23, -3], [6, 1, 5],  # iron cap
        {
            "up": face(steel_panel(STEEL, bands=1, seams=1)),
            "north": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), size=(6, 1), share="cap_front"),
            "south": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), size=(6, 1), share="cap_front"),
            "east": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), size=(5, 1), share="cap_edge"),
            "west": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), size=(5, 1), share="cap_edge"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- winch --
    winch = model.bone("winch", [9.5, 15, 1.5], parent="base")
    winch.cube(
        [-5, 13, 0], [13, 4, 3],  # drum, spinning on the X axis
        {
            "up": face(winch_barrel, size=(13, 3)),
            "north": face(winch_barrel, size=(13, 4)),
            "south": face(winch_barrel, share="barrel_back"),
            "east": face(steel_panel(STEEL_MID, bands=1, seams=1)),
            "west": face(steel_panel(STEEL_DARK, bands=1, seams=1), share="drum_end"),
            "down": HIDDEN_FLAT(),
        },
    )
    winch.cube(
        [9, 9.5, -4], [1, 11, 11],  # crank wheel, centred on the axle
        {
            "up": HIDDEN_FLAT(),
            "north": HIDDEN_FLAT(),
            "south": HIDDEN_FLAT(),
            "east": face(spoked_wheel(STEEL, light=STEEL_HIGHLIGHT, spokes=6)),
            "west": face(spoked_wheel(STEEL, light=STEEL_HIGHLIGHT, spokes=6), share="wheel"),
            "down": HIDDEN_FLAT(),
        },
    )
    winch.cube(
        [10, 13, 5], [3, 2, 3],  # crank handle at the rim
        {
            "up": face(steel_panel(STEEL_LIGHT, bands=1, seams=1, rivets=False)),
            "north": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "south": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "east": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "west": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "down": HIDDEN_FLAT(),
        },
    )
    winch.cube(
        [-1, 17.5, 0], [3, 2, 3],  # ratchet pawl on the drum
        {
            "up": face(steel_panel(STEEL_LIGHT, bands=1, seams=1, rivets=False)),
            "north": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "south": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "east": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "west": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="pawl"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- ropes --
    rope_bone = model.bone("ropes", [0, 20, 0], parent="base")
    for column in (-6, 4):
        rope_bone.cube(
            [column, 9, -1], [2, 11, 2],
            {
                "up": HIDDEN_FLAT(),
                "north": face(rope_coil, share="rope"),
                "south": face(rope_coil, share="rope"),
                "east": face(rope_coil, share="rope"),
                "west": face(rope_coil, share="rope"),
                "down": HIDDEN_FLAT(),
            },
        )

    # ------------------------------------------------------------- manacles --
    # The victim lies on the bed with both arms out along X; each wrist rests
    # on a board with an iron cuff that hinges shut over it.
    for side, sign in (("left", -1), ("right", 1)):
        board_x = -7 if sign < 0 else 2
        cuff_x = -7 if sign < 0 else 4
        manacle_bone = model.bone(f"manacle_{side}", [cuff_x + 1.5, 9, 2], parent="base")
        manacle_bone.cube(
            [board_x, 6, -1], [5, 1, 3],  # wrist board on the bed
            {
                "up": face(bed_boards, share="bed_top"),
                "north": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
                "south": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
                "east": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
                "west": face(wood_frame(WOOD_DARK, braces=1), share="bed_side"),
                "down": HIDDEN_FLAT(),
            },
        )
        manacle_bone.cube(
            [cuff_x, 7, -1], [3, 2, 3],  # the cuff itself
            {
                "up": face(manacle),
                "north": face(manacle, share="manacle"),
                "south": face(manacle, share="manacle"),
                "east": face(manacle, share="manacle"),
                "west": face(manacle, share="manacle"),
                "down": HIDDEN_FLAT(),
            },
        )

    # -------------------------------------------------------------- lantern --
    lantern_bone = model.bone("lantern", [0, 20, -6], parent="beam")
    lantern_bone.cube(
        [-1, 14, -7], [2, 6, 1],  # chain from the beam
        {
            "up": HIDDEN_FLAT(),
            "north": face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_MID)),
            "south": face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_MID), share="chain"),
            "east": face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_MID), share="chain"),
            "west": face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_MID), share="chain"),
            "down": HIDDEN_FLAT(),
        },
    )
    lantern_bone.cube(
        [-2, 10, -8], [4, 4, 3],  # lamp
        {
            "up": face(steel_panel(STEEL_DARK, bands=1, seams=1)),
            "north": face(lantern),
            "south": face(lantern, share="lantern"),
            "east": face(lantern, share="lantern"),
            "west": face(lantern, share="lantern"),
            "down": face(lantern, share="lantern"),
        },
    )

    # ----------------------------------------------------------- wear plates --
    wear_1 = model.bone("wear_1_bed", [0, 6, 0], parent="base")
    wear_1.cube(
        [-4, 6, -6.2], [9, 1, 3],
        {
            "up": face(cracked_timber(31, 5)),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_2 = model.bone("wear_2_beam", [0, 23, 0], parent="beam")
    wear_2.cube(
        [-8, 23, -4], [14, 1, 5],
        {
            "up": face(cracked_timber(32, 6)),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_3 = model.bone("wear_3_post", [9, 12, -2], parent="base")
    wear_3.cube(
        [9, 8, -3], [1, 11, 5],
        {
            "up": CLEAR_FLAT(),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": face(cracked_timber(33, 4)),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )

    return scale_device(DeviceArt(
        slug="regret_rack",
        display_name="The Regret Rack",
        model=model,
        animations=animations(),
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:basic_flame_particle",
    ), SCALE)


# --------------------------------------------------------------- animations --
def animations() -> list[Animation]:
    return [
        _idle(),
        _detect(),
        _close(),
        _closed(),
        _torture(1.0, "animation.cc_regret_rack.torture"),
        _torture(0.6, "animation.cc_regret_rack.torture_high"),
        _strain(),
        _burst(),
        _open(),
        _released(),
        _broken(),
    ]


def _manacles(animation: Animation, values) -> None:
    """Both cuffs hinge about X at their back-top edge, so they open backward."""
    for time, angle in values:
        animation.key("manacle_left", "rotation", time, (angle, 0, 0))
        animation.key("manacle_right", "rotation", time, (angle, 0, 0))


def _idle() -> Animation:
    idle = Animation("animation.cc_regret_rack.idle", 4.0, loop=True)
    for time, angle in ((0.0, 4), (2.0, -4), (4.0, 4)):
        idle.key("lantern", "rotation", time, (0, angle, 0))
    idle.key("lantern", "position", 0.0, (0, 0, 0))
    idle.key("lantern", "position", 2.0, (0, -0.3, 0))
    idle.key("lantern", "position", 4.0, (0, 0, 0))
    _manacles(idle, ((0.0, MANACLE_OPEN), (4.0, MANACLE_OPEN)))
    idle.key("winch", "rotation", 0.0, (0, 0, 0))
    idle.key("winch", "rotation", 4.0, (0, 0, 0))
    idle.key("ropes", "scale", 0.0, (1, 1, 1))
    idle.key("ropes", "scale", 4.0, (1, 1, 1))
    return idle


def _detect() -> Animation:
    detect = Animation("animation.cc_regret_rack.detect", CAPTURE_DELAY, loop=True)
    _manacles(detect, ((0.0, MANACLE_OPEN), (CAPTURE_DELAY, MANACLE_OPEN - 14)))
    detect.key("winch", "rotation", 0.0, (0, 0, 0))
    detect.key("winch", "rotation", CAPTURE_DELAY, (-38, 0, 0))
    detect.key("ropes", "scale", 0.0, (1, 1, 1))
    detect.key("ropes", "scale", CAPTURE_DELAY, (1, 1.06, 1))
    detect.key("lantern", "rotation", 0.0, (4, 0, 0))
    detect.key("lantern", "rotation", CAPTURE_DELAY, (-14, 0, 6))
    detect.key("lantern", "position", 0.0, (0, 0, 0))
    detect.key("lantern", "position", CAPTURE_DELAY, (0, 1.2, 0))
    detect.key("beam", "rotation", 0.0, (0, 0, 0))
    detect.key("beam", "rotation", CAPTURE_DELAY, (0, 0, 1.2))
    return detect


def _close() -> Animation:
    close = Animation("animation.cc_regret_rack.close", CLOSE_DURATION, loop=False)
    _manacles(close, ((0.0, MANACLE_OPEN - 14), (0.4, -6), (0.62, MANACLE_SHUT), (CLOSE_DURATION, MANACLE_SHUT)))
    close.key("winch", "rotation", 0.0, (-38, 0, 0))
    close.key("winch", "rotation", 0.5, (-96, 0, 0))
    close.key("winch", "rotation", 0.7, (-88, 0, 0))
    close.key("winch", "rotation", 1.1, (-190, 0, 0))
    close.key("winch", "rotation", CLOSE_DURATION, (-196, 0, 0))
    close.key("ropes", "scale", 0.0, (1, 1.06, 1))
    close.key("ropes", "scale", 0.8, (1, 1.14, 1))
    close.key("ropes", "scale", CLOSE_DURATION, (1, 1.12, 1))
    for time, angle in ((0.0, 1.2), (0.45, -2.4), (0.85, 1.4), (CLOSE_DURATION, 0)):
        close.key("beam", "rotation", time, (0, 0, angle))
    close.key("lantern", "rotation", 0.0, (-14, 0, 6))
    close.key("lantern", "rotation", 0.5, (18, 0, -8))
    close.key("lantern", "rotation", 1.0, (-9, 0, 4))
    close.key("lantern", "rotation", CLOSE_DURATION, (-4, 0, 0))
    close.key("base", "rotation", 0.0, (0, 0, 0))
    close.key("base", "rotation", 0.6, (0, 0, -1.4))
    close.key("base", "rotation", CLOSE_DURATION, (0, 0, 0))
    return close


def _closed() -> Animation:
    closed = Animation("animation.cc_regret_rack.closed", CLOSED_PAUSE, loop=True)
    closed.key("lantern", "rotation", 0.0, (-4, 0, 0))
    closed.key("lantern", "rotation", 0.25, (-7, 0, 2))
    closed.key("lantern", "rotation", 0.5, (-4, 0, 0))
    closed.key("winch", "rotation", 0.0, (-196, 0, 0))
    closed.key("winch", "rotation", 0.5, (-196, 0, 0))
    closed.key("ropes", "scale", 0.0, (1, 1.12, 1))
    closed.key("ropes", "scale", 0.5, (1, 1.12, 1))
    return closed


def _torture(amplitude: float, identifier: str) -> Animation:
    torture = Animation(identifier, TORTURE_INTERVAL, loop=True)
    # The winch steps a turn at a time: that is the rack doing its work.
    steps = 6
    for index in range(steps + 1):
        time = TORTURE_INTERVAL * index / steps
        torture.key("winch", "rotation", time, (-196 - 66 * amplitude * index, 0, 0))
        torture.key("ropes", "scale", time, (1, 1.12 + 0.03 * amplitude * (index % 2), 1))
    torture.key("beam", "rotation", 0.0, (0, 0, 0))
    torture.key("beam", "rotation", 0.6 * amplitude, (0, 0, -2.2 * amplitude))
    torture.key("beam", "rotation", 1.5 * amplitude, (0, 0, 1.8 * amplitude))
    torture.key("beam", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("beam", "position", 0.0, (0, 0, 0))
    torture.key("beam", "position", 0.6 * amplitude, (0.6 * amplitude, 0, 0))
    torture.key("beam", "position", 1.5 * amplitude, (-0.6 * amplitude, 0, 0))
    torture.key("beam", "position", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("lantern", "rotation", 0.0, (-4, 0, 0))
    torture.key("lantern", "rotation", 0.8 * amplitude, (10 * amplitude, 0, -6))
    torture.key("lantern", "rotation", 1.8 * amplitude, (-8 * amplitude, 0, 5))
    torture.key("lantern", "rotation", TORTURE_INTERVAL, (-4, 0, 0))
    torture.key("lantern", "position", 0.0, (0, 0, 0))
    torture.key("lantern", "position", 0.9 * amplitude, (0, 0.8 * amplitude, 0))
    torture.key("lantern", "position", 2.0 * amplitude, (0, 0, 0))
    torture.key("lantern", "position", TORTURE_INTERVAL, (0, 0, 0))
    for bone, sign in (("manacle_left", 1), ("manacle_right", -1)):
        torture.key(bone, "rotation", 0.0, (0, 0, 0))
        torture.key(bone, "rotation", 0.5 * amplitude, (2.4 * amplitude, 0, 1.4 * sign))
        torture.key(bone, "rotation", TORTURE_INTERVAL, (0, 0, 0))
    return torture


def _strain() -> Animation:
    strain = Animation("animation.cc_regret_rack.strain", STRAIN_TIME, loop=False)
    strain.key("beam", "rotation", 0.0, (0, 0, 0))
    strain.key("beam", "rotation", 0.09, (0, 0, -3.4))
    strain.key("beam", "rotation", 0.2, (0, 0, 2.6))
    strain.key("beam", "rotation", 0.34, (0, 0, -1.6))
    strain.key("beam", "rotation", STRAIN_TIME, (0, 0, 0))
    strain.key("base", "position", 0.0, (0, 0, 0))
    strain.key("base", "position", 0.09, (0.35, 0, 0))
    strain.key("base", "position", 0.2, (-0.35, 0, 0))
    strain.key("base", "position", STRAIN_TIME, (0, 0, 0))
    strain.key("lantern", "rotation", 0.0, (0, 0, 0))
    strain.key("lantern", "rotation", 0.12, (22, 0, -12))
    strain.key("lantern", "rotation", 0.4, (-12, 0, 6))
    strain.key("lantern", "rotation", STRAIN_TIME, (0, 0, 0))
    return strain


def _burst() -> Animation:
    burst = Animation("animation.cc_regret_rack.burst", BURST_TIME, loop=False)
    burst.key("base", "position", 0.0, (0, 0, 0))
    burst.key("base", "position", 0.1, (0, 0.4, 0))
    burst.key("base", "position", BURST_TIME, (0, 0, 0))
    burst.key("beam", "rotation", 0.0, (0, 0, 0))
    burst.key("beam", "rotation", 0.1, (0, 0, -5))
    burst.key("beam", "rotation", 0.3, (0, 0, 2))
    burst.key("beam", "rotation", BURST_TIME, (0, 0, 0))
    burst.key("winch", "rotation", 0.0, (-196, 0, 0))
    burst.key("winch", "rotation", BURST_TIME, (-280, 0, 0))
    return burst


def _open() -> Animation:
    opened = Animation("animation.cc_regret_rack.open", RELEASE_TIME + 0.5, loop=False)
    end = RELEASE_TIME + 0.5
    _manacles(opened, ((0.0, MANACLE_SHUT), (0.35, -34), (0.6, MANACLE_OPEN - 6), (0.85, MANACLE_OPEN - 18), (end, MANACLE_OPEN)))
    opened.key("winch", "rotation", 0.0, (-196, 0, 0))
    opened.key("winch", "rotation", 0.5, (-60, 0, 0))
    opened.key("winch", "rotation", end, (0, 0, 0))
    opened.key("ropes", "scale", 0.0, (1, 1.12, 1))
    opened.key("ropes", "scale", 0.5, (1, 1.02, 1))
    opened.key("ropes", "scale", end, (1, 1, 1))
    opened.key("lantern", "rotation", 0.0, (-4, 0, 0))
    opened.key("lantern", "rotation", 0.5, (14, 0, -6))
    opened.key("lantern", "rotation", end, (4, 0, 0))
    return opened


def _released() -> Animation:
    released = Animation("animation.cc_regret_rack.released", RELEASE_TIME, loop=False)
    _manacles(released, ((0.0, MANACLE_OPEN), (0.35, MANACLE_OPEN - 5), (0.7, MANACLE_OPEN + 3), (RELEASE_TIME, MANACLE_OPEN)))
    released.key("lantern", "rotation", 0.0, (4, 0, 0))
    released.key("lantern", "rotation", 0.5, (-6, 0, 0))
    released.key("lantern", "rotation", RELEASE_TIME, (4, 0, 0))
    return released


def _broken() -> Animation:
    broken = Animation("animation.cc_regret_rack.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("beam", "rotation", 0.0, (0, 0, 0))
    broken.key("beam", "rotation", 0.8, (0, 0, 9))
    broken.key("beam", "rotation", BROKEN_TIME, (0, 0, 13))
    broken.key("beam", "position", 0.0, (0, 0, 0))
    broken.key("beam", "position", 1.0, (0, -3, 0))
    broken.key("beam", "position", BROKEN_TIME, (0, -6, 1))
    broken.key("winch", "rotation", 0.0, (-196, 0, 0))
    broken.key("winch", "rotation", BROKEN_TIME, (-120, 0, 0))
    broken.key("winch", "position", 0.0, (0, 0, 0))
    broken.key("winch", "position", 1.1, (1.5, -8, 0))
    broken.key("winch", "position", BROKEN_TIME, (2.4, -14, 0))
    broken.key("ropes", "scale", 0.0, (1, 1.12, 1))
    broken.key("ropes", "scale", BROKEN_TIME, (1, 0.9, 1))
    broken.key("base", "rotation", 0.0, (0, 0, 0))
    broken.key("base", "rotation", BROKEN_TIME, (0, 0, -3))
    broken.key("lantern", "rotation", 0.0, (0, 0, 0))
    broken.key("lantern", "rotation", BROKEN_TIME, (36, 0, -18))
    broken.key("lantern", "position", 0.0, (0, 0, 0))
    broken.key("lantern", "position", BROKEN_TIME, (0, -4, 0))
    return broken
