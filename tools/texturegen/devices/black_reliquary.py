"""The Black Reliquary — an obsidian shrine that hoards souls.

v0.1.4 rebuild: roughly 2.2 x 2.9 x 2.2 blocks. Stepped obsidian plinth,
buttressed shrine body with gold bands, a shrine door that opens onto a glowing
soul recess, an iron lantern hanging over the door, gold chain swags down the
corners, a faceted soul crystal finial that swells while the device works, and
obsidian chips that flake off as it takes damage.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    CRYSTAL,
    CRYSTAL_DARK,
    CRYSTAL_LIGHT,
    GOLD,
    GOLD_LIGHT,
    IRON_BLACK,
    NETHERITE,
    NETHERITE_LIGHT,
    OBSIDIAN,
    OBSIDIAN_DARK,
    OBSIDIAN_FACET,
    OBSIDIAN_LIGHT,
    RUST,
    SOUL,
    SOUL_LIGHT,
    SOUL_PALE,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    STEEL_MID,
    chain,
    cracks,
    crystal,
    flat,
    gold_trim,
    netherite_plate,
    obsidian,
    rune_band,
    soul_glow,
    steel_panel,
    stone_brick,
)
from canvas import mix, rgba, shade
from model import Face, Model
from pipeline import DeviceArt, scale_device

CAPTURE_DELAY = 1.75
CLOSE_DURATION = 2.25
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 2.0
RELEASE_TIME = 1.0
BROKEN_TIME = 1.5
STRAIN_TIME = 0.7
BURST_TIME = 0.45

# World size: authored scale x1.1 (1 unit = 1/16 block) -> 2.6 blocks tall.
SCALE = 1.1

HIDDEN = rgba("#0c0a14")
RECESS = rgba("#0a0812")

DOOR_SHUT = 0.0
DOOR_OPEN = 104.0


def face(paint, **kwargs) -> Face:
    return Face(paint=paint, **kwargs)


def patch(color, key: str, size=(1, 1)) -> Face:
    return Face(paint=flat(color), size=size, share=f"flat:{key}")


HIDDEN_FLAT = lambda: patch(HIDDEN, "hidden")  # noqa: E731
DARK_FLAT = lambda: patch(IRON_BLACK, "iron_black")  # noqa: E731


def clear(painter) -> None:
    painter.clear()


CLEAR_FLAT = lambda: Face(paint=clear, size=(1, 1), share="flat:clear")  # noqa: E731


def gold_band(painter) -> None:
    """Gold inlay band with soul flecks caught in the metal."""
    gold_trim(GOLD, light=GOLD_LIGHT)(painter)
    width, height = painter.rect.width, painter.rect.height
    for column in range(1, max(1, width - 1), 3):
        if painter.rng.below(0.5):
            painter.px(column, max(1, height // 2), mix(GOLD_LIGHT, SOUL_PALE, 0.5))
    painter.bevel(GOLD_LIGHT, shade(GOLD, -0.5), alpha=150)


def netherite_band(painter) -> None:
    netherite_plate(NETHERITE, light=NETHERITE_LIGHT)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.box(0, 0, width, 1, mix(NETHERITE_LIGHT, GOLD, 0.25))
    painter.box(0, height - 1, width, 1, IRON_BLACK)


def shrine_wall(painter) -> None:
    """Buttressed obsidian wall with a gold seam."""
    obsidian(OBSIDIAN, facet=OBSIDIAN_FACET)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.box(0, height // 2 - 1, width, 2, shade(GOLD, -0.35))
    painter.box(0, height // 2 - 1, width, 1, GOLD)
    for column in range(1, width, 4):
        painter.vline(column, 0, height, shade(OBSIDIAN_DARK, -0.1))
        painter.vline(min(width - 1, column + 1), 0, height, shade(OBSIDIAN_LIGHT, 0.1))
    painter.bevel(OBSIDIAN_LIGHT, IRON_BLACK, alpha=150)


def door_face(painter) -> None:
    """The shrine door: gold-framed obsidian with a soul sigil."""
    obsidian(OBSIDIAN_DARK, facet=OBSIDIAN_FACET)(painter)
    width, height = painter.rect.width, painter.rect.height
    painter.outline(GOLD, 0)
    painter.outline(mix(GOLD, OBSIDIAN_DARK, 0.4), 1)
    # Sigil: a diamond of soul light with a bright core.
    center_x, center_y = width // 2, height // 2
    radius = max(2, min(width, height) // 4)
    for step in range(radius):
        painter.px(center_x - step, center_y - radius + step, SOUL_LIGHT)
        painter.px(center_x + step, center_y - radius + step, SOUL_LIGHT)
        painter.px(center_x - step, center_y + radius - step, SOUL_LIGHT)
        painter.px(center_x + step, center_y + radius - step, SOUL_LIGHT)
    painter.box(center_x - radius // 2, center_y - radius // 2, max(1, radius), max(1, radius), SOUL_PALE)
    for row in range(2, height - 2, 4):
        painter.px(1, row, GOLD_LIGHT)
        painter.px(max(0, width - 2), row, shade(GOLD_LIGHT, -0.2))
    painter.bevel(GOLD_LIGHT, IRON_BLACK, alpha=160)


def door_back(painter) -> None:
    """Inside of the shrine door."""
    painter.gradient_v(shade(OBSIDIAN_DARK, -0.1), shade(IRON_BLACK, 0.1))
    painter.noise(OBSIDIAN_DARK, [SOUL, IRON_BLACK], density=0.18)
    for row in range(1, painter.rect.height, 3):
        painter.hline(0, row, painter.rect.width, shade(SOUL, -0.55))
    painter.bevel(OBSIDIAN_LIGHT, IRON_BLACK, alpha=120)


def recess_face(painter) -> None:
    """Interior of the reliquary: a void lit from below."""
    painter.fill(RECESS)
    width, height = painter.rect.width, painter.rect.height
    painter.gradient_v(shade(SOUL, -0.72), RECESS)
    for column in range(0, width, 2):
        painter.vline(column, height // 2, max(1, height // 2), shade(SOUL, -0.45))
    for row in range(0, height, 3):
        painter.hline(0, row, width, shade(SOUL, -0.6))
    painter.bevel(SOUL, IRON_BLACK, alpha=90)


def lantern_head(painter) -> None:
    width, height = painter.rect.width, painter.rect.height
    painter.fill(STEEL_DARK)
    inner_width = max(1, width - 2)
    inner_height = max(1, height - 3)
    painter.box(1, 1, inner_width, inner_height, shade(SOUL, -0.3))
    painter.box(1, 2, inner_width, max(1, inner_height - 2), mix(SOUL, SOUL_PALE, 0.45))
    painter.vline(max(1, width // 2), 1, inner_height, SOUL_PALE)
    painter.box(0, 0, width, 1, GOLD)
    painter.box(0, height - 1, width, 1, IRON_BLACK)
    painter.bevel(GOLD_LIGHT, IRON_BLACK, alpha=140)


def gold_links(painter) -> None:
    """Gold chain silhouette with transparent gaps."""
    width, height = painter.rect.width, painter.rect.height
    painter.clear()
    link = max(3, height // 7)
    for index in range(0, height, link):
        wide = (index // link) % 2 == 0
        left = 0 if wide or width < 3 else 1
        right = width if wide or width < 3 else width - 1
        for row in range(index, min(height, index + link)):
            painter.box(left, row, max(1, right - left), 1, shade(GOLD, -0.2))
        painter.box(left, index, max(1, right - left), 1, GOLD_LIGHT)
        painter.box(left, min(height - 1, index + link - 1), max(1, right - left), 1, shade(GOLD, -0.5))
        painter.px(min(width - 1, left), index + 1, mix(GOLD_LIGHT, (255, 255, 255, 255), 0.35))


def cracked_obsidian(seed: int, count: int = 5):
    return cracks(seed, count=count, color=mix(SOUL, IRON_BLACK, 0.6), glow=SOUL_LIGHT)


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_black_reliquary",
        texture_width=128,
        texture_height=256,
    )
    obsidian_face = obsidian(OBSIDIAN_DARK, facet=OBSIDIAN_FACET)
    facet_top = obsidian(OBSIDIAN, facet=OBSIDIAN_FACET)
    crystal_face = crystal(CRYSTAL, light=CRYSTAL_LIGHT, dark=CRYSTAL_DARK)
    crystal_pale = crystal(CRYSTAL_LIGHT, light=(238, 222, 255, 255), dark=CRYSTAL)

    # ---------------------------------------------------------------- base --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-13, 0, -13], [26, 3, 26],  # bottom step
        {
            "up": face(facet_top),
            "north": face(obsidian_face, share="obsidian_side"),
            "south": face(obsidian_face, share="obsidian_side"),
            "east": face(obsidian_face, share="obsidian_side"),
            "west": face(obsidian_face, share="obsidian_side"),
            "down": HIDDEN_FLAT(),
        },
    )
    base.cube(
        [-11, 3, -11], [22, 4, 22],  # second step
        {
            "up": face(facet_top),
            "north": face(netherite_band, share="netherite_side"),
            "south": face(netherite_band, share="netherite_side"),
            "east": face(netherite_band, share="netherite_side"),
            "west": face(netherite_band, share="netherite_side"),
            "down": HIDDEN_FLAT(),
        },
    )
    base.cube(
        [-12, 7, -12], [24, 2, 24],  # gold ledge
        {
            "up": face(gold_band, size=(24, 24)),
            "north": face(gold_band, size=(24, 2), share="gold_edge_wide"),
            "south": face(gold_band, size=(24, 2), share="gold_edge_wide"),
            "east": face(gold_band, size=(24, 2), share="gold_edge_wide"),
            "west": face(gold_band, size=(24, 2), share="gold_edge_wide"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ---------------------------------------------------------------- body --
    body = model.bone("body", [0, 9, 0], parent="base")
    body.cube(
        [-10, 9, -10], [20, 16, 20],
        {
            "up": face(steel_panel(STEEL_DARK, bands=2, rust=0.4)),
            "north": face(shrine_wall),
            "south": face(shrine_wall, share="shrine_wall"),
            "east": face(shrine_wall, share="shrine_wall"),
            "west": face(shrine_wall, share="shrine_wall"),
            "down": HIDDEN_FLAT(),
        },
    )
    # Corner buttresses read the shrine as masonry rather than a tower.
    for x, z in ((-12, -12), (-12, 10), (10, -12), (10, 10)):
        body.cube(
            [x, 9, z], [2, 12, 2],
            {
                "up": HIDDEN_FLAT(),
                "north": face(obsidian_face, share="post_side"),
                "south": face(obsidian_face, share="post_side"),
                "east": face(obsidian_face, share="post_side"),
                "west": face(obsidian_face, share="post_side"),
                "down": HIDDEN_FLAT(),
            },
        )
    for row in (11, 21):
        body.cube(
            [-10.4, row, -10.4], [20.8, 2, 20.8],  # gold bands
            {
                "up": face(gold_band, size=(21, 21)),
                "north": face(gold_band, size=(21, 2), share="gold_edge_band"),
                "south": face(gold_band, size=(21, 2), share="gold_edge_band"),
                "east": face(gold_band, size=(21, 2), share="gold_edge_band"),
                "west": face(gold_band, size=(21, 2), share="gold_edge_band"),
                "down": HIDDEN_FLAT(),
            },
        )
    # The soul recess the door opens onto, on the camera-facing north side.
    body.cube(
        [-6, 11, -11], [12, 12, 1],
        {
            "up": HIDDEN_FLAT(),
            "north": face(recess_face, size=(12, 12)),
            "south": HIDDEN_FLAT(),
            "east": face(recess_face, size=(1, 12), share="recess_side"),
            "west": face(recess_face, size=(1, 12), share="recess_side"),
            "down": face(recess_face, size=(12, 1), share="recess_floor"),
        },
    )

    # --------------------------------------------------------------- roof ---
    roof = model.bone("roof", [0, 25, 0], parent="body")
    roof.cube(
        [-13, 25, -13], [26, 3, 26],
        {
            "up": face(facet_top),
            "north": face(netherite_band, share="netherite_side"),
            "south": face(netherite_band, share="netherite_side"),
            "east": face(netherite_band, share="netherite_side"),
            "west": face(netherite_band, share="netherite_side"),
            "down": HIDDEN_FLAT(),
        },
    )
    for x, z in ((-12, 11), (10, 11), (-12, -11), (10, -11)):
        roof.cube(
            [x + 0.5, 28, z + 0.5], [1, 5, 1],  # gold corner finials
            {
                "up": face(gold_band, size=(1, 1), share="finial_tip"),
                "north": face(gold_band, share="finial", size=(1, 5)),
                "south": face(gold_band, share="finial", size=(1, 5)),
                "east": face(gold_band, share="finial", size=(1, 5)),
                "west": face(gold_band, share="finial", size=(1, 5)),
                "down": HIDDEN_FLAT(),
            },
        )

    # ------------------------------------------------------------- crystal --
    crystal_bone = model.bone("crystal", [0, 33, 0], parent="roof")
    crystal_bone.cube(
        [-4, 28, -4], [8, 8, 8],
        {
            "up": face(crystal_face),
            "north": face(crystal_face, share="crystal_face"),
            "south": face(crystal_face, share="crystal_face"),
            "east": face(crystal_face, share="crystal_face"),
            "west": face(crystal_face, share="crystal_face"),
            "down": face(crystal(CRYSTAL_DARK, light=CRYSTAL, dark=CRYSTAL_DARK), share="crystal_under"),
        },
    )
    crystal_bone.cube(
        [-2.5, 36, -2.5], [5, 3, 5],
        {
            "up": face(crystal_pale),
            "north": face(crystal_pale, share="crystal_top"),
            "south": face(crystal_pale, share="crystal_top"),
            "east": face(crystal_pale, share="crystal_top"),
            "west": face(crystal_pale, share="crystal_top"),
            "down": HIDDEN_FLAT(),
        },
    )

    # ----------------------------------------------------------------- door --
    door = model.bone("door", [-7, 9, -11], parent="body")
    door.cube(
        [-7, 9, -11], [14, 14, 2],
        {
            "up": face(gold_band, size=(14, 2)),
            "north": face(door_face),
            "south": face(door_back),
            "east": face(shrine_wall, size=(2, 14), share="wall_edge"),
            "west": face(shrine_wall, size=(2, 14), share="wall_edge"),
            "down": HIDDEN_FLAT(),
        },
    )
    latch = model.bone("latch", [5, 15, -12], parent="door")
    latch.cube(
        [5, 13, -12], [3, 4, 2],
        {
            "up": face(steel_panel(STEEL_MID, bands=1, seams=1, rivets=False)),
            "north": face(steel_panel(STEEL, bands=1, seams=1, rivets=False)),
            "south": face(steel_panel(STEEL_DARK, bands=1, seams=1, rivets=False), share="latch_back"),
            "east": face(steel_panel(STEEL_DARK, bands=1, seams=1, rivets=False), share="latch_side"),
            "west": face(steel_panel(STEEL_DARK, bands=1, seams=1, rivets=False), share="latch_side"),
            "down": HIDDEN_FLAT(),
        },
    )

    # -------------------------------------------------------------- lantern --
    lantern = model.bone("lantern", [0, 22, -11], parent="body")
    lantern.cube(
        [-1, 19, -11.5], [2, 8, 1],  # gold chain above the door
        {
            "up": HIDDEN_FLAT(),
            "north": face(gold_links),
            "south": face(gold_links, share="gold_links"),
            "east": face(gold_links, share="gold_links"),
            "west": face(gold_links, share="gold_links"),
            "down": HIDDEN_FLAT(),
        },
    )
    lantern.cube(
        [-3, 15, -12], [6, 4, 4],
        {
            "up": face(gold_band, size=(6, 4)),
            "north": face(lantern_head),
            "south": face(lantern_head, share="lantern"),
            "east": face(lantern_head, share="lantern"),
            "west": face(lantern_head, share="lantern"),
            "down": face(lantern_head, share="lantern"),
        },
    )

    # ------------------------------------------------------------ gold swags --
    swag = model.bone("swags", [0, 25, 0], parent="roof")
    for side, column in (("left", -11), ("right", 10)):
        swag.cube(
            [column, 19, 6], [1, 7, 1],
            {
                "up": HIDDEN_FLAT(),
                "north": face(gold_links, share="gold_links"),
                "south": face(gold_links, share="gold_links"),
                "east": face(gold_links, share="gold_links"),
                "west": face(gold_links, share="gold_links"),
                "down": HIDDEN_FLAT(),
            },
        )

    # ----------------------------------------------------------- wear plates --
    wear_1 = model.bone("wear_1_body", [13, 22, 0], parent="body")
    wear_1.cube(
        [12, 16, -8], [1, 10, 15],
        {
            "up": CLEAR_FLAT(),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": face(cracked_obsidian(41, 6)),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_2 = model.bone("wear_2_roof", [0, 28, 0], parent="roof")
    wear_2.cube(
        [-9, 28, 2], [17, 1, 8],
        {
            "up": face(cracked_obsidian(42, 5)),
            "north": CLEAR_FLAT(),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )
    wear_3 = model.bone("wear_3_door", [0, 23, -11], parent="door")
    wear_3.cube(
        [-6, 22, -11.2], [12, 1, 4],
        {
            "up": CLEAR_FLAT(),
            "north": face(cracked_obsidian(43, 5)),
            "south": CLEAR_FLAT(),
            "east": CLEAR_FLAT(),
            "west": CLEAR_FLAT(),
            "down": CLEAR_FLAT(),
        },
    )

    return scale_device(DeviceArt(
        slug="black_reliquary",
        display_name="The Black Reliquary",
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
        _torture(1.0, "animation.cc_black_reliquary.torture"),
        _torture(0.55, "animation.cc_black_reliquary.torture_high"),
        _strain(),
        _burst(),
        _open(),
        _released(),
        _broken(),
    ]


def _door(animation: Animation, values) -> None:
    """The door hinges on its west edge and swings clear of the shrine face."""
    for time, angle in values:
        animation.key("door", "rotation", time, (0, angle, 0))


def _idle() -> Animation:
    idle = Animation("animation.cc_black_reliquary.idle", 5.0, loop=True)
    _door(idle, ((0.0, DOOR_SHUT), (5.0, DOOR_SHUT)))
    for time, scale in ((0.0, 1.0), (2.5, 1.06), (5.0, 1.0)):
        idle.key("crystal", "scale", time, (scale, scale, scale))
    idle.key("crystal", "rotation", 0.0, (0, 0, 0))
    idle.key("crystal", "rotation", 5.0, (0, 360, 0))
    for time, angle in ((0.0, 3), (2.5, -3), (5.0, 3)):
        idle.key("lantern", "rotation", time, (angle, 0, 0))
    for time, angle in ((0.0, 2), (2.6, -2), (5.0, 2)):
        idle.key("swags", "rotation", time, (0, 0, angle))
    idle.key("body", "position", 0.0, (0, 0, 0))
    idle.key("body", "position", 2.5, (0, 0.2, 0))
    idle.key("body", "position", 5.0, (0, 0, 0))
    return idle


def _detect() -> Animation:
    detect = Animation("animation.cc_black_reliquary.detect", CAPTURE_DELAY, loop=True)
    _door(detect, ((0.0, DOOR_SHUT), (CAPTURE_DELAY, -18)))
    for time, scale in ((0.0, 1.0), (CAPTURE_DELAY, 1.45)):
        detect.key("crystal", "scale", time, (scale, scale, scale))
    for time, angle in ((0.0, 3), (CAPTURE_DELAY, -12)):
        detect.key("lantern", "rotation", time, (angle, 0, 0))
    detect.key("lantern", "position", 0.0, (0, 0, 0))
    detect.key("lantern", "position", CAPTURE_DELAY, (0, 3, 0))
    for time, angle in ((0.0, 2), (CAPTURE_DELAY, -6)):
        detect.key("swags", "rotation", time, (0, 0, angle))
    detect.key("crystal", "rotation", 0.0, (0, 0, 0))
    detect.key("crystal", "rotation", CAPTURE_DELAY, (0, 220, 0))
    detect.key("latch", "position", 0.0, (0, 0, 0))
    detect.key("latch", "position", CAPTURE_DELAY, (0, 2, 0))
    return detect


def _close() -> Animation:
    close = Animation("animation.cc_black_reliquary.close", CLOSE_DURATION, loop=False)
    _door(close, ((0.0, -18), (0.5, 6), (0.75, -3), (1.0, 0), (CLOSE_DURATION, DOOR_SHUT)))
    close.key("body", "rotation", 0.0, (0, 0, 0))
    close.key("body", "rotation", 0.6, (0, 0, -2))
    close.key("body", "rotation", 1.1, (0, 0, 1.2))
    close.key("body", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("crystal", "scale", 0.0, (1.45, 1.45, 1.45))
    close.key("crystal", "scale", 0.72, (0.7, 1.6, 0.7))
    close.key("crystal", "scale", 1.2, (1, 1, 1))
    close.key("crystal", "scale", CLOSE_DURATION, (1, 1, 1))
    close.key("crystal", "rotation", 0.0, (0, 220, 0))
    close.key("crystal", "rotation", CLOSE_DURATION, (0, 300, 0))
    close.key("latch", "position", 0.0, (0, 2, 0))
    close.key("latch", "position", 0.7, (0, 0, 0))
    close.key("latch", "position", CLOSE_DURATION, (0, 0, 0))
    close.key("lantern", "rotation", 0.0, (-12, 0, 0))
    close.key("lantern", "rotation", 0.6, (16, 0, 0))
    close.key("lantern", "rotation", 1.2, (-6, 0, 0))
    close.key("lantern", "rotation", CLOSE_DURATION, (-3, 0, 0))
    close.key("lantern", "position", 0.0, (0, 3, 0))
    close.key("lantern", "position", CLOSE_DURATION, (0, 0, 0))
    close.key("swags", "rotation", 0.0, (-6, 0, 0))
    close.key("swags", "rotation", 0.7, (4, 0, 0))
    close.key("swags", "rotation", CLOSE_DURATION, (0, 0, 0))
    return close


def _closed() -> Animation:
    closed = Animation("animation.cc_black_reliquary.closed", CLOSED_PAUSE, loop=True)
    _door(closed, ((0.0, 0), (0.25, -1.4), (0.5, 0)))
    closed.key("crystal", "scale", 0.0, (1, 1, 1))
    closed.key("crystal", "scale", 0.25, (1.1, 1.1, 1.1))
    closed.key("crystal", "scale", 0.5, (1, 1, 1))
    closed.key("lantern", "rotation", 0.0, (-3, 0, 0))
    closed.key("lantern", "rotation", 0.25, (-6, 0, 0))
    closed.key("lantern", "rotation", 0.5, (-3, 0, 0))
    return closed


def _torture(amplitude: float, identifier: str) -> Animation:
    torture = Animation(identifier, TORTURE_INTERVAL, loop=True)
    for time, angle in ((0.0, 0), (0.2 * amplitude, 2.2 * amplitude), (0.45 * amplitude, -2 * amplitude),
                        (0.7 * amplitude, 1.2 * amplitude), (TORTURE_INTERVAL, 0)):
        torture.key("body", "rotation", time, (0, 0, angle))
    torture.key("body", "position", 0.0, (0, 0, 0))
    torture.key("body", "position", 0.25 * amplitude, (0.4 * amplitude, 0, 0))
    torture.key("body", "position", 0.6 * amplitude, (-0.4 * amplitude, 0, 0))
    torture.key("body", "position", TORTURE_INTERVAL, (0, 0, 0))
    # The crystal pulses with every soul drawn in.
    pulses = 4
    for index in range(pulses + 1):
        time = TORTURE_INTERVAL * index / pulses
        scale = 1.0 + 0.42 * amplitude * (index % 2)
        torture.key("crystal", "scale", time, (scale, scale, scale))
    torture.key("crystal", "rotation", 0.0, (0, 0, 0))
    torture.key("crystal", "rotation", TORTURE_INTERVAL, (0, 420 * amplitude, 0))
    _door(torture, ((0.0, 0), (0.3 * amplitude, -2.2 * amplitude), (0.8 * amplitude, 1.2 * amplitude),
                    (1.3 * amplitude, 0), (TORTURE_INTERVAL, 0)))
    torture.key("lantern", "rotation", 0.0, (-3, 0, 0))
    torture.key("lantern", "rotation", 0.4 * amplitude, (12 * amplitude, 0, -5))
    torture.key("lantern", "rotation", 1.1 * amplitude, (-9 * amplitude, 0, 4))
    torture.key("lantern", "rotation", TORTURE_INTERVAL, (-3, 0, 0))
    torture.key("lantern", "position", 0.0, (0, 0, 0))
    torture.key("lantern", "position", 0.5 * amplitude, (0, 0.6 * amplitude, 0))
    torture.key("lantern", "position", TORTURE_INTERVAL, (0, 0, 0))
    for time, angle in ((0.0, 0), (0.35 * amplitude, 6 * amplitude), (0.9 * amplitude, -4 * amplitude),
                        (TORTURE_INTERVAL, 0)):
        torture.key("swags", "rotation", time, (0, angle, 0))
    return torture


def _strain() -> Animation:
    strain = Animation("animation.cc_black_reliquary.strain", STRAIN_TIME, loop=False)
    for time, angle in ((0.0, 0), (0.08, 3.4), (0.18, -2.8), (0.3, 2), (STRAIN_TIME, 0)):
        strain.key("body", "rotation", time, (0, 0, angle))
    strain.key("body", "position", 0.0, (0, 0, 0))
    strain.key("body", "position", 0.08, (0.5, 0, 0))
    strain.key("body", "position", 0.18, (-0.5, 0, 0))
    strain.key("body", "position", STRAIN_TIME, (0, 0, 0))
    _door(strain, ((0.0, 0), (0.1, -4.4), (0.26, 2), (STRAIN_TIME, 0)))
    strain.key("crystal", "rotation", 0.0, (0, 0, 0))
    strain.key("crystal", "rotation", STRAIN_TIME, (0, 12, 0))
    strain.key("swags", "rotation", 0.0, (0, 0, 0))
    strain.key("swags", "rotation", 0.12, (0, 9, 0))
    strain.key("swags", "rotation", STRAIN_TIME, (0, 0, 0))
    return strain


def _burst() -> Animation:
    burst = Animation("animation.cc_black_reliquary.burst", BURST_TIME, loop=False)
    burst.key("body", "position", 0.0, (0, 0, 0))
    burst.key("body", "position", 0.1, (0, 0.5, 0))
    burst.key("body", "position", BURST_TIME, (0, 0, 0))
    burst.key("crystal", "scale", 0.0, (1, 1, 1))
    burst.key("crystal", "scale", 0.12, (1.6, 1.6, 1.6))
    burst.key("crystal", "scale", BURST_TIME, (1, 1, 1))
    burst.key("crystal", "rotation", 0.0, (0, 0, 0))
    burst.key("crystal", "rotation", BURST_TIME, (0, 90, 0))
    _door(burst, ((0.0, 0), (0.1, -6), (0.3, 2.6), (BURST_TIME, 0)))
    return burst


def _open() -> Animation:
    opened = Animation("animation.cc_black_reliquary.open", RELEASE_TIME + 0.6, loop=False)
    end = RELEASE_TIME + 0.6
    _door(opened, ((0.0, DOOR_SHUT), (0.35, 58), (0.65, 116), (0.9, 98), (end, DOOR_OPEN)))
    opened.key("latch", "position", 0.0, (0, 0, 0))
    opened.key("latch", "position", 0.45, (0, 2.4, 0))
    opened.key("latch", "position", end, (0, 2, 0))
    opened.key("crystal", "scale", 0.0, (1, 1, 1))
    opened.key("crystal", "scale", 0.7, (0.75, 0.75, 0.75))
    opened.key("crystal", "scale", end, (1, 1, 1))
    opened.key("lantern", "rotation", 0.0, (-3, 0, 0))
    opened.key("lantern", "rotation", 0.5, (14, 0, -6))
    opened.key("lantern", "rotation", end, (3, 0, 0))
    return opened


def _released() -> Animation:
    released = Animation("animation.cc_black_reliquary.released", RELEASE_TIME, loop=False)
    _door(released, ((0.0, DOOR_OPEN), (0.35, DOOR_OPEN - 4), (0.72, DOOR_OPEN + 3), (RELEASE_TIME, DOOR_OPEN)))
    released.key("crystal", "scale", 0.0, (1, 1, 1))
    released.key("crystal", "scale", 0.3, (1.12, 1.12, 1.12))
    released.key("crystal", "scale", RELEASE_TIME, (1, 1, 1))
    released.key("lantern", "rotation", 0.0, (3, 0, 0))
    released.key("lantern", "rotation", 0.4, (-6, 0, 0))
    released.key("lantern", "rotation", RELEASE_TIME, (3, 0, 0))
    return released


def _broken() -> Animation:
    broken = Animation("animation.cc_black_reliquary.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("body", "rotation", 0.0, (0, 0, 0))
    broken.key("body", "rotation", 0.7, (0, 0, 5))
    broken.key("body", "rotation", BROKEN_TIME, (0, 0, 8))
    broken.key("body", "position", 0.0, (0, 0, 0))
    broken.key("body", "position", 1.1, (0, -1.8, 0.6))
    broken.key("body", "position", BROKEN_TIME, (0, -2.4, 0.9))
    broken.key("crystal", "scale", 0.0, (1, 1, 1))
    broken.key("crystal", "scale", 0.5, (0.4, 0.4, 0.4))
    broken.key("crystal", "scale", BROKEN_TIME, (0, 0, 0))
    broken.key("crystal", "rotation", 0.0, (0, 0, 0))
    broken.key("crystal", "rotation", BROKEN_TIME, (0, 0, 62))
    _door(broken, ((0.0, 0), (0.8, 74), (BROKEN_TIME, 96)))
    broken.key("roof", "rotation", 0.0, (0, 0, 0))
    broken.key("roof", "rotation", 0.9, (0, 0, -6))
    broken.key("roof", "rotation", BROKEN_TIME, (0, 0, -9))
    broken.key("lantern", "rotation", 0.0, (0, 0, 0))
    broken.key("lantern", "rotation", BROKEN_TIME, (44, 0, -20))
    broken.key("lantern", "position", 0.0, (0, 0, 0))
    broken.key("lantern", "position", BROKEN_TIME, (0, -8, 0))
    broken.key("swags", "rotation", 0.0, (0, 0, 0))
    broken.key("swags", "rotation", BROKEN_TIME, (18, 0, 0))
    return broken
