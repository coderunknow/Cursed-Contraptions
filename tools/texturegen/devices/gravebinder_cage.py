"""Gravebinder Cage — a barred iron cage you can see your friends through.

v0.1.4 rebuild: a stone-slab plinth, four corner posts, genuinely transparent
bar walls (``entity_alphatest`` drops the gaps), a hinged barred door, a
rune-etched back plate with a skull, chains hanging from the roof ring, and
bars that visibly buckle as the cage is battered.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    BONE,
    BONE_DARK,
    IRON_BLACK,
    RUST,
    SOUL,
    SOUL_LIGHT,
    SOUL_PALE,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    STEEL_MID,
    bar_grid,
    cracks,
    flat,
    rune_band,
    skull,
    soul_glow,
    steel_panel,
    steel_plate,
    stone_brick,
)
from canvas import mix, rgba, shade
from model import Face, Model
from pipeline import DeviceArt, scale_device

CAPTURE_DELAY = 1.25
CLOSE_DURATION = 1.75
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 2.5
RELEASE_TIME = 1.0
BROKEN_TIME = 1.5
STRAIN_TIME = 0.7
BURST_TIME = 0.45

# World size: authored scale x1.4 (1 unit = 1/16 block) -> 2.1 blocks tall.
SCALE = 1.4

HIDDEN = rgba("#1a1d22")
GAP = rgba("#000000", 0)

DOOR_SHUT = 0.0
DOOR_OPEN = -96.0


def face(paint, **kwargs) -> Face:
    return Face(paint=paint, **kwargs)


def patch(color, key: str, size=(1, 1)) -> Face:
    return Face(paint=flat(color), size=size, share=f"flat:{key}")


HIDDEN_FLAT = lambda: patch(HIDDEN, "hidden")  # noqa: E731
DARK_FLAT = lambda: patch(IRON_BLACK, "iron_black")  # noqa: E731


def clear(painter) -> None:
    painter.clear()


CLEAR_FLAT = lambda: Face(paint=clear, size=(1, 1), share="flat:clear")  # noqa: E731


def back_plate(painter) -> None:
    """Rune-etched soul plate behind the captive."""
    rune_band(rgba("#2b2f38"), glow=shade(SOUL_LIGHT, -0.05), dark=IRON_BLACK)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.box(0, 0, width, 1, STEEL_DARK)
    painter.box(0, height - 1, width, 1, shade(STEEL_DARK, -0.2))
    painter.bevel(STEEL_MID, IRON_BLACK, alpha=130)


def door_plate(painter) -> None:
    """The cage door: a barred frame with a heavy lock boss."""
    width, height = painter.rect.width, painter.rect.height
    bar_grid(STEEL, light=STEEL_HIGHLIGHT, rails=2, spacing=max(2, width // 4), rust=0.4)(painter)
    painter.box(0, 0, width, 1, steel_mix(0.35))
    painter.box(0, height - 1, width, 1, shade(STEEL_DARK, -0.1))
    painter.box(0, 0, 1, height, shade(STEEL_LIGHT, -0.05))
    painter.box(width - 1, 0, 1, height, shade(STEEL_DARK, -0.1))
    boss = max(2, width // 5)
    painter.box(width // 2 - boss // 2, height // 2 - boss // 2, boss, boss, STEEL_MID)
    painter.box(width // 2 - boss // 2, height // 2 - boss // 2, boss, 1, STEEL_HIGHLIGHT)
    painter.px(width // 2, height // 2, IRON_BLACK)


def steel_mix(amount: float):
    return mix(STEEL, STEEL_HIGHLIGHT, amount)


def post(painter) -> None:
    """Corner post: riveted iron with rust running out of the joints."""
    steel_panel(STEEL_DARK, bands=4, seams=1, rust=0.5)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.vline(0, 0, height, shade(STEEL_MID, 0.1))
    painter.vline(max(0, width - 1), 0, height, IRON_BLACK)
    painter.bevel(STEEL_LIGHT, IRON_BLACK, alpha=140)


def chain_links(painter) -> None:
    width, height = painter.rect.width, painter.rect.height
    painter.clear()
    link = max(3, height // 6)
    for index in range(0, height, link):
        wide = (index // link) % 2 == 0
        left = 0 if wide or width < 3 else 1
        right = width if wide or width < 3 else width - 1
        for row in range(index, min(height, index + link)):
            painter.box(left, row, max(1, right - left), 1, shade(STEEL_MID, -0.12))
        painter.box(left, index, max(1, right - left), 1, STEEL_LIGHT)
        painter.box(left, min(height - 1, index + link - 1), max(1, right - left), 1, IRON_BLACK)


def cracked_iron(seed: int, count: int = 5):
    return cracks(seed, count=count, color=IRON_BLACK, glow=shade(RUST, 0.1))


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_gravebinder_cage",
        texture_width=128,
        texture_height=128,
    )

    # ---------------------------------------------------------------- base --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-12, 0, -11], [24, 3, 22],
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
        [-10, 3, -9], [20, 1, 18],  # cage floor
        {
            "up": face(steel_panel(STEEL_MID, bands=1, seams=4, rust=0.3)),
            "north": DARK_FLAT(),
            "south": DARK_FLAT(),
            "east": DARK_FLAT(),
            "west": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )

    # ------------------------------------------------------------- structure --
    frame = model.bone("frame", [0, 3, 0], parent="base")
    frame.cube(
        [-12, 3, -11], [2, 21, 2],  # corner posts
        {
            "up": DARK_FLAT(),
            "north": face(post, share="post"),
            "south": face(post, share="post"),
            "east": face(post, share="post"),
            "west": face(post, share="post"),
            "down": HIDDEN_FLAT(),
        },
    )
    frame.cube(
        [10, 3, -11], [2, 21, 2],
        {
            "up": DARK_FLAT(),
            "north": face(post, share="post"),
            "south": face(post, share="post"),
            "east": face(post, share="post"),
            "west": face(post, share="post"),
            "down": HIDDEN_FLAT(),
        },
    )
    frame.cube(
        [-12, 3, 9], [2, 21, 2],
        {
            "up": DARK_FLAT(),
            "north": face(post, share="post"),
            "south": face(post, share="post"),
            "east": face(post, share="post"),
            "west": face(post, share="post"),
            "down": HIDDEN_FLAT(),
        },
    )
    frame.cube(
        [10, 3, 9], [2, 21, 2],
        {
            "up": DARK_FLAT(),
            "north": face(post, share="post"),
            "south": face(post, share="post"),
            "east": face(post, share="post"),
            "west": face(post, share="post"),
            "down": HIDDEN_FLAT(),
        },
    )
    # Back wall: solid rune plate with a carved skull.
    frame.cube(
        [-10, 3, 10], [20, 21, 1],
        {
            "up": HIDDEN_FLAT(),
            "north": face(back_plate),
            "south": face(steel_panel(STEEL_DARK, bands=3, rust=0.5), share="cage_back"),
            "east": HIDDEN_FLAT(),
            "west": HIDDEN_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    frame.cube(
        [-4, 14, 9.6], [8, 9, 1],  # skull relief
        {
            "up": HIDDEN_FLAT(),
            "north": face(skull(BONE, dark=BONE_DARK, socket=IRON_BLACK)),
            "south": HIDDEN_FLAT(),
            "east": HIDDEN_FLAT(),
            "west": HIDDEN_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    # Side and front walls: transparent bar grids.
    bars = bar_grid(STEEL, light=STEEL_HIGHLIGHT, rails=3, spacing=4, rust=0.35)
    frame.cube(
        [-12, 3, -9], [1, 21, 18],  # left wall, barred
        {
            "up": HIDDEN_FLAT(), "north": HIDDEN_FLAT(), "south": HIDDEN_FLAT(),
            "east": HIDDEN_FLAT(), "west": face(bars, share="bars"), "down": HIDDEN_FLAT(),
        },
    )
    frame.cube(
        [11, 3, -9], [1, 21, 18],  # right wall, barred
        {
            "up": HIDDEN_FLAT(), "north": HIDDEN_FLAT(), "south": HIDDEN_FLAT(),
            "east": face(bars, share="bars"), "west": HIDDEN_FLAT(), "down": HIDDEN_FLAT(),
        },
    )
    # Roof: solid plate with a lifting ring on top.
    roof = model.bone("roof", [0, 24, 0], parent="frame")
    roof.cube(
        [-13, 24, -12], [26, 3, 24],
        {
            "up": face(steel_panel(STEEL, bands=2, seams=4, rust=0.35)),
            "north": face(steel_panel(STEEL_DARK, bands=2, rust=0.5), share="roof_edge"),
            "south": face(steel_panel(STEEL_DARK, bands=2, rust=0.5), share="roof_edge"),
            "east": face(steel_panel(STEEL_DARK, bands=2, rust=0.5), share="roof_edge"),
            "west": face(steel_panel(STEEL_DARK, bands=2, rust=0.5), share="roof_edge"),
            "down": HIDDEN_FLAT(),
        },
    )
    roof.cube(
        [-4, 27, -4], [8, 2, 8],  # cap
        {
            "up": face(steel_panel(STEEL_MID, bands=1, seams=2, rust=0.3)),
            "north": face(post, size=(8, 2), share="cap_side"),
            "south": face(post, size=(8, 2), share="cap_side"),
            "east": face(post, size=(8, 2), share="cap_side"),
            "west": face(post, size=(8, 2), share="cap_side"),
            "down": HIDDEN_FLAT(),
        },
    )
    ring = model.bone("ring", [0, 29, 0], parent="roof")
    ring.cube(
        [-3, 29, -1], [6, 1, 2],
        {
            "up": face(steel_panel(STEEL_LIGHT, bands=1, seams=1, rivets=False)),
            "north": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="ring_side"),
            "south": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="ring_side"),
            "east": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="ring_side"),
            "west": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False), share="ring_side"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ----------------------------------------------------------------- door --
    door = model.bone("door", [-10, 3, -10], parent="frame")
    door.cube(
        [-9, 3, -10], [19, 21, 1],
        {
            "up": HIDDEN_FLAT(),
            "north": face(door_plate),
            "south": face(bars, share="bars"),
            "east": HIDDEN_FLAT(),
            "west": HIDDEN_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    door.cube(
        [8, 3, -10.5], [2, 21, 2],  # door jamb
        {
            "up": DARK_FLAT(),
            "north": face(post, size=(2, 21), share="jamb_side"),
            "south": face(post, size=(2, 21), share="jamb_side"),
            "east": face(post, size=(2, 21), share="jamb_side"),
            "west": face(post, size=(2, 21), share="jamb_side"),
            "down": HIDDEN_FLAT(),
        },
    )
    lock = model.bone("lock", [6, 13, -11], parent="door")
    lock.cube(
        [4, 11, -11], [4, 5, 2],
        {
            "up": face(steel_panel(STEEL_LIGHT, bands=1, seams=1, rivets=False)),
            "north": face(steel_panel(STEEL, bands=1, seams=1, rivets=False)),
            "south": face(steel_panel(STEEL_DARK, bands=1, seams=1, rivets=False), share="lock_back"),
            "east": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False)),
            "west": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False)),
            "down": HIDDEN_FLAT(),
        },
    )

    # --------------------------------------------------------------- ember --
    ember = model.bone("ember", [0, 14, -2], parent="frame")
    ember.cube(
        [-1, 13, -3], [2, 2, 2],
        {
            "north": face(soul_glow(SOUL)),
            "south": face(soul_glow(SOUL), share="ember_back"),
            "east": face(soul_glow(SOUL), share="ember_back"),
            "west": face(soul_glow(SOUL), share="ember_back"),
            "up": face(soul_glow(SOUL_PALE, light=SOUL_PALE, pale=(255, 255, 255, 255))),
            "down": face(soul_glow(SOUL, light=SOUL, pale=SOUL_LIGHT), share="ember_down"),
        },
    )

    # -------------------------------------------------------------- chains --
    for side, column in (("left", -11), ("right", 10)):
        chain = model.bone(f"chain_{side}", [column + 0.5, 24, -10], parent="frame")
        chain.cube(
            [column, 18, -10], [1, 6, 1],
            {
                "up": DARK_FLAT(),
                "north": face(chain_links, share="links"),
                "south": face(chain_links, share="links"),
                "east": face(chain_links, share="links"),
                "west": face(chain_links, share="links"),
                "down": DARK_FLAT(),
            },
        )

    # ----------------------------------------------------------- wear plates --
    wear_1 = model.bone("wear_1_door", [0, 20, -12], parent="door")
    wear_1.cube(
        [-6, 18, -12], [11, 1, 4],
        {
            "up": CLEAR_FLAT(),
            "north": face(cracked_iron(21, 5)),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_2 = model.bone("wear_2_roof", [0, 27, 0], parent="roof")
    wear_2.cube(
        [-11, 27, -10], [22, 1, 7],
        {
            "up": face(cracked_iron(22, 6)),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_3 = model.bone("wear_3_post", [11, 14, -11], parent="frame")
    wear_3.cube(
        [11, 8, -11], [1, 13, 3],
        {
            "up": CLEAR_FLAT(),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": face(cracked_iron(23, 4)),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )

    return scale_device(DeviceArt(
        slug="gravebinder_cage",
        display_name="Gravebinder Cage",
        model=model,
        animations=animations(),
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:soul_particle",
    ), SCALE)


# --------------------------------------------------------------- animations --
def animations() -> list[Animation]:
    return [
        _idle(),
        _detect(),
        _close(),
        _closed(),
        _torture(1.0, "animation.cc_gravebinder_cage.torture"),
        _torture(0.66, "animation.cc_gravebinder_cage.torture_high"),
        _strain(),
        _burst(),
        _open(),
        _released(),
        _broken(),
    ]


def _door(animation: Animation, values) -> None:
    for time, angle in values:
        animation.key("door", "rotation", time, (0, angle, 0))


def _idle() -> Animation:
    idle = Animation("animation.cc_gravebinder_cage.idle", 4.4, loop=True)
    _door(idle, ((0.0, DOOR_OPEN), (2.0, DOOR_OPEN - 2.4), (3.2, DOOR_OPEN + 1.6), (4.4, DOOR_OPEN)))
    for time, angle in ((0.0, 2.4), (2.2, -2.4), (4.4, 2.4)):
        idle.key("chain_left", "rotation", time, (angle, 0, angle * 0.4))
        idle.key("chain_right", "rotation", time, (-angle, 0, -angle * 0.4))
    for time, y in ((0.0, 0), (2.2, -0.4), (4.4, 0)):
        idle.key("ring", "position", time, (0, y, 0))
    idle.key("ring", "rotation", 0.0, (0, 0, 0))
    idle.key("ring", "rotation", 4.4, (0, 360, 0))
    idle.key("ember", "scale", 0.0, (0, 0, 0))
    idle.key("ember", "scale", 4.4, (0, 0, 0))
    return idle


def _detect() -> Animation:
    detect = Animation("animation.cc_gravebinder_cage.detect", CAPTURE_DELAY, loop=True)
    _door(detect, ((0.0, DOOR_OPEN), (CAPTURE_DELAY, DOOR_OPEN + 8)))
    detect.key("ember", "scale", 0.0, (0, 0, 0))
    detect.key("ember", "scale", CAPTURE_DELAY * 0.6, (0.7, 0.7, 0.7))
    detect.key("ember", "scale", CAPTURE_DELAY, (1, 1, 1))
    detect.key("ember", "position", 0.0, (0, 0, 0))
    detect.key("ember", "position", CAPTURE_DELAY, (0, 1.6, 3))
    detect.key("ring", "rotation", 0.0, (0, 0, 0))
    detect.key("ring", "rotation", CAPTURE_DELAY, (0, 120, 0))
    detect.key("lock", "position", 0.0, (0, 0, 0))
    detect.key("lock", "position", CAPTURE_DELAY, (0, 1.4, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        detect.key(bone, "rotation", 0.0, (0, 0, 0))
        detect.key(bone, "rotation", CAPTURE_DELAY * 0.5, (9 * sign, 0, 0))
        detect.key(bone, "rotation", CAPTURE_DELAY, (-3 * sign, 0, 0))
    return detect


def _close() -> Animation:
    close = Animation("animation.cc_gravebinder_cage.close", CLOSE_DURATION, loop=False)
    _door(close, ((0.0, DOOR_OPEN + 8), (0.35, -14), (0.6, 5), (0.85, -2), (1.1, 0), (CLOSE_DURATION, DOOR_SHUT)))
    close.key("frame", "rotation", 0.0, (0, 0, 0))
    close.key("frame", "rotation", 0.5, (0, 0, -1.6))
    close.key("frame", "rotation", 0.85, (0, 0, 1.1))
    close.key("frame", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("lock", "position", 0.0, (0, 1.4, 0))
    close.key("lock", "position", 0.55, (0, 0, 0))
    close.key("lock", "position", CLOSE_DURATION, (0, 0, 0))
    close.key("ember", "scale", 0.0, (1, 1, 1))
    close.key("ember", "scale", 0.5, (1.5, 1.5, 1.5))
    close.key("ember", "scale", 1.05, (0.2, 0.2, 0.2))
    close.key("ember", "scale", CLOSE_DURATION, (0.2, 0.2, 0.2))
    close.key("ring", "rotation", 0.0, (0, 120, 0))
    close.key("ring", "rotation", CLOSE_DURATION, (0, 300, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        close.key(bone, "rotation", 0.0, (-3 * sign, 0, 0))
        close.key(bone, "rotation", 0.4, (14 * sign, 0, 5 * sign))
        close.key(bone, "rotation", 0.9, (-6 * sign, 0, -2 * sign))
        close.key(bone, "rotation", CLOSE_DURATION, (0, 0, 0))
    return close


def _closed() -> Animation:
    closed = Animation("animation.cc_gravebinder_cage.closed", CLOSED_PAUSE, loop=True)
    _door(closed, ((0.0, 0), (0.22, -1.4), (0.5, 0)))
    closed.key("ember", "scale", 0.0, (0.2, 0.2, 0.2))
    closed.key("ember", "scale", 0.28, (0.55, 0.55, 0.55))
    closed.key("ember", "scale", 0.5, (0.2, 0.2, 0.2))
    closed.key("ring", "rotation", 0.0, (0, 300, 0))
    closed.key("ring", "rotation", 0.5, (0, 306, 0))
    return closed


def _torture(amplitude: float, identifier: str) -> Animation:
    torture = Animation(identifier, TORTURE_INTERVAL, loop=True)
    for time, angle in ((0.0, 0), (0.22 * amplitude, 2.6 * amplitude), (0.5 * amplitude, -2.2 * amplitude),
                        (0.9 * amplitude, 1.4 * amplitude), (TORTURE_INTERVAL, 0)):
        torture.key("frame", "rotation", time, (0, 0, angle))
    torture.key("frame", "position", 0.0, (0, 0, 0))
    torture.key("frame", "position", 0.3 * amplitude, (0.5 * amplitude, 0, 0))
    torture.key("frame", "position", 0.7 * amplitude, (-0.5 * amplitude, 0, 0))
    torture.key("frame", "position", TORTURE_INTERVAL, (0, 0, 0))
    _door(torture, ((0.0, 0), (0.35, -2.6 * amplitude), (0.85, 1.2 * amplitude), (1.3, 0), (TORTURE_INTERVAL, 0)))
    torture.key("ring", "rotation", 0.0, (0, 300, 0))
    torture.key("ring", "rotation", TORTURE_INTERVAL, (0, 300 + 220 * amplitude, 0))
    torture.key("ember", "scale", 0.0, (0.6, 0.6, 0.6))
    torture.key("ember", "scale", TORTURE_INTERVAL * 0.5, (1.1, 1.1, 1.1))
    torture.key("ember", "scale", TORTURE_INTERVAL, (0.6, 0.6, 0.6))
    torture.key("ember", "rotation", 0.0, (0, 0, -10))
    torture.key("ember", "rotation", TORTURE_INTERVAL * 0.5, (0, 0, 12))
    torture.key("ember", "rotation", TORTURE_INTERVAL, (0, 0, -10))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        torture.key(bone, "rotation", 0.0, (0, 0, 0))
        torture.key(bone, "rotation", 0.3 * amplitude, (12 * amplitude * sign, 0, 4 * sign))
        torture.key(bone, "rotation", 0.8 * amplitude, (-8 * amplitude * sign, 0, -3 * sign))
        torture.key(bone, "rotation", TORTURE_INTERVAL, (0, 0, 0))
    return torture


def _strain() -> Animation:
    strain = Animation("animation.cc_gravebinder_cage.strain", STRAIN_TIME, loop=False)
    for time, angle in ((0.0, 0), (0.08, 4.6), (0.18, -3.8), (0.29, 2.8), (0.42, -1.8), (STRAIN_TIME, 0)):
        strain.key("frame", "rotation", time, (0, 0, angle))
    strain.key("frame", "position", 0.0, (0, 0, 0))
    strain.key("frame", "position", 0.08, (0.8, 0, 0))
    strain.key("frame", "position", 0.18, (-0.8, 0, 0))
    strain.key("frame", "position", STRAIN_TIME, (0, 0, 0))
    _door(strain, ((0.0, 0), (0.1, -5), (0.26, 2.4), (STRAIN_TIME, 0)))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        strain.key(bone, "rotation", 0.0, (0, 0, 0))
        strain.key(bone, "rotation", 0.12, (16 * sign, 0, 6 * sign))
        strain.key(bone, "rotation", STRAIN_TIME, (0, 0, 0))
    return strain


def _burst() -> Animation:
    burst = Animation("animation.cc_gravebinder_cage.burst", BURST_TIME, loop=False)
    burst.key("frame", "position", 0.0, (0, 0, 0))
    burst.key("frame", "position", 0.1, (0, 0.6, 0))
    burst.key("frame", "position", BURST_TIME, (0, 0, 0))
    _door(burst, ((0.0, 0), (0.1, -8), (0.28, 3), (BURST_TIME, 0)))
    burst.key("ember", "scale", 0.0, (0.9, 0.9, 0.9))
    burst.key("ember", "scale", 0.1, (1.9, 1.9, 1.9))
    burst.key("ember", "scale", BURST_TIME, (0.9, 0.9, 0.9))
    burst.key("ring", "rotation", 0.0, (0, 0, 0))
    burst.key("ring", "rotation", BURST_TIME, (0, 150, 0))
    return burst


def _open() -> Animation:
    opened = Animation("animation.cc_gravebinder_cage.open", RELEASE_TIME + 0.5, loop=False)
    end = RELEASE_TIME + 0.5
    _door(opened, ((0.0, DOOR_SHUT), (0.3, -52), (0.6, -108), (0.85, -88), (end, DOOR_OPEN - 4)))
    opened.key("lock", "position", 0.0, (0, 0, 0))
    opened.key("lock", "position", 0.4, (0, 1.8, 0))
    opened.key("lock", "position", end, (0, 1.4, 0))
    opened.key("ember", "scale", 0.0, (0.2, 0.2, 0.2))
    opened.key("ember", "scale", 0.5, (0, 0, 0))
    opened.key("ember", "scale", end, (0, 0, 0))
    opened.key("ring", "rotation", 0.0, (0, 300, 0))
    opened.key("ring", "rotation", end, (0, 120, 0))
    return opened


def _released() -> Animation:
    released = Animation("animation.cc_gravebinder_cage.released", RELEASE_TIME, loop=False)
    _door(released, ((0.0, DOOR_OPEN - 4), (0.35, DOOR_OPEN - 7), (0.7, DOOR_OPEN + 3), (RELEASE_TIME, DOOR_OPEN)))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        released.key(bone, "rotation", 0.0, (0, 0, 0))
        released.key(bone, "rotation", 0.4, (6 * sign, 0, 2 * sign))
        released.key(bone, "rotation", RELEASE_TIME, (0, 0, 0))
    return released


def _broken() -> Animation:
    broken = Animation("animation.cc_gravebinder_cage.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("frame", "rotation", 0.0, (0, 0, 0))
    broken.key("frame", "rotation", 0.6, (0, 0, 7))
    broken.key("frame", "rotation", BROKEN_TIME, (0, 0, 5))
    broken.key("frame", "position", 0.0, (0, 0, 0))
    broken.key("frame", "position", 1.1, (0, -1.4, 0))
    broken.key("frame", "position", BROKEN_TIME, (0, -1.4, 0))
    _door(broken, ((0.0, 0), (0.7, -44), (BROKEN_TIME, -58)))
    broken.key("roof", "rotation", 0.0, (0, 0, 0))
    broken.key("roof", "rotation", 1.0, (2, 0, -8))
    broken.key("roof", "rotation", BROKEN_TIME, (3, 0, -11))
    broken.key("ring", "rotation", 0.0, (0, 0, 0))
    broken.key("ring", "position", 0.0, (0, 0, 0))
    broken.key("ring", "position", BROKEN_TIME, (0, -6, 0))
    broken.key("ring", "rotation", BROKEN_TIME, (0, 0, 40))
    broken.key("ember", "scale", 0.0, (0, 0, 0))
    broken.key("ember", "scale", BROKEN_TIME, (0, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        broken.key(bone, "rotation", 0.0, (0, 0, 0))
        broken.key(bone, "rotation", 0.5, (26 * sign, 0, 8 * sign))
        broken.key(bone, "rotation", BROKEN_TIME, (18 * sign, 0, 5 * sign))
    return broken
