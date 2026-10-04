"""Cursed Stocks — pillory with a slamming board, clanking chains, and a lock.

Layout (model space, X east / Y up / Z south, 1 unit = 1 pixel):
the offender's tile is empty; the shafts leave crosswise from the block edges,
so the head and both hands are locked at the front of a waist-high platform.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    GOLD,
    IRON_BLACK,
    ROPE,
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
    steel_plate,
)
from model import Face, Model
from pipeline import DeviceArt
from _kit import finalize, flat_face, shared_face

CAPTURE_DELAY = 0.75
CLOSE_DURATION = 0.8
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 4.0
RELEASE_TIME = 0.8
BROKEN_TIME = 1.4


def _board(upper: bool):
    """Plank board with three clamped shafts; the holes are carved into the wood."""

    def paint(painter) -> None:
        planks(WOOD, light=WOOD_LIGHT, dark=WOOD_DARK, count=2, knots=2)(painter)
        width, height = painter.rect.width, painter.rect.height
        # Iron strapping across the ends.
        for column in (0, width - 2):
            painter.box(column, 0, 2, height, STEEL_DARK)
            painter.box(column, 0, 1, height, STEEL)
            painter.vline(column, 0, height, STEEL_LIGHT)
        # The three shafts: centre (head) and both flanks (hands).
        for index, ratio in enumerate((0.5, 0.2, 0.8)):
            shaft_column = int(width * ratio) - 1
            for offset in range(2):
                column = min(width - 1, max(0, shaft_column + offset))
                painter.vline(column, 0, height, IRON_BLACK)
                painter.vline(min(width - 1, column + 1), 0, height, RUST if upper else IRON_BLACK)
        painter.bevel(WOOD_LIGHT, WOOD_DARK, alpha=150)

    return paint


def _board_split():
    """Fixed lower board: half of each shaft is carved out of its top edge."""

    def paint(painter) -> None:
        planks(WOOD, light=WOOD_LIGHT, dark=WOOD_DARK, count=2, knots=2)(painter)
        width, height = painter.rect.width, painter.rect.height
        for column in (0, width - 2):
            painter.box(column, 0, 2, height, STEEL_DARK)
            painter.box(column, 0, 1, height, STEEL)
        for ratio in (0.5, 0.2, 0.8):
            center = int(width * ratio)
            painter.box(max(0, center - 1), 0, 2, max(2, height // 2 + 1), IRON_BLACK)
            painter.px(max(0, center - 1), max(0, height // 2), RUST)
        painter.bevel(WOOD_LIGHT, WOOD_DARK, alpha=150)

    return paint


def _padlock():
    def paint(painter) -> None:
        painter.fill(STEEL_DARK)
        width, height = painter.rect.width, painter.rect.height
        painter.gradient_v(STEEL, STEEL_DARK)
        painter.box(0, 0, width, 1, STEEL_HIGHLIGHT)
        painter.box(0, height - 1, width, 1, IRON_BLACK)
        painter.px(width // 2, height // 2, IRON_BLACK)
        painter.px(width // 2, height // 2 + 1, GOLD)
        painter.bevel(STEEL_LIGHT, IRON_BLACK, alpha=170)

    return paint


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_cursed_stocks",
        texture_width=64,
        texture_height=128,
        visible_bounds=(2.0, 1.8),
        visible_offset=(0.0, 0.9, 0.0),
    )

    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-7, 0, -7], [14, 4, 14],
        {
            "up": shared_face(planks(WOOD, light=WOOD_LIGHT, dark=WOOD_DARK, count=4, knots=3), "stocks_floor"),
            # The slab is 14 wide, 4 tall and 14 deep, so all four side faces
            # are 14x4 while the top and bottom faces are 14x14.
            "north": shared_face(planks(WOOD_DARK, count=2, knots=1), "stocks_side"),
            "south": shared_face(planks(WOOD_DARK, count=2, knots=1), "stocks_side"),
            "east": shared_face(planks(WOOD_DARK, count=2, knots=1), "stocks_side"),
            "west": shared_face(planks(WOOD_DARK, count=2, knots=1), "stocks_side"),
            "down": shared_face(planks(WOOD_DARK, count=4, knots=2), "stocks_under"),
        },
    )
    # Upright post behind the offender.
    base.cube(
        [-2, 4, 4], [4, 12, 4],
        {
            "north": shared_face(planks(WOOD, count=2, knots=2), "stocks_post"),
            "south": shared_face(planks(WOOD, count=2, knots=2), "stocks_post"),
            "east": shared_face(planks(WOOD, count=2, knots=2), "stocks_post_side"),
            "west": shared_face(planks(WOOD, count=2, knots=2), "stocks_post_side"),
            "up": flat_face(WOOD_DARK, "wood_dark"),
            "down": flat_face(WOOD_DARK, "wood_dark"),
        },
    )

    # Fixed lower board, planted on the post.
    lower = model.bone("board_lower", [0, 12, 3], parent="base")
    lower.cube(
        [-9, 12, -2], [18, 3, 5],
        {
            "up": shared_face(_board_split(), "stocks_lower_top"),
            "north": shared_face(_board(False), "stocks_lower_front"),
            "south": shared_face(planks(WOOD_DARK, count=2, knots=1), "stocks_board_back"),
            "east": flat_face(WOOD_DARK, "wood_dark"),
            "west": flat_face(WOOD_DARK, "wood_dark"),
            "down": shared_face(planks(WOOD_DARK, count=3, knots=1), "stocks_board_under"),
        },
    )

    # Hinged upper board: drops onto the lower one and pins the captive.
    upper = model.bone("board_upper", [0, 15, 3], parent="base")
    upper.cube(
        [-9, 15, -2], [18, 3, 5],
        {
            "down": shared_face(_board_split(), "stocks_upper_bottom", flip_v=True),
            "north": shared_face(_board(True), "stocks_upper_front"),
            "south": shared_face(planks(WOOD_DARK, count=2, knots=1), "stocks_board_back"),
            "east": flat_face(WOOD_DARK, "wood_dark"),
            "west": flat_face(WOOD_DARK, "wood_dark"),
            "up": shared_face(planks(WOOD_LIGHT, count=2, knots=1), "stocks_upper_top"),
        },
    )
    # Hinge barrels at the post.
    for column in (-9, 7):
        upper.cube(
            [column, 16, 2], [2, 1, 2],
            {
                "north": flat_face(STEEL_DARK, "steel_dark"),
                "south": flat_face(STEEL_DARK, "steel_dark"),
                "east": shared_face(steel_plate(STEEL, rivets=False), "stocks_hinge"),
                "west": shared_face(steel_plate(STEEL, rivets=False), "stocks_hinge"),
                "up": shared_face(steel_plate(STEEL_LIGHT, rivets=False), "stocks_hinge_top"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Padlock hanging on the front lip.
    upper.cube(
        [-2, 11, -3], [4, 4, 1],
        {
            "north": shared_face(_padlock(), "stocks_lock"),
            "south": flat_face(IRON_BLACK, "iron_black"),
            "east": flat_face(STEEL_DARK, "steel_dark"),
            "west": flat_face(STEEL_DARK, "steel_dark"),
            "up": flat_face(STEEL_DARK, "steel_dark"),
            "down": flat_face(IRON_BLACK, "iron_black"),
        },
    )

    # Chains that drag from the board ends and swing while the device works.
    chain_paint = chain(STEEL, dark=IRON_BLACK, light=STEEL_LIGHT)
    for name, column in (("chain_left", -9), ("chain_right", 8)):
        bone = model.bone(name, [column + 0.5, 15, 1.5], parent="board_upper")
        bone.cube(
            [column, 5, 1], [1, 10, 1],
            {
                "north": shared_face(chain_paint, "stocks_chain"),
                "south": shared_face(chain_paint, "stocks_chain"),
                "east": shared_face(chain_paint, "stocks_chain"),
                "west": shared_face(chain_paint, "stocks_chain"),
                "up": flat_face(IRON_BLACK, "iron_black"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )

    # A straw handful left behind, a nod to the "board" flavour.
    straw = model.bone("straw", [0, 4, -4], parent="base")
    straw.cube(
        [-5, 4, -6], [10, 1, 3],
        {
            "up": shared_face(planks(ROPE, light=(214, 186, 120, 255), dark=(140, 112, 60, 255), count=3, knots=0), "stocks_straw"),
            "north": flat_face((150, 122, 70, 255), "straw_side"),
            "south": flat_face((150, 122, 70, 255), "straw_side"),
            "east": flat_face((140, 112, 62, 255), "straw_side"),
            "west": flat_face((140, 112, 62, 255), "straw_side"),
            "down": flat_face((120, 96, 52, 255), "straw_side"),
        },
    )

    animations = _animations()
    art = DeviceArt(
        slug="cursed_stocks",
        display_name="Cursed Stocks",
        model=model,
        animations=animations,
        state_animations={},
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:basic_crit_particle",
    )
    return finalize(art)


def _animations() -> list[Animation]:
    animations: list[Animation] = []

    idle = Animation("animation.cc_cursed_stocks.idle", 4.0, loop=True)
    idle.key("board_upper", "rotation", 0.0, (-2, 0, 0))
    idle.key("board_upper", "rotation", 2.0, (1.2, 0, 0))
    idle.key("board_upper", "rotation", 4.0, (-2, 0, 0))
    idle.key("chain_left", "rotation", 0.0, (0, 0, 0))
    idle.key("chain_left", "rotation", 2.0, (0, 0, 5))
    idle.key("chain_left", "rotation", 4.0, (0, 0, 0))
    idle.key("chain_right", "rotation", 0.0, (0, 0, 0))
    idle.key("chain_right", "rotation", 2.0, (0, 0, -5))
    idle.key("chain_right", "rotation", 4.0, (0, 0, 0))
    animations.append(idle)

    detect = Animation("animation.cc_cursed_stocks.detect", CAPTURE_DELAY, loop=True)
    detect.key("board_upper", "rotation", 0.0, (-2, 0, 0))
    detect.key("board_upper", "rotation", 0.35, (46, 0, 0))
    detect.key("board_upper", "rotation", 0.75, (40, 0, 0))
    detect.key("chain_left", "rotation", 0.0, (0, 0, 0))
    detect.key("chain_left", "rotation", 0.35, (0, 0, 14))
    detect.key("chain_left", "rotation", 0.75, (0, 0, 8))
    detect.key("chain_right", "rotation", 0.0, (0, 0, 0))
    detect.key("chain_right", "rotation", 0.35, (0, 0, -14))
    detect.key("chain_right", "rotation", 0.75, (0, 0, -8))
    animations.append(detect)

    close = Animation("animation.cc_cursed_stocks.close", CLOSE_DURATION, loop=False)
    close.key("board_upper", "rotation", 0.0, (40, 0, 0))
    close.key("board_upper", "rotation", 0.3, (-5, 0, 0))
    close.key("board_upper", "rotation", 0.45, (2.5, 0, 0))
    close.key("board_upper", "rotation", 0.6, (0, 0, 0))
    close.key("board_upper", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("chain_left", "rotation", 0.0, (0, 0, 8))
    close.key("chain_left", "rotation", 0.35, (0, 0, 22))
    close.key("chain_left", "rotation", 0.7, (0, 0, -6))
    close.key("chain_left", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("chain_right", "rotation", 0.0, (0, 0, -8))
    close.key("chain_right", "rotation", 0.35, (0, 0, -22))
    close.key("chain_right", "rotation", 0.7, (0, 0, 6))
    close.key("chain_right", "rotation", CLOSE_DURATION, (0, 0, 0))
    animations.append(close)

    closed = Animation("animation.cc_cursed_stocks.closed", CLOSED_PAUSE, loop=True)
    closed.key("board_upper", "rotation", 0.0, (0, 0, 0))
    closed.key("board_upper", "rotation", 0.25, (0.8, 0, 0))
    closed.key("board_upper", "rotation", 0.5, (0, 0, 0))
    animations.append(closed)

    torture = Animation("animation.cc_cursed_stocks.torture", TORTURE_INTERVAL, loop=True)
    for time, angle in ((0.0, 0), (0.6, 0), (0.72, 3.5), (0.84, -3), (0.96, 2.4), (1.08, -1.6), (1.2, 0), (3.0, 0), (3.1, 2), (3.3, -1.6), (3.6, 0), (4.0, 0)):
        torture.key("base", "rotation", time, (0, 0, angle))
    torture.key("base", "position", 0.0, (0, 0, 0))
    torture.key("base", "position", 0.72, (0.5, 0, 0))
    torture.key("base", "position", 0.9, (-0.5, 0, 0))
    torture.key("base", "position", 1.2, (0, 0, 0))
    torture.key("base", "position", 4.0, (0, 0, 0))
    torture.key("board_upper", "rotation", 0.0, (0, 0, 0))
    torture.key("board_upper", "rotation", 0.5, (-3.5, 0, 0))
    torture.key("board_upper", "rotation", 1.0, (0, 0, 0))
    torture.key("board_upper", "rotation", 3.0, (0, 0, 0))
    torture.key("board_upper", "rotation", 3.4, (-2, 0, 0))
    torture.key("board_upper", "rotation", 4.0, (0, 0, 0))
    torture.key("chain_left", "rotation", 0.0, (0, 0, 0))
    torture.key("chain_left", "rotation", 0.6, (0, 0, 10))
    torture.key("chain_left", "rotation", 1.4, (0, 0, -4))
    torture.key("chain_left", "rotation", 2.2, (0, 0, 0))
    torture.key("chain_left", "rotation", 4.0, (0, 0, 0))
    torture.key("chain_right", "rotation", 0.0, (0, 0, 0))
    torture.key("chain_right", "rotation", 0.6, (0, 0, -10))
    torture.key("chain_right", "rotation", 1.4, (0, 0, 4))
    torture.key("chain_right", "rotation", 2.2, (0, 0, 0))
    torture.key("chain_right", "rotation", 4.0, (0, 0, 0))
    animations.append(torture)

    strain = Animation("animation.cc_cursed_stocks.strain", 0.6, loop=False)
    for time, angle in ((0.0, 0), (0.08, 6), (0.16, -5), (0.26, 4), (0.36, -3), (0.48, 1.5), (0.6, 0)):
        strain.key("base", "rotation", time, (0, 0, angle))
    strain.key("board_upper", "rotation", 0.0, (0, 0, 0))
    strain.key("board_upper", "rotation", 0.1, (-4.5, 0, 0))
    strain.key("board_upper", "rotation", 0.28, (1.8, 0, 0))
    strain.key("board_upper", "rotation", 0.5, (0, 0, 0))
    strain.key("board_upper", "rotation", 0.6, (0, 0, 0))
    animations.append(strain)

    open_animation = Animation("animation.cc_cursed_stocks.open", RELEASE_TIME + 0.3, loop=False)
    open_animation.key("board_upper", "rotation", 0.0, (0, 0, 0))
    open_animation.key("board_upper", "rotation", 0.3, (3, 0, 0))
    open_animation.key("board_upper", "rotation", 0.6, (58, 0, 0))
    open_animation.key("board_upper", "rotation", RELEASE_TIME + 0.3, (52, 0, 0))
    open_animation.key("chain_left", "rotation", 0.0, (0, 0, 0))
    open_animation.key("chain_left", "rotation", 0.5, (0, 0, 18))
    open_animation.key("chain_left", "rotation", RELEASE_TIME + 0.3, (0, 0, 6))
    open_animation.key("chain_right", "rotation", 0.0, (0, 0, 0))
    open_animation.key("chain_right", "rotation", 0.5, (0, 0, -18))
    open_animation.key("chain_right", "rotation", RELEASE_TIME + 0.3, (0, 0, -6))
    animations.append(open_animation)

    released = Animation("animation.cc_cursed_stocks.released", RELEASE_TIME, loop=False)
    released.key("board_upper", "rotation", 0.0, (52, 0, 0))
    released.key("board_upper", "rotation", 0.4, (44, 0, 0))
    released.key("board_upper", "rotation", RELEASE_TIME, (47, 0, 0))
    released.key("chain_left", "rotation", 0.0, (0, 0, 6))
    released.key("chain_left", "rotation", RELEASE_TIME, (0, 0, 0))
    released.key("chain_right", "rotation", 0.0, (0, 0, -6))
    released.key("chain_right", "rotation", RELEASE_TIME, (0, 0, 0))
    animations.append(released)

    broken = Animation("animation.cc_cursed_stocks.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("board_upper", "rotation", 0.0, (0, 0, 0))
    broken.key("board_upper", "rotation", 0.5, (-10, 0, 6))
    broken.key("board_upper", "rotation", 1.0, (-6, 0, 4))
    broken.key("board_upper", "rotation", BROKEN_TIME, (-7, 0, 5))
    broken.key("board_upper", "position", 0.0, (0, 0, 0))
    broken.key("board_upper", "position", 1.0, (0, -3, -1))
    broken.key("board_upper", "position", BROKEN_TIME, (0, -3, -1))
    broken.key("base", "rotation", 0.0, (0, 0, 0))
    broken.key("base", "rotation", 0.8, (-3, 0, 4))
    broken.key("base", "rotation", BROKEN_TIME, (-2, 0, 4))
    broken.key("chain_left", "rotation", 0.0, (0, 0, 0))
    broken.key("chain_left", "rotation", 0.6, (0, 0, 26))
    broken.key("chain_left", "rotation", BROKEN_TIME, (0, 0, 18))
    broken.key("chain_right", "rotation", 0.0, (0, 0, 0))
    broken.key("chain_right", "rotation", 0.6, (0, 0, -22))
    broken.key("chain_right", "rotation", BROKEN_TIME, (0, 0, -15))
    animations.append(broken)

    return animations
