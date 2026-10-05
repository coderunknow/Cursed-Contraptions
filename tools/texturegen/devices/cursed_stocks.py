"""Cursed Stocks — a braced timber bench that clamps its captive.

v0.1.4 rebuild: roughly 1.5 x 1.1 x 1.5 blocks with a stone plinth, a heavy
backboard, a hinged upper board that slams shut on capture, iron lock bars, a
side crank that spins while the device works, a chained stone weight, and wear
plates that appear as the timber splinters.

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
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    STEEL_MID,
    WOOD,
    WOOD_DARK,
    WOOD_LIGHT,
    WOOD_MID,
    cracks,
    flat,
    leather,
    rope,
    skull,
    spoked_wheel,
    steel_plate,
    steel_panel,
    stone_brick,
    wood_frame,
)
from canvas import mix, rgba, shade
from model import Face, Model
from pipeline import DeviceArt, scale_device

CAPTURE_DELAY = 0.75
CLOSE_DURATION = 1.0
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 4.0
RELEASE_TIME = 1.0
BROKEN_TIME = 1.5
# World size: authored scale x1.5 (1 unit = 1/16 block).
SCALE = 1.5

STRAIN_TIME = 0.7
BURST_TIME = 0.45

HIDDEN = rgba("#1b1712")
GLASS = rgba("#0b0906")

# Upper board closed / open, in degrees about X at the hinge (back edge).
BOARD_CLOSED = 0.0
BOARD_OPEN = -46.0
BOARD_LIFTED = -54.0


def face(paint, **kwargs) -> Face:
    return Face(paint=paint, **kwargs)


def patch(color, key: str, size=(1, 1)) -> Face:
    return Face(paint=flat(color), size=size, share=f"flat:{key}")


HIDDEN_FLAT = lambda: patch(HIDDEN, "hidden")  # noqa: E731
DARK_FLAT = lambda: patch(IRON_BLACK, "iron_black")  # noqa: E731


def clear(painter) -> None:
    painter.clear()


CLEAR_FLAT = lambda: Face(paint=clear, size=(1, 1), share="flat:clear")  # noqa: E731


def boards(painter) -> None:
    """The clamping board face: planks, iron straps, and worn notches."""
    wood_frame(WOOD, light=WOOD_LIGHT, dark=WOOD_DARK, braces=2)(painter)
    width, height = painter.rect.width, painter.rect.height
    for column in range(0, width, 4):
        painter.vline(column, 1, height - 2, shade(WOOD_DARK, 0.05))
        painter.vline(min(width - 1, column + 1), 1, height - 2, shade(WOOD_LIGHT, 0.12))
    for _ in range(3):
        column = painter.rng.between(1, max(1, width - 2))
        row = painter.rng.between(1, max(1, height - 3))
        painter.box(column, row, painter.rng.between(1, 2), painter.rng.between(2, 4), shade(WOOD_DARK, 0.25))
    painter.streaks(BLOOD, count=2, alpha_range=(50, 120))
    painter.bevel(WOOD_LIGHT, WOOD_DARK, alpha=110)


def notch(painter) -> None:
    """A cut-out hole for an ankle or a wrist: black, with chafed edges."""
    painter.fill(shade(WOOD_DARK, 0.05))
    width, height = painter.rect.width, painter.rect.height
    painter.box(0, 0, width, height, shade(WOOD_DARK, -0.1))
    painter.box(0, 0, width, 1, shade(WOOD_LIGHT, 0.1))
    painter.box(0, height - 1, width, 1, IRON_BLACK)
    painter.px(0, 0, shade(WOOD_LIGHT, 0.25))


def leather_strap(painter) -> None:
    leather(LEATHER)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.px(max(0, width // 2), 1, STEEL_LIGHT)
    painter.px(max(0, width // 2), max(1, height - 2), STEEL_LIGHT)


def rope_coil(painter) -> None:
    rope(ROPE, dark=ROPE_DARK)(painter)


def chained_weight(painter) -> None:
    """A stone block lashed with rope: the counterweight on the back."""
    stone_brick(rgba("#514b43"))(painter)
    width, height = painter.rect.width, painter.rect.height
    for row in range(2, height - 2, 3):
        painter.hline(0, row, width, ROPE_DARK)
    painter.bevel(ROPE, IRON_BLACK, alpha=120)


def cracked_timber(seed: int, count: int = 5):
    return cracks(seed, count=count, color=IRON_BLACK, glow=shade(RUST, 0.05))


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_cursed_stocks",
        texture_width=128,
        texture_height=128,
    )

    # ---------------------------------------------------------------- base --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-11, 0, -8], [22, 3, 16],
        {
            "up": face(stone_brick()),
            "north": face(stone_brick(), share="plinth"),
            "south": face(stone_brick(), share="plinth"),
            "east": face(wood_frame(WOOD_MID, braces=1), share="plinth_side"),
            "west": face(wood_frame(WOOD_MID, braces=1), share="plinth_side"),
            "down": HIDDEN_FLAT(),
        },
    )
    base.cube(
        [-9, 3, -6], [18, 6, 5],  # the seat block
        {
            "up": face(wood_frame(WOOD_LIGHT, braces=2)),
            "north": face(boards, share="board_face"),
            "south": face(wood_frame(WOOD, braces=1), share="seat_back"),
            "east": face(wood_frame(WOOD_MID, braces=1), size=(4, 15), share="seat_end"),
            "west": face(wood_frame(WOOD_MID, braces=1), size=(4, 15), share="seat_end"),
            "down": HIDDEN_FLAT(),
        },
    )
    base.cube(
        [-9, 3, 2], [18, 10, 3],  # backrest
        {
            "up": HIDDEN_FLAT(),
            "north": face(skull(rgba("#7a7466"), dark=rgba("#514b43"))),
            "south": face(wood_frame(WOOD_DARK, braces=2), share="seat_back_wide"),
            "east": face(wood_frame(WOOD_MID, braces=1), size=(2, 10), share="backrest_end"),
            "west": face(wood_frame(WOOD_MID, braces=1), size=(2, 10), share="backrest_end"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ------------------------------------------------------- fixed lower board --
    lower = model.bone("board_lower", [0, 9, -3], parent="base")
    lower.cube(
        [-9, 9, -5], [18, 4, 11],
        {
            "up": face(boards),
            "north": face(boards, share="board_face"),
            "south": face(boards, share="board_face"),
            "east": face(wood_frame(WOOD_MID, braces=1), size=(3, 11), share="board_end_tall"),
            "west": face(wood_frame(WOOD_MID, braces=1), size=(3, 11), share="board_end_tall"),
            "down": HIDDEN_FLAT(),
        },
    )
    for column in (-7, -3, 1, 5):
        lower.cube(
            [column, 9, -5], [2, 4, 2],
            {
                "up": HIDDEN_FLAT(),
                "north": face(notch),
                "south": face(notch, share="notch"),
                "east": HIDDEN_FLAT(),
                "west": HIDDEN_FLAT(),
                "down": HIDDEN_FLAT(),
            },
        )

    # ------------------------------------------------------ hinged upper board --
    upper = model.bone("board_upper", [0, 13, -5.0], parent="base")
    upper.cube(
        [-9, 13, -4], [18, 3, 9],
        {
            "up": face(boards),
            "north": face(boards, share="board_face"),
            "south": face(boards, share="board_face"),
            "east": face(wood_frame(WOOD_MID, braces=1), size=(3, 11), share="board_end"),
            "west": face(wood_frame(WOOD_MID, braces=1), size=(3, 11), share="board_end"),
            "down": face(boards, share="board_face"),
        },
    )
    lock_bar = model.bone("lock_bar", [0, 15, -6], parent="board_upper")
    lock_bar.cube(
        [-2, 14, -6], [4, 2, 2],
        {
            "up": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False)),
            "north": face(steel_panel(STEEL, bands=1, seams=1, rivets=False)),
            "south": face(steel_panel(STEEL_DARK, bands=1, seams=1, rivets=False), share="lock_back"),
            "east": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), share="lock_side"),
            "west": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), share="lock_side"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- crank --
    crank = model.bone("crank", [13.5, 8, -3], parent="base")
    crank.cube(
        [9, 7, -4], [4.5, 2, 2],  # axle
        {
            "up": face(steel_panel(STEEL_MID, bands=1, seams=1, rust=0.3)),
            "north": HIDDEN_FLAT(),
            "south": HIDDEN_FLAT(),
            "east": HIDDEN_FLAT(),
            "west": HIDDEN_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    crank.cube(
        [13, 2.5, -8.5], [1, 11, 11],  # wheel in the YZ plane
        {
            "up": HIDDEN_FLAT(),
            "north": HIDDEN_FLAT(),
            "south": HIDDEN_FLAT(),
            "east": face(spoked_wheel(STEEL, light=STEEL_HIGHLIGHT)),
            "west": face(spoked_wheel(STEEL, light=STEEL_HIGHLIGHT), share="wheel"),
            "down": HIDDEN_FLAT(),
        },
    )
    crank.cube(
        [12, 12, 1], [2, 2, 4],  # handle
        {
            "up": face(steel_panel(STEEL_LIGHT, bands=1, seams=1, rivets=False)),
            "north": HIDDEN_FLAT(),
            "south": HIDDEN_FLAT(),
            "east": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="handle_tip"),
            "west": HIDDEN_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------- weight + chains --
    weight = model.bone("weight", [0, 4, 7], parent="base")
    weight.cube(
        [-4, 1, 8], [8, 5, 5],
        {
            "up": face(chained_weight),
            "north": face(chained_weight, share="weight_face"),
            "south": face(chained_weight, share="weight_face"),
            "east": face(chained_weight, share="weight_face"),
            "west": face(chained_weight, share="weight_face"),
            "down": HIDDEN_FLAT(),
        },
    )
    for side, column in (("left", -7), ("right", 6)):
        chain = model.bone(f"chain_{side}", [column + 0.5, 6, 8], parent="base")
        chain.cube(
            [column, 4, 8], [1, 4, 1],
            {
                "up": face(rope_coil),
                "north": face(rope_coil, share="rope"),
                "south": face(rope_coil, share="rope"),
                "east": face(rope_coil, share="rope"),
                "west": face(rope_coil, share="rope"),
                "down": face(rope_coil, share="rope"),
            },
        )

    # ----------------------------------------------------------- wear plates --
    wear_1 = model.bone("wear_1_board", [0, 16, -8], parent="board_upper")
    wear_1.cube(
        [-7, 16, -8], [8, 1, 4],
        {
            "up": face(cracked_timber(11, 4)),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_2 = model.bone("wear_2_flank", [13, 6, 0], parent="base")
    wear_2.cube(
        [12, 4, -6], [1, 8, 9],
        {
            "up": CLEAR_FLAT(),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": face(cracked_timber(12, 5)),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_3 = model.bone("wear_3_plinth", [0, 3, 0], parent="base")
    wear_3.cube(
        [-10.5, 3, -7.5], [21, 1, 5],
        {
            "up": face(cracked_timber(13, 6)),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )

    return scale_device(DeviceArt(
        slug="cursed_stocks",
        display_name="Cursed Stocks",
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
        _torture(1.0, "animation.cc_cursed_stocks.torture", 220),
        _torture(0.7, "animation.cc_cursed_stocks.torture_high", 420),
        _strain(),
        _burst(),
        _open(),
        _released(),
        _broken(),
    ]


def _board(animation: Animation, times_values) -> None:
    for time, angle in times_values:
        animation.key("board_upper", "rotation", time, (angle, 0, 0))


def _crank(animation: Animation, times_values) -> None:
    """The crank wheel turns about X (its axle); the weight only sways."""
    for time, angle in times_values:
        animation.key("crank", "rotation", time, (angle, 0, 0))
        animation.key("weight", "rotation", time, (0, 0, angle * 0.02))


def _idle() -> Animation:
    idle = Animation("animation.cc_cursed_stocks.idle", 3.6, loop=True)
    _board(idle, ((0.0, BOARD_OPEN), (1.4, BOARD_OPEN - 2.5), (2.6, BOARD_OPEN + 1.5), (3.6, BOARD_OPEN)))
    _crank(idle, ((0.0, 0), (3.6, 0)))
    for time, angle in ((0.0, 0), (1.8, 1.4), (3.6, 0)):
        idle.key("chain_left", "rotation", time, (angle, 0, 0))
        idle.key("chain_right", "rotation", time, (-angle, 0, 0))
    for time, y in ((0.0, 0), (1.8, -0.25), (3.6, 0)):
        idle.key("weight", "position", time, (0, y, 0))
    return idle


def _detect() -> Animation:
    detect = Animation("animation.cc_cursed_stocks.detect", CAPTURE_DELAY, loop=True)
    _board(detect, ((0.0, BOARD_OPEN), (CAPTURE_DELAY, BOARD_LIFTED)))
    _crank(detect, ((0.0, 0), (CAPTURE_DELAY, 34)))
    detect.key("lock_bar", "position", 0.0, (0, 0, 0))
    detect.key("lock_bar", "position", CAPTURE_DELAY, (0, 1.2, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        detect.key(bone, "rotation", 0.0, (0, 0, 0))
        detect.key(bone, "rotation", CAPTURE_DELAY * 0.55, (7 * sign, 0, 2 * sign))
        detect.key(bone, "rotation", CAPTURE_DELAY, (0, 0, 0))
    return detect


def _close() -> Animation:
    close = Animation("animation.cc_cursed_stocks.close", CLOSE_DURATION, loop=False)
    _board(close, ((0.0, BOARD_LIFTED), (0.42, 6), (0.6, -3), (0.78, 0), (CLOSE_DURATION, BOARD_CLOSED)))
    _crank(close, ((0.0, 34), (0.7, 96), (CLOSE_DURATION, 104)))
    close.key("lock_bar", "position", 0.0, (0, 1.2, 0))
    close.key("lock_bar", "position", 0.5, (0, 0, 0))
    close.key("lock_bar", "position", CLOSE_DURATION, (0, 0, 0))
    close.key("base", "rotation", 0.0, (0, 0, 0))
    close.key("base", "rotation", 0.45, (0, 0, -1.8))
    close.key("base", "rotation", 0.75, (0, 0, 1.2))
    close.key("base", "rotation", CLOSE_DURATION, (0, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        close.key(bone, "rotation", 0.0, (0, 0, 0))
        close.key(bone, "rotation", 0.3, (-9 * sign, 0, -3 * sign))
        close.key(bone, "rotation", 0.8, (4 * sign, 0, 0))
        close.key(bone, "rotation", CLOSE_DURATION, (0, 0, 0))
    return close


def _closed() -> Animation:
    closed = Animation("animation.cc_cursed_stocks.closed", CLOSED_PAUSE, loop=True)
    _board(closed, ((0.0, 0), (0.2, -1.2), (0.5, 0)))
    _crank(closed, ((0.0, 104), (0.5, 104)))
    closed.key("lock_bar", "position", 0.0, (0, 0, 0))
    closed.key("lock_bar", "position", 0.5, (0, 0, 0))
    return closed


def _torture(amplitude: float, identifier: str, spin: float) -> Animation:
    torture = Animation(identifier, TORTURE_INTERVAL, loop=True)
    _board(torture, ((0.0, 0), (0.3 * amplitude, -2.2 * amplitude), (0.8 * amplitude, 2.4 * amplitude),
                     (1.4 * amplitude, 0), (TORTURE_INTERVAL, 0)))
    _crank(torture, ((0.0, 104), (TORTURE_INTERVAL, 104 + spin)))
    for time, angle in ((0.0, 0), (0.35 * amplitude, 2.6 * amplitude), (0.9 * amplitude, -2.2 * amplitude),
                        (TORTURE_INTERVAL, 0)):
        torture.key("base", "rotation", time, (0, 0, angle))
    torture.key("board_lower", "position", 0.0, (0, 0, 0))
    torture.key("board_lower", "position", 0.4 * amplitude, (0, 0.3 * amplitude, 0))
    torture.key("board_lower", "position", TORTURE_INTERVAL, (0, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        torture.key(bone, "rotation", 0.0, (0, 0, 0))
        torture.key(bone, "rotation", 0.4 * amplitude, (10 * amplitude * sign, 0, 3 * sign))
        torture.key(bone, "rotation", 1.0 * amplitude, (-6 * amplitude * sign, 0, -2 * sign))
        torture.key(bone, "rotation", TORTURE_INTERVAL, (0, 0, 0))
    return torture


def _strain() -> Animation:
    strain = Animation("animation.cc_cursed_stocks.strain", STRAIN_TIME, loop=False)
    _board(strain, ((0.0, 0), (0.09, -4.4), (0.19, 3.6), (0.3, -2.4), (0.45, 1.2), (STRAIN_TIME, 0)))
    strain.key("base", "position", 0.0, (0, 0, 0))
    strain.key("base", "position", 0.09, (0.4, 0, 0))
    strain.key("base", "position", 0.19, (-0.4, 0, 0))
    strain.key("base", "position", STRAIN_TIME, (0, 0, 0))
    return strain


def _burst() -> Animation:
    burst = Animation("animation.cc_cursed_stocks.burst", BURST_TIME, loop=False)
    burst.key("base", "position", 0.0, (0, 0, 0))
    burst.key("base", "position", 0.1, (0, 0.45, 0))
    burst.key("base", "position", BURST_TIME, (0, 0, 0))
    _board(burst, ((0.0, 0), (0.1, -8), (0.3, 3), (BURST_TIME, 0)))
    _crank(burst, ((0.0, 104), (BURST_TIME, 168)))
    return burst


def _open() -> Animation:
    opened = Animation("animation.cc_cursed_stocks.open", RELEASE_TIME + 0.5, loop=False)
    end = RELEASE_TIME + 0.5
    _board(opened, ((0.0, 0), (0.35, -34), (0.65, -58), (0.9, -40), (end, BOARD_OPEN)))
    _crank(opened, ((0.0, 104), (end, 30)))
    opened.key("lock_bar", "position", 0.0, (0, 0, 0))
    opened.key("lock_bar", "position", 0.4, (0, 1.6, 0))
    opened.key("lock_bar", "position", end, (0, 1.2, 0))
    return opened


def _released() -> Animation:
    released = Animation("animation.cc_cursed_stocks.released", RELEASE_TIME, loop=False)
    _board(released, ((0.0, BOARD_OPEN), (0.35, BOARD_OPEN - 3), (0.7, BOARD_OPEN + 2), (RELEASE_TIME, BOARD_OPEN)))
    _crank(released, ((0.0, 30), (RELEASE_TIME, 0)))
    return released


def _broken() -> Animation:
    broken = Animation("animation.cc_cursed_stocks.broken", BROKEN_TIME, loop="hold_on_last_frame")
    _board(broken, ((0.0, 0), (0.7, -22), (BROKEN_TIME, 76)))
    broken.key("board_upper", "position", 0.0, (0, 0, 0))
    broken.key("board_upper", "position", 1.0, (0, -2, 1))
    broken.key("board_upper", "position", BROKEN_TIME, (0, -3.5, 2.4))
    broken.key("board_lower", "rotation", 0.0, (0, 0, 0))
    broken.key("board_lower", "rotation", 0.9, (6, 0, -4))
    broken.key("board_lower", "rotation", BROKEN_TIME, (9, 0, -6))
    broken.key("base", "rotation", 0.0, (0, 0, 0))
    broken.key("base", "rotation", BROKEN_TIME, (0, 0, 3.5))
    broken.key("crank", "rotation", 0.0, (104, 0, 0))
    broken.key("crank", "rotation", BROKEN_TIME, (74, 0, 0))
    return broken
