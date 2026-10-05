"""Iron Maiden — the flagship contraption, rebuilt for v0.1.4.

An upright, riveted iron cabinet roughly 1.5 x 2.4 blocks: a plinth, a hollow
shell with a soul-lit inner plate, a bed of nails that extends on every turn of
the screw, two doors with barred windows so the captive stays visible, a crank
that spins while the device works, hanging chains, and crack overlays that
appear as the frame is battered.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    BLOOD,
    GRIME,
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
    soul_glow,
    spike as spike_art,
    spoked_wheel,
    steel_face,
    steel_panel,
    steel_plate,
    stone_brick,
)
from canvas import mix, rgba, shade
from model import Face, Model
from pipeline import DeviceArt, scale_device

# Timings mirrored from behavior_pack/scripts/config.js (20 ticks = 1 second).
CAPTURE_DELAY = 1.0
CLOSE_DURATION = 1.5
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 3.0
RELEASE_TIME = 1.0
BROKEN_TIME = 1.5
# World size: authored scale x0.8 (1 unit = 1/16 block).
SCALE = 0.8

STRAIN_TIME = 0.7
BURST_TIME = 0.45

# ------------------------------------------------------------------ painters --
HIDDEN = rgba("#20242b")
GLASS = rgba("#0a0d12")


def face(paint, **kwargs) -> Face:
    return Face(paint=paint, **kwargs)


def patch(color, key: str, size=(1, 1)) -> Face:
    """One shared flat patch, reused by every hidden or filler face."""
    return Face(paint=flat(color), size=size, share=f"flat:{key}")


HIDDEN_FLAT = lambda: patch(HIDDEN, "hidden")  # noqa: E731
DARK_FLAT = lambda: patch(IRON_BLACK, "iron_black")  # noqa: E731


def clear(painter) -> None:
    """A fully transparent patch: used for the back of a decal and for gaps."""
    painter.clear()


CLEAR_FLAT = lambda: Face(paint=clear, size=(1, 1), share="flat:clear")  # noqa: E731


def door_outer(painter) -> None:
    """A riveted door leaf with a barred window, hinge bands and a lock plate.

    Painted once and mirrored onto the right-hand door, so the left edge of the
    patch is the seam between the two leaves.
    """
    width, height = painter.rect.width, painter.rect.height
    steel_plate(STEEL, rivets=False, grime=0.22, scratches=4, rust=0.3)(painter)
    painter.outline(STEEL_DARK, inset=0)
    painter.outline(shade(STEEL_LIGHT, 0.15), inset=1)
    # Vertical plating seams binding the leaf together.
    for column in range(3, width - 2, 4):
        painter.vline(column, 2, height - 4, shade(STEEL_DARK, 0.1))
        painter.vline(min(width - 1, column + 1), 2, height - 4, shade(STEEL_MID, 0.35))
    # Hinge bands on the outer edge.
    for top in (max(3, height // 7), height - max(7, height // 7)):
        painter.box(1, top, 3, 3, STEEL_LIGHT)
        painter.box(1, top + 1, 3, 1, STEEL_HIGHLIGHT)
        painter.box(1, top + 2, 3, 1, STEEL_DARK)
        painter.px(2, top + 1, STEEL_DARK)
    # Lock plate and ring handle on the inner edge.
    lock_row = height // 2 - 1
    painter.box(max(1, width - 5), lock_row, 3, max(3, height // 9), STEEL_MID)
    painter.outline(STEEL_DARK, inset=0)
    painter.box(max(1, width - 5), lock_row, 3, 1, STEEL_HIGHLIGHT)
    painter.px(max(1, width - 3), lock_row + 2, IRON_BLACK)
    painter.px(max(1, width - 4), lock_row + 2, IRON_BLACK)
    # The observation window: iron bars over a black interior.
    window_top = max(4, height // 4)
    window_height = max(6, height // 2)
    window_left = 2
    window_width = max(3, width - 7)
    painter.box(window_left - 1, window_top - 1, window_width + 2, window_height + 2, shade(STEEL_DARK, 0.2))
    painter.box(window_left, window_top, window_width, window_height, GLASS)
    for row in range(window_top, window_top + window_height, 1):
        if row % 3 == 0:
            painter.box(window_left, row, window_width, 1, shade(STEEL_DARK, 0.05))
    for column in range(window_left + 1, window_left + window_width, 2):
        painter.box(column, window_top, 1, window_height, mix(STEEL, STEEL_DARK, 0.35))
        painter.px(column, window_top, STEEL_LIGHT)
    painter.outline(STEEL_DARK, inset=0)
    painter.box(window_left - 1, window_top - 1, window_width + 2, 1, STEEL_LIGHT)
    # Nail heads marching down the leaf beside the window.
    for row in range(3, height - 3, 3):
        painter.px(max(1, width - 6), row, STEEL_HIGHLIGHT)
        painter.px(2, row, shade(STEEL_DARK, 0.15))
    painter.bevel(STEEL_HIGHLIGHT, STEEL_DARK, alpha=120)


def door_inner(painter) -> None:
    """The inside of a door: dark iron, nails, and old blood."""
    width, height = painter.rect.width, painter.rect.height
    painter.gradient_v(shade(STEEL_DARK, -0.05), shade(IRON_BLACK, 0.05))
    painter.noise(STEEL_DARK, [RUST, IRON_BLACK], density=0.28)
    for row in range(0, height, 3):
        painter.hline(0, row, width, shade(IRON_BLACK, 0.08))
    for column in range(1, width - 1, 2):
        for row in range(2, height - 2, 4):
            painter.px(column, row, STEEL_LIGHT)
            painter.px(column, row + 1, shade(STEEL_DARK, -0.2))
    for _ in range(4):
        column = painter.rng.between(0, max(0, width - 1))
        top = painter.rng.between(0, max(0, height - 5))
        for row in range(top, min(height, top + painter.rng.between(3, 6))):
            painter.blend_px(column, row, BLOOD, painter.rng.between(90, 190) / 255.0)
    painter.bevel(STEEL, IRON_BLACK, alpha=90)


def nail_tip(painter) -> None:
    """Front of a bed nail."""
    width, height = painter.rect.width, painter.rect.height
    painter.fill(shade(STEEL_DARK, -0.25))
    if width >= 1 and height >= 1:
        painter.px(0, 0, STEEL_HIGHLIGHT)
        painter.box(0, 0, width, max(1, height // 2), STEEL_LIGHT)
    painter.bevel(STEEL_HIGHLIGHT, IRON_BLACK, alpha=110)


def nail_shaft(painter) -> None:
    """Side of a bed nail: a tapered shaft."""
    spike_art(STEEL, light=STEEL_HIGHLIGHT)(painter)


def chain_links(painter) -> None:
    """Vertical chain silhouette with transparent gaps between the links."""
    width, height = painter.rect.width, painter.rect.height
    painter.clear()
    link = max(3, height // 8)
    for index in range(0, height, link):
        wide = (index // link) % 2 == 0
        left = 0 if wide or width < 3 else 1
        right = width if wide or width < 3 else width - 1
        for row in range(index, min(height, index + link)):
            painter.box(left, row, max(1, right - left), 1, shade(STEEL_MID, -0.1))
        painter.box(left, index, max(1, right - left), 1, STEEL_LIGHT)
        painter.box(left, min(height - 1, index + link - 1), max(1, right - left), 1, IRON_BLACK)
        painter.px(min(width - 1, left), index + 1, STEEL_HIGHLIGHT)
    painter.noise(STEEL_MID, [IRON_BLACK, STEEL_LIGHT], density=0.1)


def cracked_plate(seed: int, count: int = 5):
    """A wear plate: hairline cracks floating just clear of the shell."""
    return cracks(seed, count=count, color=IRON_BLACK, glow=shade(RUST, 0.1))


def shell_side(painter) -> None:
    """Outer side wall of the cabinet."""
    steel_plate(STEEL_DARK, rivets=True, grime=0.3, rust=0.45, bands=2)(painter)
    width, height = painter.rect.width, painter.rect.height
    for row in range(0, height, 4):
        painter.hline(0, row, width, shade(IRON_BLACK, 0.1))
    painter.bevel(STEEL_MID, IRON_BLACK, alpha=130)


def shell_inner(painter) -> None:
    """Interior wall: scorched, bloodied, unlit."""
    painter.gradient_v(shade(STEEL_DARK, -0.2), shade(IRON_BLACK, 0.12))
    painter.noise(STEEL_DARK, [IRON_BLACK, BLOOD], density=0.25)
    for row in range(0, painter.rect.height, 5):
        painter.hline(0, row, painter.rect.width, shade(IRON_BLACK, 0.15))


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_iron_maiden",
        texture_width=128,
        texture_height=256,
    )

    # ---------------------------------------------------------------- base --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-11, 0, -10], [22, 3, 20],
        {
            "up": face(stone_brick()),
            "north": face(stone_brick(), share="plinth"),
            "south": face(stone_brick(), share="plinth"),
            "east": face(stone_brick(), share="plinth"),
            "west": face(stone_brick(), share="plinth"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- shell --
    body = model.bone("body", [0, 3, 0], parent="base")
    body.cube(
        [-11, 3, 7], [22, 34, 3],  # back wall
        {
            "north": face(shell_inner, share="shell_back"),
            "south": face(steel_panel(STEEL_DARK, bands=3, rust=0.5)),
            "east": face(shell_side),
            "west": face(shell_side, share="shell_side"),
            "up": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    body.cube(
        [-11, 3, -4], [3, 34, 11],  # left wall
        {
            "north": face(shell_side, share="shell_side"),
            "south": face(shell_inner, share="shell_wall_end"),
            "east": face(shell_inner, size=(2, 27), share="shell_wall_inner"),
            "west": face(steel_panel(STEEL, bands=3, rust=0.3)),
            "up": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    body.cube(
        [8, 3, -4], [3, 34, 11],  # right wall
        {
            "north": face(shell_side, share="shell_side"),
            "south": face(shell_inner, size=(9, 27), share="shell_wall_wide"),
            "east": face(steel_panel(STEEL, bands=3, rust=0.3)),
            "west": face(shell_inner, size=(2, 27), share="shell_wall_inner"),
            "up": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    body.cube(
        [-8, 3, -4], [16, 2, 11],  # raised floor for the captive
        {
            "north": face(steel_plate(STEEL_DARK, rivets=False, grime=0.4, bands=1)),
            "south": HIDDEN_FLAT(),
            "east": HIDDEN_FLAT(),
            "west": HIDDEN_FLAT(),
            "up": face(steel_panel(STEEL_MID, seams=4, bands=1, rust=0.25)),
            "down": HIDDEN_FLAT(),
        },
    )
    body.cube(
        [-8, 8, 6], [16, 22, 1],  # the maiden's own face, behind the captive
        {
            "north": face(steel_face(STEEL, eye_glow=SOUL_LIGHT)),
            "south": HIDDEN_FLAT(),
            "east": HIDDEN_FLAT(),
            "west": HIDDEN_FLAT(),
            "up": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- roof --
    roof = model.bone("roof", [0, 37, 0], parent="body")
    roof.cube(
        [-12, 37, -11], [24, 3, 21],
        {
            "up": face(steel_panel(STEEL, bands=3, rust=0.35, seams=5)),
            "north": face(steel_panel(STEEL_DARK, bands=2, rust=0.45), share="roof_edge"),
            "south": face(steel_panel(STEEL_DARK, bands=2, rust=0.45), share="roof_edge"),
            "east": face(steel_panel(STEEL_DARK, bands=2, rust=0.45), share="roof_edge"),
            "west": face(steel_panel(STEEL_DARK, bands=2, rust=0.45), share="roof_edge"),
            "down": HIDDEN_FLAT(),
        },
    )
    crown = model.bone("crown", [0, 40, 0], parent="roof")
    crown.cube(
        [-9, 40, -8], [18, 3, 17],
        {
            "up": face(steel_panel(STEEL, bands=2, rust=0.3, seams=4)),
            "north": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "south": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "east": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "west": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "down": HIDDEN_FLAT(),
        },
    )
    crown.cube(
        [-5, 43, -4], [10, 3, 9],
        {
            "up": face(steel_panel(STEEL_MID, bands=1, rust=0.3, seams=2)),
            "north": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "south": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "east": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "west": face(steel_panel(STEEL_DARK, bands=2, rust=0.4), share="crown_edge"),
            "down": HIDDEN_FLAT(),
        },
    )
    spike_tower = model.bone("spike_tower", [0, 46, 0], parent="crown")
    spike_tower.cube(
        [-1, 46, -1], [2, 6, 2],
        {
            "north": face(spike_art(STEEL, light=STEEL_HIGHLIGHT)),
            "south": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="tower_spike"),
            "east": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="tower_spike"),
            "west": face(spike_art(STEEL, light=STEEL_HIGHLIGHT), share="tower_spike"),
            "up": face(spike_art(STEEL_HIGHLIGHT, light=SOUL_PALE)),
            "down": HIDDEN_FLAT(),
        },
    )

    # --------------------------------------------------------------- doors --
    left = model.bone("door_left", [-11, 3, -7], parent="body")
    left.cube(
        [-11, 3, -7], [11, 34, 3],
        {
            "north": face(door_outer),
            "south": face(door_inner),
            "east": face(steel_panel(STEEL_DARK, bands=3, rust=0.4, seams=2), share="door_edge"),
            "west": face(steel_panel(STEEL_DARK, bands=3, rust=0.4, seams=2), share="door_edge"),
            "up": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )
    right = model.bone("door_right", [11, 3, -7], parent="body")
    right.cube(
        [0, 3, -7], [11, 34, 3],
        {
            "north": face(door_outer, flip_u=True),
            "south": face(door_inner, flip_u=True),
            "east": face(steel_panel(STEEL_DARK, bands=3, rust=0.4, seams=2), share="door_edge"),
            "west": face(steel_panel(STEEL_DARK, bands=3, rust=0.4, seams=2), share="door_edge"),
            "up": DARK_FLAT(),
            "down": HIDDEN_FLAT(),
        },
    )

    # --------------------------------------------------------- spike bed ----
    spikes = model.bone("spikes", [0, 4, 6], parent="body")
    for column in (-7, -5, -3, -1, 1, 3, 5):
        for row in (10, 15, 20, 25, 30):
            spikes.cube(
                [column, row, 3], [1, 1, 3],
                {
                    "north": face(nail_tip),
                    "south": DARK_FLAT(),
                    "east": face(nail_shaft, share="nail_side"),
                    "west": face(nail_shaft, share="nail_side"),
                    "up": face(nail_shaft, share="nail_axis"),
                    "down": face(nail_shaft, share="nail_axis"),
                },
            )

    # -------------------------------------------------------------- ember ---
    ember = model.bone("ember", [0, 30, 2], parent="body")
    ember.cube(
        [-1, 29, 1], [2, 3, 2],
        {
            "north": face(soul_glow(SOUL)),
            "south": face(soul_glow(SOUL), share="ember_back"),
            "east": face(soul_glow(SOUL), share="ember_back"),
            "west": face(soul_glow(SOUL), share="ember_back"),
            "up": face(soul_glow(SOUL_PALE, light=SOUL_PALE, pale=(255, 255, 255, 255))),
            "down": face(soul_glow(SOUL, light=SOUL, pale=SOUL_LIGHT), share="ember_down"),
        },
    )

    # -------------------------------------------------------------- crank ---
    crank = model.bone("crank", [17, 21, 0], parent="body")
    crank.cube(
        [11, 20, -1], [7, 2, 2],  # axle out of the right wall
        {
            "north": DARK_FLAT(),
            "south": DARK_FLAT(),
            "east": DARK_FLAT(),
            "west": DARK_FLAT(),
            "up": face(steel_panel(STEEL_MID, bands=1, seams=1, rust=0.3)),
            "down": DARK_FLAT(),
        },
    )
    crank.cube(
        [17, 12, -9], [1, 19, 19],  # wheel in the YZ plane
        {
            "north": DARK_FLAT(),
            "south": DARK_FLAT(),
            "east": face(spoked_wheel(STEEL, light=STEEL_HIGHLIGHT)),
            "west": face(spoked_wheel(STEEL, light=STEEL_HIGHLIGHT), share="wheel"),
            "up": DARK_FLAT(),
            "down": DARK_FLAT(),
        },
    )
    crank.cube(
        [16, 21, 8], [3, 2, 4],  # crank handle
        {
            "north": DARK_FLAT(),
            "south": DARK_FLAT(),
            "east": patch(STEEL_LIGHT, "steel_light"),
            "west": DARK_FLAT(),
            "up": DARK_FLAT(),
            "down": DARK_FLAT(),
        },
    )
    crank.cube(
        [11, 17, -2], [3, 3, 5],  # bracket holding the axle
        {
            "north": face(steel_panel(STEEL_DARK, bands=1, seams=2, rust=0.4), share="bracket_side"),
            "south": face(steel_plate(STEEL_DARK, rivets=True, grime=0.3), share="bracket"),
            "east": DARK_FLAT(),
            "west": HIDDEN_FLAT(),
            "up": face(steel_panel(STEEL_MID, bands=1, seams=1, rust=0.25)),
            "down": HIDDEN_FLAT(),
        },
    )

    # ------------------------------------------------------------- chains ---
    for side, column in (("left", -12), ("right", 11)):
        chain = model.bone(f"chain_{side}", [column + 0.5, 37, 0], parent="body")
        chain.cube(
            [column, 25, -1], [1, 12, 2],
            {
                "north": DARK_FLAT(),
                "south": DARK_FLAT(),
                "east": face(chain_links),
                "west": face(chain_links, share="chain_links"),
                "up": DARK_FLAT(),
                "down": face(chain_links, share="chain_links"),
            },
        )

    # --------------------------------------------------------- wear plates --
    wear_1 = model.bone("wear_1_chest", [-8, 20, -8], parent="body")
    wear_1.cube(
        [-8, 16, -8], [7, 9, 1],
        {
            "north": face(cracked_plate(1, 4)),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "up": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_2 = model.bone("wear_2_flank", [12, 24, 2], parent="body")
    wear_2.cube(
        [11, 20, -2], [1, 9, 8],
        {
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": face(cracked_plate(2, 5)),
            "west": CLEAR_FLAT(),
            "up": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_3 = model.bone("wear_3_roof", [0, 43, 0], parent="crown")
    wear_3.cube(
        [-9, 43, -8], [18, 1, 4],
        {
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "up": face(cracked_plate(3, 6)),
            "down": CLEAR_FLAT(),
        },
    )

    return scale_device(DeviceArt(
        slug="iron_maiden",
        display_name="Iron Maiden",
        model=model,
        animations=animations(),
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:basic_flame_particle",
    ), SCALE)


# --------------------------------------------------------------- animations --
def animations() -> list[Animation]:
    """Every animation the v0.1.4 controller expects, authored by hand."""
    return [
        _idle(),
        _detect(),
        _close(),
        _closed(),
        _torture(),
        _torture_high(),
        _strain(),
        _burst(),
        _open(),
        _released(),
        _broken(),
    ]


DOORS_SHUT = {"door_left": (0, 0, 0), "door_right": (0, 0, 0)}
DOORS_AJAR = {"door_left": (0, 38, 0), "door_right": (0, -38, 0)}
DOORS_WIDE = {"door_left": (0, 102, 0), "door_right": (0, -102, 0)}


def _doors(animation: Animation, values: dict[str, tuple[float, float, float]]) -> Animation:
    for bone, rotation in values.items():
        animation.key(bone, "rotation", 0.0, rotation)
    return animation


def _idle() -> Animation:
    idle = Animation("animation.cc_iron_maiden.idle", 4.0, loop=True)
    for time, y in ((0.0, 0), (2.0, 0.16), (4.0, 0)):
        idle.key("body", "position", time, (0, y, 0))
    for time, angle in ((0.0, 0), (1.0, 0.9), (2.5, -0.7), (4.0, 0)):
        idle.key("door_left", "rotation", time, (0, angle, 0))
        idle.key("door_right", "rotation", time, (0, -angle, 0))
    for time, angle in ((0.0, 2.5), (2.0, -2.5), (4.0, 2.5)):
        idle.key("chain_left", "rotation", time, (angle, 0, 0))
        idle.key("chain_right", "rotation", time, (-angle, 0, 0))
    idle.key("spikes", "scale", 0.0, (1, 1, 0.2))
    idle.key("spikes", "scale", 4.0, (1, 1, 0.2))
    idle.key("ember", "scale", 0.0, (0, 0, 0))
    idle.key("ember", "scale", 4.0, (0, 0, 0))
    idle.key("crank", "rotation", 0.0, (0, 0, 0))
    idle.key("crank", "rotation", 4.0, (0, 0, 0))
    return idle


def _detect() -> Animation:
    detect = Animation("animation.cc_iron_maiden.detect", CAPTURE_DELAY, loop=True)
    _doors(detect, DOORS_SHUT)
    detect.key("door_left", "rotation", 0.45, (0, 44, 0))
    detect.key("door_left", "rotation", CAPTURE_DELAY, (0, 41, 0))
    detect.key("door_right", "rotation", 0.45, (0, -44, 0))
    detect.key("door_right", "rotation", CAPTURE_DELAY, (0, -41, 0))
    for time, lean in ((0.0, 0), (0.5, 2.6), (1.0, 2.1)):
        detect.key("body", "rotation", time, (lean, 0, 0))
    detect.key("spikes", "scale", 0.0, (1, 1, 0.2))
    detect.key("spikes", "scale", CAPTURE_DELAY, (1, 1, 0.4))
    detect.key("ember", "scale", 0.0, (0, 0, 0))
    detect.key("ember", "scale", 0.45, (0.6, 0.6, 0.6))
    detect.key("ember", "scale", CAPTURE_DELAY, (0.85, 0.85, 0.85))
    detect.key("ember", "position", 0.0, (0, 0, 0))
    detect.key("ember", "position", CAPTURE_DELAY, (0, -1.2, -1))
    detect.key("crank", "rotation", 0.0, (0, 0, 0))
    detect.key("crank", "rotation", CAPTURE_DELAY, (26, 0, 0))
    detect.key("chain_left", "rotation", 0.0, (0, 0, 0))
    detect.key("chain_left", "rotation", CAPTURE_DELAY, (6, 0, 0))
    detect.key("chain_right", "rotation", 0.0, (0, 0, 0))
    detect.key("chain_right", "rotation", CAPTURE_DELAY, (-6, 0, 0))
    return detect


def _close() -> Animation:
    close = Animation("animation.cc_iron_maiden.close", CLOSE_DURATION, loop=False)
    close.key("door_left", "rotation", 0.0, (0, 41, 0))
    close.key("door_left", "rotation", 0.6, (0, -5, 0))
    close.key("door_left", "rotation", 0.82, (0, 1.8, 0))
    close.key("door_left", "rotation", 1.05, (0, 0, 0))
    close.key("door_left", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("door_right", "rotation", 0.0, (0, -41, 0))
    close.key("door_right", "rotation", 0.6, (0, 5, 0))
    close.key("door_right", "rotation", 0.82, (0, -1.8, 0))
    close.key("door_right", "rotation", 1.05, (0, 0, 0))
    close.key("door_right", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("body", "rotation", 0.0, (2.1, 0, 0))
    close.key("body", "rotation", 0.6, (-1.6, 0, 0))
    close.key("body", "rotation", 1.05, (0, 0, 0))
    close.key("body", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("body", "position", 0.0, (0, 0, 0))
    close.key("body", "position", 0.62, (0, -0.5, 0.6))
    close.key("body", "position", 1.1, (0, 0, 0))
    close.key("body", "position", CLOSE_DURATION, (0, 0, 0))
    close.key("spikes", "scale", 0.0, (1, 1, 0.4))
    close.key("spikes", "scale", 0.66, (1, 1, 1.12))
    close.key("spikes", "scale", 1.0, (1, 1, 1))
    close.key("spikes", "scale", CLOSE_DURATION, (1, 1, 1))
    close.key("ember", "scale", 0.0, (0.85, 0.85, 0.85))
    close.key("ember", "scale", 0.5, (1.5, 1.5, 1.5))
    close.key("ember", "scale", 1.05, (0, 0, 0))
    close.key("ember", "scale", CLOSE_DURATION, (0, 0, 0))
    close.key("crank", "rotation", 0.0, (26, 0, 0))
    close.key("crank", "rotation", 0.7, (92, 0, 0))
    close.key("crank", "rotation", CLOSE_DURATION, (96, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        close.key(bone, "rotation", 0.0, (6 * sign, 0, 0))
        close.key(bone, "rotation", 0.35, (-9 * sign, 0, 4 * sign))
        close.key(bone, "rotation", 0.8, (4 * sign, 0, -2 * sign))
        close.key(bone, "rotation", CLOSE_DURATION, (0, 0, 0))
    return close


def _closed() -> Animation:
    closed = Animation("animation.cc_iron_maiden.closed", CLOSED_PAUSE, loop=True)
    closed.key("door_left", "rotation", 0.0, (0, 0, 0))
    closed.key("door_left", "rotation", 0.22, (0, 1.1, 0))
    closed.key("door_left", "rotation", 0.5, (0, 0, 0))
    closed.key("door_right", "rotation", 0.0, (0, 0, 0))
    closed.key("door_right", "rotation", 0.22, (0, -1.1, 0))
    closed.key("door_right", "rotation", 0.5, (0, 0, 0))
    closed.key("spikes", "scale", 0.0, (1, 1, 1))
    closed.key("spikes", "scale", 0.5, (1, 1, 1))
    closed.key("ember", "scale", 0.0, (0.25, 0.25, 0.25))
    closed.key("ember", "scale", 0.3, (0.5, 0.5, 0.5))
    closed.key("ember", "scale", 0.5, (0.25, 0.25, 0.25))
    closed.key("crank", "rotation", 0.0, (96, 0, 0))
    closed.key("crank", "rotation", 0.5, (96, 0, 0))
    return closed


def _torture_body(animation: Animation, amplitude: float, speed: float) -> None:
    for time, angle in ((0.0, 0), (0.25 * speed, amplitude), (0.5 * speed, -amplitude * 0.85),
                        (0.85 * speed, amplitude * 0.6), (1.3 * speed, 0), (TORTURE_INTERVAL, 0)):
        animation.key("body", "rotation", time, (0, 0, angle))
    animation.key("body", "position", 0.0, (0, 0, 0))
    animation.key("body", "position", 0.3 * speed, (0.45 * amplitude, 0, 0))
    animation.key("body", "position", 0.7 * speed, (-0.45 * amplitude, 0, 0))
    animation.key("body", "position", 1.2 * speed, (0, 0, 0))
    animation.key("body", "position", TORTURE_INTERVAL, (0, 0, 0))


def _torture() -> Animation:
    torture = Animation("animation.cc_iron_maiden.torture", TORTURE_INTERVAL, loop=True)
    _torture_body(torture, 1.3, 1.0)
    torture.key("door_left", "rotation", 0.0, (0, 0, 0))
    torture.key("door_left", "rotation", 0.45, (0, -2.4, 0))
    torture.key("door_left", "rotation", 1.0, (0, 0.8, 0))
    torture.key("door_left", "rotation", 1.6, (0, 0, 0))
    torture.key("door_left", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("door_right", "rotation", 0.0, (0, 0, 0))
    torture.key("door_right", "rotation", 0.45, (0, 2.4, 0))
    torture.key("door_right", "rotation", 1.0, (0, -0.8, 0))
    torture.key("door_right", "rotation", 1.6, (0, 0, 0))
    torture.key("door_right", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("spikes", "scale", 0.0, (1, 1, 0.6))
    torture.key("spikes", "scale", 0.55, (1, 1, 1))
    torture.key("spikes", "scale", 1.9, (1, 1, 1))
    torture.key("spikes", "scale", 2.5, (1, 1, 0.6))
    torture.key("spikes", "scale", TORTURE_INTERVAL, (1, 1, 0.6))
    torture.key("ember", "scale", 0.0, (0.5, 0.5, 0.5))
    torture.key("ember", "scale", 1.5, (0.95, 0.95, 0.95))
    torture.key("ember", "scale", TORTURE_INTERVAL, (0.5, 0.5, 0.5))
    torture.key("ember", "rotation", 0.0, (0, 0, -8))
    torture.key("ember", "rotation", 1.5, (0, 0, 10))
    torture.key("ember", "rotation", TORTURE_INTERVAL, (0, 0, -8))
    torture.key("crank", "rotation", 0.0, (96, 0, 0))
    torture.key("crank", "rotation", TORTURE_INTERVAL, (456, 0, 0))
    torture.key("chain_left", "rotation", 0.0, (0, 0, 0))
    torture.key("chain_left", "rotation", 0.4, (7, 0, 3))
    torture.key("chain_left", "rotation", 0.9, (-5, 0, -2))
    torture.key("chain_left", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("chain_right", "rotation", 0.0, (0, 0, 0))
    torture.key("chain_right", "rotation", 0.4, (-7, 0, 3))
    torture.key("chain_right", "rotation", 0.9, (5, 0, -2))
    torture.key("chain_right", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("roof", "rotation", 0.0, (0, 0, 0))
    torture.key("roof", "rotation", 0.5, (0, 0, 1.4))
    torture.key("roof", "rotation", 1.1, (0, 0, -1.1))
    torture.key("roof", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    return torture


def _torture_high() -> Animation:
    torture = Animation("animation.cc_iron_maiden.torture_high", TORTURE_INTERVAL, loop=True)
    _torture_body(torture, 2.4, 0.75)
    torture.key("door_left", "rotation", 0.0, (0, 0, 0))
    torture.key("door_left", "rotation", 0.35, (0, -4.5, 0))
    torture.key("door_left", "rotation", 0.8, (0, 2.2, 0))
    torture.key("door_left", "rotation", 1.3, (0, 0, 0))
    torture.key("door_left", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("door_right", "rotation", 0.0, (0, 0, 0))
    torture.key("door_right", "rotation", 0.35, (0, 4.5, 0))
    torture.key("door_right", "rotation", 0.8, (0, -2.2, 0))
    torture.key("door_right", "rotation", 1.3, (0, 0, 0))
    torture.key("door_right", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    torture.key("spikes", "scale", 0.0, (1, 1, 0.75))
    torture.key("spikes", "scale", 0.4, (1, 1, 1.18))
    torture.key("spikes", "scale", 1.4, (1, 1, 0.75))
    torture.key("spikes", "scale", 1.8, (1, 1, 1.18))
    torture.key("spikes", "scale", TORTURE_INTERVAL, (1, 1, 0.75))
    torture.key("ember", "scale", 0.0, (1.1, 1.1, 1.1))
    torture.key("ember", "scale", 0.9, (1.7, 1.7, 1.7))
    torture.key("ember", "scale", 1.8, (1.1, 1.1, 1.1))
    torture.key("ember", "rotation", 0.0, (0, 0, -14))
    torture.key("ember", "rotation", 0.9, (0, 0, 16))
    torture.key("ember", "rotation", TORTURE_INTERVAL, (0, 0, -14))
    torture.key("crank", "rotation", 0.0, (456, 0, 0))
    torture.key("crank", "rotation", TORTURE_INTERVAL, (1176, 0, 0))
    torture.key("roof", "rotation", 0.0, (0, 0, 0))
    torture.key("roof", "rotation", 0.3, (0, 0, 2.6))
    torture.key("roof", "rotation", 0.7, (0, 0, -2.1))
    torture.key("roof", "rotation", TORTURE_INTERVAL, (0, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        torture.key(bone, "rotation", 0.0, (0, 0, 0))
        torture.key(bone, "rotation", 0.3, (12 * sign, 0, 5 * sign))
        torture.key(bone, "rotation", 0.7, (-9 * sign, 0, -4 * sign))
        torture.key(bone, "rotation", TORTURE_INTERVAL, (0, 0, 0))
    return torture


def _strain() -> Animation:
    strain = Animation("animation.cc_iron_maiden.strain", STRAIN_TIME, loop=False)
    for time, angle in ((0.0, 0), (0.08, 6), (0.17, -5.2), (0.27, 4.4), (0.38, -3), (0.5, 1.8), (0.62, -0.8)):
        strain.key("body", "rotation", time, (0, 0, angle))
    strain.key("body", "rotation", STRAIN_TIME, (0, 0, 0))
    strain.key("body", "position", 0.0, (0, 0, 0))
    strain.key("body", "position", 0.08, (0.9, 0, 0))
    strain.key("body", "position", 0.17, (-0.9, 0, 0))
    strain.key("body", "position", 0.3, (0.5, 0, 0))
    strain.key("body", "position", STRAIN_TIME, (0, 0, 0))
    strain.key("door_left", "rotation", 0.0, (0, 0, 0))
    strain.key("door_left", "rotation", 0.1, (0, -5, 0))
    strain.key("door_left", "rotation", 0.25, (0, 2.4, 0))
    strain.key("door_left", "rotation", 0.45, (0, 0, 0))
    strain.key("door_left", "rotation", STRAIN_TIME, (0, 0, 0))
    strain.key("door_right", "rotation", 0.0, (0, 0, 0))
    strain.key("door_right", "rotation", 0.1, (0, 5, 0))
    strain.key("door_right", "rotation", 0.25, (0, -2.4, 0))
    strain.key("door_right", "rotation", 0.45, (0, 0, 0))
    strain.key("door_right", "rotation", STRAIN_TIME, (0, 0, 0))
    strain.key("spikes", "scale", 0.0, (1, 1, 0.8))
    strain.key("spikes", "scale", 0.14, (1, 1, 1.05))
    strain.key("spikes", "scale", STRAIN_TIME, (1, 1, 0.8))
    return strain


def _burst() -> Animation:
    burst = Animation("animation.cc_iron_maiden.burst", BURST_TIME, loop=False)
    burst.key("body", "position", 0.0, (0, 0, 0))
    burst.key("body", "position", 0.12, (0, 0.7, 0))
    burst.key("body", "position", BURST_TIME, (0, 0, 0))
    burst.key("body", "rotation", 0.0, (0, 0, 0))
    burst.key("body", "rotation", 0.12, (0, 0, -2.4))
    burst.key("body", "rotation", 0.3, (0, 0, 1.6))
    burst.key("body", "rotation", BURST_TIME, (0, 0, 0))
    burst.key("door_left", "rotation", 0.0, (0, 0, 0))
    burst.key("door_left", "rotation", 0.1, (0, -7, 0))
    burst.key("door_left", "rotation", 0.3, (0, 0, 0))
    burst.key("door_left", "rotation", BURST_TIME, (0, 0, 0))
    burst.key("door_right", "rotation", 0.0, (0, 0, 0))
    burst.key("door_right", "rotation", 0.1, (0, 7, 0))
    burst.key("door_right", "rotation", 0.3, (0, 0, 0))
    burst.key("door_right", "rotation", BURST_TIME, (0, 0, 0))
    burst.key("spikes", "scale", 0.0, (1, 1, 0.9))
    burst.key("spikes", "scale", 0.1, (1, 1, 1.2))
    burst.key("spikes", "scale", BURST_TIME, (1, 1, 0.9))
    burst.key("ember", "scale", 0.0, (0.7, 0.7, 0.7))
    burst.key("ember", "scale", 0.12, (1.9, 1.9, 1.9))
    burst.key("ember", "scale", BURST_TIME, (0.7, 0.7, 0.7))
    burst.key("crank", "rotation", 0.0, (96, 0, 0))
    burst.key("crank", "rotation", BURST_TIME, (210, 0, 0))
    return burst


def _open() -> Animation:
    opened = Animation("animation.cc_iron_maiden.open", RELEASE_TIME + 0.6, loop=False)
    end = RELEASE_TIME + 0.6
    opened.key("door_left", "rotation", 0.0, (0, 0, 0))
    opened.key("door_left", "rotation", 0.32, (0, 58, 0))
    opened.key("door_left", "rotation", 0.62, (0, 108, 0))
    opened.key("door_left", "rotation", 0.9, (0, 97, 0))
    opened.key("door_left", "rotation", end, (0, 102, 0))
    opened.key("door_right", "rotation", 0.0, (0, 0, 0))
    opened.key("door_right", "rotation", 0.32, (0, -58, 0))
    opened.key("door_right", "rotation", 0.62, (0, -108, 0))
    opened.key("door_right", "rotation", 0.9, (0, -97, 0))
    opened.key("door_right", "rotation", end, (0, -102, 0))
    opened.key("body", "rotation", 0.0, (0, 0, 0))
    opened.key("body", "rotation", 0.5, (2, 0, 0))
    opened.key("body", "rotation", end, (0, 0, 0))
    opened.key("spikes", "scale", 0.0, (1, 1, 0.9))
    opened.key("spikes", "scale", 0.5, (1, 1, 0.22))
    opened.key("spikes", "scale", end, (1, 1, 0.2))
    opened.key("ember", "scale", 0.0, (0.7, 0.7, 0.7))
    opened.key("ember", "scale", 0.6, (0, 0, 0))
    opened.key("ember", "scale", end, (0, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        opened.key(bone, "rotation", 0.0, (0, 0, 0))
        opened.key(bone, "rotation", 0.3, (-11 * sign, 0, 0))
        opened.key(bone, "rotation", 0.7, (5 * sign, 0, 0))
        opened.key(bone, "rotation", end, (0, 0, 0))
    return opened


def _released() -> Animation:
    released = Animation("animation.cc_iron_maiden.released", RELEASE_TIME, loop=False)
    released.key("door_left", "rotation", 0.0, (0, 102, 0))
    released.key("door_left", "rotation", 0.4, (0, 96, 0))
    released.key("door_left", "rotation", 0.75, (0, 104, 0))
    released.key("door_left", "rotation", RELEASE_TIME, (0, 102, 0))
    released.key("door_right", "rotation", 0.0, (0, -102, 0))
    released.key("door_right", "rotation", 0.4, (0, -96, 0))
    released.key("door_right", "rotation", 0.75, (0, -104, 0))
    released.key("door_right", "rotation", RELEASE_TIME, (0, -102, 0))
    released.key("spikes", "scale", 0.0, (1, 1, 0.2))
    released.key("spikes", "scale", RELEASE_TIME, (1, 1, 0.2))
    released.key("ember", "scale", 0.0, (0, 0, 0))
    released.key("ember", "scale", RELEASE_TIME, (0, 0, 0))
    released.key("chain_left", "rotation", 0.0, (0, 0, 0))
    released.key("chain_left", "rotation", 0.5, (4, 0, 0))
    released.key("chain_left", "rotation", RELEASE_TIME, (0, 0, 0))
    released.key("chain_right", "rotation", 0.0, (0, 0, 0))
    released.key("chain_right", "rotation", 0.5, (-4, 0, 0))
    released.key("chain_right", "rotation", RELEASE_TIME, (0, 0, 0))
    return released


def _broken() -> Animation:
    broken = Animation("animation.cc_iron_maiden.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("body", "rotation", 0.0, (0, 0, 0))
    broken.key("body", "rotation", 0.7, (-5, 0, 4))
    broken.key("body", "rotation", BROKEN_TIME, (-7, 0, 2.5))
    broken.key("body", "position", 0.0, (0, 0, 0))
    broken.key("body", "position", 1.2, (0, -1.6, 0.8))
    broken.key("body", "position", BROKEN_TIME, (0, -1.6, 0.8))
    broken.key("door_left", "rotation", 0.0, (0, 0, 0))
    broken.key("door_left", "rotation", 0.85, (0, 74, 0))
    broken.key("door_left", "rotation", BROKEN_TIME, (0, 55, 0))
    broken.key("door_right", "rotation", 0.0, (0, 0, 0))
    broken.key("door_right", "rotation", 0.85, (0, -66, 0))
    broken.key("door_right", "rotation", BROKEN_TIME, (0, -82, 0))
    broken.key("crown", "rotation", 0.0, (0, 0, 0))
    broken.key("crown", "rotation", 0.9, (3, 0, -7))
    broken.key("crown", "rotation", BROKEN_TIME, (4, 0, -6))
    broken.key("spike_tower", "position", 0.0, (0, 0, 0))
    broken.key("spike_tower", "position", 1.0, (0, -4, 0))
    broken.key("spike_tower", "position", BROKEN_TIME, (0, -34, 6))
    broken.key("spike_tower", "rotation", 1.0, (0, 0, 0))
    broken.key("spike_tower", "rotation", BROKEN_TIME, (0, 0, 96))
    broken.key("spikes", "scale", 0.0, (1, 1, 0.2))
    broken.key("spikes", "scale", BROKEN_TIME, (1, 1, 0.05))
    broken.key("ember", "scale", 0.0, (0, 0, 0))
    broken.key("ember", "scale", BROKEN_TIME, (0, 0, 0))
    for bone, sign in (("chain_left", 1), ("chain_right", -1)):
        broken.key(bone, "rotation", 0.0, (0, 0, 0))
        broken.key(bone, "rotation", 0.6, (22 * sign, 0, 6 * sign))
        broken.key(bone, "rotation", BROKEN_TIME, (14 * sign, 0, 3 * sign))
    return broken
