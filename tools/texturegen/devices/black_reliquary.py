"""The Black Reliquary — obsidian tomb-chest with a levitating soul crystal.

Layout: a heavy plinth carrying a rune disc, an obsidian chamber, double doors
with a gem-set seal, a gilded lid, corner braziers burning soul fire and four
chains. The crystal floats above the lid, and the rune disc turns while the
device is working.
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
    SOUL,
    SOUL_LIGHT,
    SOUL_PALE,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    chain,
    cloth,
    crystal,
    gold_trim,
    netherite_plate,
    obsidian,
    soul_glow,
    steel_plate,
)
from model import Face, Model
from pipeline import DeviceArt
from _kit import finalize, flat_face, shared_face

CAPTURE_DELAY = 1.75
CLOSE_DURATION = 2.25
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 2.0
RELEASE_TIME = 1.4
BROKEN_TIME = 2.0

RUNE_DISC = [
    "....####....",
    "..##....##..",
    ".#..####..#.",
    "#..##..##..#",
    "#.##.GG.##.#",
    "#.##.GG.##.#",
    "#..##GG##..#",
    ".#..####..#.",
    "..##....##..",
    "....####....",
]


def _door(hinge_left: bool):
    """Obsidian door leaf: gilded frame, rune ring, and a gem-set seal."""

    def paint(painter) -> None:
        obsidian()(painter)
        width, height = painter.rect.width, painter.rect.height
        # Gilded frame.
        painter.outline(GOLD, inset=0)
        painter.outline(GOLD_LIGHT, inset=1)
        painter.outline(OBSIDIAN_DARK, inset=2)
        # Rune ring in the upper half; the gem sits in the middle of it.
        center_column = width // 2
        center_row = max(4, height // 3)
        radius = max(2, min(width, height) // 5)
        for row in range(height):
            for column in range(width):
                distance = ((column - center_column) ** 2 + (row - center_row) ** 2) ** 0.5
                if abs(distance - radius) < 0.9:
                    painter.blend_px(column, row, SOUL, 0.55)
                elif distance < radius - 1:
                    painter.blend_px(column, row, OBSIDIAN_DARK, 0.5)
        # Gem seal: soul fire behind faceted glass.
        gem_row = center_row
        for offset in range(-2, 3):
            for row_offset in range(-2, 3):
                if abs(offset) + abs(row_offset) <= 2:
                    painter.px(
                        max(0, min(width - 1, center_column + offset)),
                        max(0, min(height - 1, gem_row + row_offset)),
                        SOUL_LIGHT if abs(offset) + abs(row_offset) < 2 else SOUL,
                    )
        painter.px(center_column, gem_row - 2, SOUL_PALE)
        painter.px(center_column, gem_row + 2, CRYSTAL_DARK)
        # Netherite bands and a ring handle.
        for row in (4, height - 5):
            painter.box(2, row, width - 4, 1, NETHERITE)
            painter.box(2, row + 1, width - 4, 1, NETHERITE_LIGHT)
            painter.rivets(GOLD, spacing=4, inset=3)
        handle_column = 2 if hinge_left else width - 3
        for row in range(height // 2 - 2, height // 2 + 3):
            painter.px(min(width - 1, handle_column), row, GOLD_LIGHT)
        painter.bevel(CRYSTAL_DARK, OBSIDIAN_DARK, alpha=150)

    return paint


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_black_reliquary",
        texture_width=64,
        texture_height=128,
        visible_bounds=(2.4, 3.2),
        visible_offset=(0.0, 1.6, 0.0),
    )

    # ------------------------------------------------------------- plinth --
    base = model.bone("base", [0, 0, 0])
    base.cube(
        [-8, 0, -8], [16, 3, 16],
        {
            "up": shared_face(obsidian(OBSIDIAN, facet=OBSIDIAN_FACET), "reliquary_plinth_top"),
            "north": shared_face(gold_trim(), "reliquary_gold"),
            "south": shared_face(gold_trim(), "reliquary_gold"),
            "east": shared_face(gold_trim(), "reliquary_gold"),
            "west": shared_face(gold_trim(), "reliquary_gold"),
            "down": shared_face(obsidian(OBSIDIAN_DARK, facet=OBSIDIAN), "reliquary_plinth_bottom"),
        },
    )
    # Netherite corner posts.
    for column, row in ((-8, -8), (6, -8), (-8, 6), (6, 6)):
        base.cube(
            [column, 3, row], [2, 21, 2],
            {
                "north": shared_face(netherite_plate(), "reliquary_post"),
                "south": shared_face(netherite_plate(), "reliquary_post"),
                "east": shared_face(netherite_plate(), "reliquary_post"),
                "west": shared_face(netherite_plate(), "reliquary_post"),
                "up": flat_face(NETHERITE_LIGHT, "netherite_light"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Back wall and side walls.
    base.cube(
        [-6, 3, 6], [12, 21, 2],
        {
            "north": shared_face(obsidian(OBSIDIAN_LIGHT, facet=OBSIDIAN_FACET), "reliquary_wall"),
            "south": shared_face(obsidian(OBSIDIAN_LIGHT, facet=OBSIDIAN_FACET), "reliquary_wall"),
            "east": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
            "west": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
            "up": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
            "down": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
        },
    )
    for column in (-6, 4):
        base.cube(
            [column, 3, -6], [2, 21, 12],
            {
                "north": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                "south": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                "east": shared_face(obsidian(OBSIDIAN_LIGHT, facet=OBSIDIAN_FACET), "reliquary_wall"),
                "west": shared_face(obsidian(OBSIDIAN_LIGHT, facet=OBSIDIAN_FACET), "reliquary_wall"),
                "up": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                "down": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
            },
        )

    # ----------------------------------------------------------- rune disc --
    rune = model.bone("rune_disc", [0, 3, 0], parent="base")
    rune.cube(
        [-5, 3, -5], [10, 1, 10],
        {
            "up": shared_face(_rune_disc(), "reliquary_rune"),
            "down": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
            "north": shared_face(gold_trim(GOLD, light=GOLD_LIGHT), "reliquary_rune_edge"),
            "south": shared_face(gold_trim(GOLD, light=GOLD_LIGHT), "reliquary_rune_edge"),
            "east": shared_face(gold_trim(GOLD, light=GOLD_LIGHT), "reliquary_rune_edge"),
            "west": shared_face(gold_trim(GOLD, light=GOLD_LIGHT), "reliquary_rune_edge"),
        },
    )

    # ------------------------------------------------------------ the lid --
    top = model.bone("top", [0, 24, 0], parent="base")
    top.cube(
        [-8, 24, -8], [16, 3, 16],
        {
            "up": shared_face(obsidian(OBSIDIAN, facet=OBSIDIAN_LIGHT), "reliquary_lid_top"),
            "north": shared_face(gold_trim(), "reliquary_gold"),
            "south": shared_face(gold_trim(), "reliquary_gold"),
            "east": shared_face(gold_trim(), "reliquary_gold"),
            "west": shared_face(gold_trim(), "reliquary_gold"),
            "down": shared_face(obsidian(OBSIDIAN_DARK, facet=OBSIDIAN), "reliquary_lid_under"),
        },
    )
    # Eave trim so the lid overhangs the doors.
    for row in (-9, 7):
        top.cube(
            [-9, 22, row], [18, 2, 2],
            {
                "north": shared_face(netherite_plate(), "reliquary_eave"),
                "south": shared_face(netherite_plate(), "reliquary_eave"),
                "east": flat_face(NETHERITE, "netherite"),
                "west": flat_face(NETHERITE, "netherite"),
                "up": flat_face(NETHERITE_LIGHT, "netherite_light"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )

    # -------------------------------------------------------------- doors --
    for name, mirrored in (("door_left", False), ("door_right", True)):
        hinge = -8 if not mirrored else 8
        door = model.bone(name, [hinge, 3, -8], parent="base")
        door.cube(
            [-8 if not mirrored else 0, 3, -8], [8, 21, 2],
            {
                "north": shared_face(_door(not mirrored), "reliquary_door", flip_u=mirrored),
                "south": shared_face(obsidian(OBSIDIAN_DARK, facet=OBSIDIAN), "reliquary_door_inner", flip_u=mirrored),
                "east": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                "west": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                "up": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                "down": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
            },
        )
        # Hinge straps.
        for row in (6, 18):
            door.cube(
                [-8 if not mirrored else 5, row, -9], [3, 2, 1],
                {
                    "north": shared_face(gold_trim(), "reliquary_hinge"),
                    "south": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                    "east": flat_face(GOLD, "gold"),
                    "west": flat_face(GOLD, "gold"),
                    "up": flat_face(GOLD_LIGHT, "gold_light"),
                    "down": flat_face(OBSIDIAN_DARK, "obsidian_dark"),
                },
            )

    # ------------------------------------------------------------ crystal --
    body = model.bone("crystal", [0, 29, 0], parent="top")
    body.cube(
        [-2, 27, -2], [4, 5, 4],
        {
            "north": shared_face(crystal(), "reliquary_crystal"),
            "south": shared_face(crystal(), "reliquary_crystal"),
            "east": shared_face(crystal(), "reliquary_crystal"),
            "west": shared_face(crystal(), "reliquary_crystal"),
            "up": shared_face(crystal(CRYSTAL_LIGHT, light=(255, 255, 255, 255), dark=CRYSTAL), "reliquary_crystal_top"),
            "down": shared_face(crystal(CRYSTAL_DARK, light=CRYSTAL, dark=OBSIDIAN_DARK), "reliquary_crystal_bottom"),
        },
    )
    for column, row in ((-3, -3), (1, -3), (-3, 1), (1, 1)):
        body.cube(
            [column, 31, row], [2, 2, 2],
            {
                "north": shared_face(crystal(CRYSTAL_LIGHT, light=(255, 255, 255, 255), dark=CRYSTAL), "reliquary_shard"),
                "south": shared_face(crystal(CRYSTAL_LIGHT, light=(255, 255, 255, 255), dark=CRYSTAL), "reliquary_shard"),
                "east": shared_face(crystal(CRYSTAL_LIGHT, light=(255, 255, 255, 255), dark=CRYSTAL), "reliquary_shard"),
                "west": shared_face(crystal(CRYSTAL_LIGHT, light=(255, 255, 255, 255), dark=CRYSTAL), "reliquary_shard"),
                "up": shared_face(crystal(SOUL_PALE, light=(255, 255, 255, 255), dark=CRYSTAL_LIGHT), "reliquary_shard_top"),
                "down": flat_face(CRYSTAL_DARK, "crystal_dark"),
            },
        )

    # ------------------------------------------------------------ braziers --
    for name, column, row in (("brazier_left", -7, 5), ("brazier_right", 4, 5)):
        brazier = model.bone(name, [column + 1.5, 24, row + 1.5], parent="top")
        brazier.cube(
            [column, 24, row], [3, 3, 3],
            {
                "north": shared_face(steel_plate(STEEL_DARK, rivets=True, rust=0.5), "reliquary_brazier"),
                "south": shared_face(steel_plate(STEEL_DARK, rivets=True, rust=0.5), "reliquary_brazier"),
                "east": shared_face(steel_plate(STEEL_DARK, rivets=True, rust=0.5), "reliquary_brazier"),
                "west": shared_face(steel_plate(STEEL_DARK, rivets=True, rust=0.5), "reliquary_brazier"),
                "up": shared_face(soul_glow(SOUL), "reliquary_flame"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Hanging chains at the front corners.
    for name, column in (("chain_left", -9), ("chain_right", 8)):
        link = model.bone(name, [column + 0.5, 23, -9], parent="top")
        link.cube(
            [column, 13, -9], [1, 10, 1],
            {
                "north": shared_face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_LIGHT), "reliquary_chain"),
                "south": shared_face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_LIGHT), "reliquary_chain"),
                "east": shared_face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_LIGHT), "reliquary_chain"),
                "west": shared_face(chain(STEEL_DARK, dark=IRON_BLACK, light=STEEL_LIGHT), "reliquary_chain"),
                "up": flat_face(IRON_BLACK, "iron_black"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )

    animations = _animations()
    art = DeviceArt(
        slug="black_reliquary",
        display_name="The Black Reliquary",
        model=model,
        animations=animations,
        state_animations={},
        particle="minecraft:soul_particle",
        accent_particle="minecraft:basic_smoke_particle",
    )
    return finalize(art)


def _rune_disc():
    """A turning gilded rune disc; the gaps stay transparent."""

    def paint(painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        center = (width - 1) / 2, (height - 1) / 2
        for row in range(height):
            for column in range(width):
                distance = ((column - center[0]) ** 2 + (row - center[1]) ** 2) ** 0.5
                if distance > width / 2 - 0.5:
                    continue
                painter.px(column, row, OBSIDIAN_DARK if distance < width / 2 - 1.2 else GOLD)
        for row_index, line in enumerate(RUNE_DISC):
            if row_index >= height:
                break
            for column_index, char in enumerate(line):
                if column_index >= width:
                    break
                if char == "#":
                    painter.blend_px(column_index, row_index, SOUL, 0.75)
                elif char == "G":
                    painter.blend_px(column_index, row_index, GOLD_LIGHT, 0.9)
        painter.noise(OBSIDIAN, [OBSIDIAN_LIGHT, SOUL], density=0.12)

    return paint


def _animations() -> list[Animation]:
    animations: list[Animation] = []

    idle = Animation("animation.cc_black_reliquary.idle", 4.0, loop=True)
    idle.key("crystal", "rotation", 0.0, (0, 0, 0))
    idle.key("crystal", "rotation", 4.0, (0, 360, 0))
    idle.key("crystal", "position", 0.0, (0, 0, 0))
    idle.key("crystal", "position", 2.0, (0, 0.8, 0))
    idle.key("crystal", "position", 4.0, (0, 0, 0))
    idle.key("rune_disc", "rotation", 0.0, (0, 0, 0))
    idle.key("rune_disc", "rotation", 4.0, (0, 45, 0))
    idle.key("brazier_left", "scale", 0.0, (1, 1, 1))
    idle.key("brazier_left", "scale", 1.0, (1, 1.12, 1))
    idle.key("brazier_left", "scale", 2.0, (1, 0.96, 1))
    idle.key("brazier_left", "scale", 3.0, (1, 1.08, 1))
    idle.key("brazier_left", "scale", 4.0, (1, 1, 1))
    idle.key("brazier_right", "scale", 0.0, (1, 1, 1))
    idle.key("brazier_right", "scale", 1.4, (1, 1.14, 1))
    idle.key("brazier_right", "scale", 2.4, (1, 0.94, 1))
    idle.key("brazier_right", "scale", 3.4, (1, 1.06, 1))
    idle.key("brazier_right", "scale", 4.0, (1, 1, 1))
    idle.key("chain_left", "rotation", 0.0, (0, 0, 0))
    idle.key("chain_left", "rotation", 2.0, (0, 0, 3))
    idle.key("chain_left", "rotation", 4.0, (0, 0, 0))
    idle.key("chain_right", "rotation", 0.0, (0, 0, 0))
    idle.key("chain_right", "rotation", 2.0, (0, 0, -3))
    idle.key("chain_right", "rotation", 4.0, (0, 0, 0))
    animations.append(idle)

    detect = Animation("animation.cc_black_reliquary.detect", CAPTURE_DELAY, loop=True)
    detect.key("door_left", "rotation", 0.0, (0, 0, 0))
    detect.key("door_left", "rotation", 0.8, (0, -24, 0))
    detect.key("door_left", "rotation", 1.75, (0, -21, 0))
    detect.key("door_right", "rotation", 0.0, (0, 0, 0))
    detect.key("door_right", "rotation", 0.8, (0, 24, 0))
    detect.key("door_right", "rotation", 1.75, (0, 21, 0))
    detect.key("crystal", "scale", 0.0, (1, 1, 1))
    detect.key("crystal", "scale", 0.9, (1.25, 1.25, 1.25))
    detect.key("crystal", "scale", 1.75, (1.35, 1.35, 1.35))
    detect.key("crystal", "rotation", 0.0, (0, 0, 0))
    detect.key("crystal", "rotation", 1.75, (0, 140, 0))
    detect.key("rune_disc", "rotation", 0.0, (0, 0, 0))
    detect.key("rune_disc", "rotation", 1.75, (0, 90, 0))
    detect.key("brazier_left", "scale", 0.0, (1, 1, 1))
    detect.key("brazier_left", "scale", 0.9, (1.2, 1.4, 1.2))
    detect.key("brazier_left", "scale", 1.75, (1.3, 1.5, 1.3))
    detect.key("brazier_right", "scale", 0.0, (1, 1, 1))
    detect.key("brazier_right", "scale", 0.9, (1.2, 1.4, 1.2))
    detect.key("brazier_right", "scale", 1.75, (1.3, 1.5, 1.3))
    animations.append(detect)

    close = Animation("animation.cc_black_reliquary.close", CLOSE_DURATION, loop=False)
    close.key("door_left", "rotation", 0.0, (0, -21, 0))
    close.key("door_left", "rotation", 0.8, (0, 6, 0))
    close.key("door_left", "rotation", 1.1, (0, -3, 0))
    close.key("door_left", "rotation", 1.45, (0, 0, 0))
    close.key("door_left", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("door_right", "rotation", 0.0, (0, 21, 0))
    close.key("door_right", "rotation", 0.8, (0, -6, 0))
    close.key("door_right", "rotation", 1.1, (0, 3, 0))
    close.key("door_right", "rotation", 1.45, (0, 0, 0))
    close.key("door_right", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("crystal", "scale", 0.0, (1.35, 1.35, 1.35))
    close.key("crystal", "scale", 0.8, (0.85, 1.3, 0.85))
    close.key("crystal", "scale", 1.2, (1.1, 0.95, 1.1))
    close.key("crystal", "scale", CLOSE_DURATION, (1, 1, 1))
    close.key("crystal", "rotation", 0.0, (0, 140, 0))
    close.key("crystal", "rotation", CLOSE_DURATION, (0, 500, 0))
    close.key("base", "rotation", 0.0, (0, 0, 0))
    close.key("base", "rotation", 0.8, (0, 0, 1.4))
    close.key("base", "rotation", 1.3, (0, 0, -0.8))
    close.key("base", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("brazier_left", "scale", 0.0, (1.3, 1.5, 1.3))
    close.key("brazier_left", "scale", CLOSE_DURATION, (1, 1, 1))
    close.key("brazier_right", "scale", 0.0, (1.3, 1.5, 1.3))
    close.key("brazier_right", "scale", CLOSE_DURATION, (1, 1, 1))
    animations.append(close)

    closed = Animation("animation.cc_black_reliquary.closed", CLOSED_PAUSE, loop=True)
    closed.key("door_left", "rotation", 0.0, (0, 0, 0))
    closed.key("door_left", "rotation", 0.25, (0, -0.8, 0))
    closed.key("door_left", "rotation", 0.5, (0, 0, 0))
    closed.key("door_right", "rotation", 0.0, (0, 0, 0))
    closed.key("door_right", "rotation", 0.25, (0, 0.8, 0))
    closed.key("door_right", "rotation", 0.5, (0, 0, 0))
    closed.key("crystal", "scale", 0.0, (1, 1, 1))
    closed.key("crystal", "scale", 0.5, (1.02, 1.02, 1.02))
    animations.append(closed)

    torture = Animation("animation.cc_black_reliquary.torture", TORTURE_INTERVAL, loop=True)
    torture.key("crystal", "rotation", 0.0, (0, 0, 0))
    torture.key("crystal", "rotation", 2.0, (0, 720, 0))
    torture.key("crystal", "position", 0.0, (0, 0, 0))
    torture.key("crystal", "position", 0.5, (0, 1.4, 0))
    torture.key("crystal", "position", 1.0, (0, 0.2, 0))
    torture.key("crystal", "position", 1.5, (0, 1.0, 0))
    torture.key("crystal", "position", 2.0, (0, 0, 0))
    torture.key("crystal", "scale", 0.0, (1, 1, 1))
    torture.key("crystal", "scale", 1.0, (1.12, 1.12, 1.12))
    torture.key("crystal", "scale", 2.0, (1, 1, 1))
    torture.key("rune_disc", "rotation", 0.0, (0, 0, 0))
    torture.key("rune_disc", "rotation", 2.0, (0, 90, 0))
    torture.key("door_left", "rotation", 0.0, (0, 0, 0))
    torture.key("door_left", "rotation", 0.6, (0, -2.6, 0))
    torture.key("door_left", "rotation", 1.2, (0, 0.8, 0))
    torture.key("door_left", "rotation", 2.0, (0, 0, 0))
    torture.key("door_right", "rotation", 0.0, (0, 0, 0))
    torture.key("door_right", "rotation", 0.6, (0, 2.6, 0))
    torture.key("door_right", "rotation", 1.2, (0, -0.8, 0))
    torture.key("door_right", "rotation", 2.0, (0, 0, 0))
    torture.key("base", "rotation", 0.0, (0, 0, 0))
    torture.key("base", "rotation", 0.4, (0, 0, 1.2))
    torture.key("base", "rotation", 1.0, (0, 0, -1))
    torture.key("base", "rotation", 1.6, (0, 0, 0))
    torture.key("base", "rotation", 2.0, (0, 0, 0))
    torture.key("brazier_left", "scale", 0.0, (1, 1.2, 1))
    torture.key("brazier_left", "scale", 1.0, (1.1, 1.5, 1.1))
    torture.key("brazier_left", "scale", 2.0, (1, 1.2, 1))
    torture.key("brazier_right", "scale", 0.0, (1, 1.1, 1))
    torture.key("brazier_right", "scale", 1.0, (1.05, 1.45, 1.05))
    torture.key("brazier_right", "scale", 2.0, (1, 1.1, 1))
    torture.key("chain_left", "rotation", 0.0, (0, 0, -4))
    torture.key("chain_left", "rotation", 1.0, (0, 0, 5))
    torture.key("chain_left", "rotation", 2.0, (0, 0, -4))
    torture.key("chain_right", "rotation", 0.0, (0, 0, 4))
    torture.key("chain_right", "rotation", 1.0, (0, 0, -5))
    torture.key("chain_right", "rotation", 2.0, (0, 0, 4))
    animations.append(torture)

    strain = Animation("animation.cc_black_reliquary.strain", 0.6, loop=False)
    for time, angle in ((0.0, 0), (0.08, 3.6), (0.16, -3.2), (0.26, 2.4), (0.36, -1.6), (0.5, 0.8), (0.6, 0)):
        strain.key("base", "rotation", time, (0, 0, angle))
    strain.key("door_left", "rotation", 0.0, (0, 0, 0))
    strain.key("door_left", "rotation", 0.1, (0, -3, 0))
    strain.key("door_left", "rotation", 0.3, (0, 0.8, 0))
    strain.key("door_left", "rotation", 0.55, (0, 0, 0))
    strain.key("door_right", "rotation", 0.0, (0, 0, 0))
    strain.key("door_right", "rotation", 0.1, (0, 3, 0))
    strain.key("door_right", "rotation", 0.3, (0, -0.8, 0))
    strain.key("door_right", "rotation", 0.55, (0, 0, 0))
    strain.key("crystal", "scale", 0.0, (1, 1, 1))
    strain.key("crystal", "scale", 0.12, (1.16, 1.16, 1.16))
    strain.key("crystal", "scale", 0.35, (1.02, 1.02, 1.02))
    strain.key("crystal", "scale", 0.6, (1, 1, 1))
    animations.append(strain)

    open_animation = Animation("animation.cc_black_reliquary.open", RELEASE_TIME + 0.5, loop=False)
    open_animation.key("door_left", "rotation", 0.0, (0, 0, 0))
    open_animation.key("door_left", "rotation", 0.5, (0, -104, 0))
    open_animation.key("door_left", "rotation", 0.9, (0, -96, 0))
    open_animation.key("door_left", "rotation", RELEASE_TIME + 0.5, (0, -100, 0))
    open_animation.key("door_right", "rotation", 0.0, (0, 0, 0))
    open_animation.key("door_right", "rotation", 0.5, (0, 104, 0))
    open_animation.key("door_right", "rotation", 0.9, (0, 96, 0))
    open_animation.key("door_right", "rotation", RELEASE_TIME + 0.5, (0, 100, 0))
    open_animation.key("crystal", "position", 0.0, (0, 0, 0))
    open_animation.key("crystal", "position", 0.7, (0, 2.6, 0))
    open_animation.key("crystal", "position", RELEASE_TIME + 0.5, (0, 1.6, 0))
    open_animation.key("crystal", "rotation", 0.0, (0, 0, 0))
    open_animation.key("crystal", "rotation", RELEASE_TIME + 0.5, (0, 240, 0))
    open_animation.key("crystal", "scale", 0.0, (1, 1, 1))
    open_animation.key("crystal", "scale", 0.7, (1.2, 1.2, 1.2))
    open_animation.key("crystal", "scale", RELEASE_TIME + 0.5, (1.05, 1.05, 1.05))
    open_animation.key("rune_disc", "rotation", 0.0, (0, 0, 0))
    open_animation.key("rune_disc", "rotation", RELEASE_TIME + 0.5, (0, 180, 0))
    open_animation.key("brazier_left", "scale", 0.0, (1, 1, 1))
    open_animation.key("brazier_left", "scale", 0.7, (1.3, 1.6, 1.3))
    open_animation.key("brazier_left", "scale", RELEASE_TIME + 0.5, (1, 1, 1))
    open_animation.key("brazier_right", "scale", 0.0, (1, 1, 1))
    open_animation.key("brazier_right", "scale", 0.7, (1.3, 1.6, 1.3))
    open_animation.key("brazier_right", "scale", RELEASE_TIME + 0.5, (1, 1, 1))
    animations.append(open_animation)

    released = Animation("animation.cc_black_reliquary.released", RELEASE_TIME, loop=False)
    released.key("door_left", "rotation", 0.0, (0, -100, 0))
    released.key("door_left", "rotation", 0.5, (0, -94, 0))
    released.key("door_left", "rotation", RELEASE_TIME, (0, -97, 0))
    released.key("door_right", "rotation", 0.0, (0, 100, 0))
    released.key("door_right", "rotation", 0.5, (0, 94, 0))
    released.key("door_right", "rotation", RELEASE_TIME, (0, 97, 0))
    released.key("crystal", "position", 0.0, (0, 1.6, 0))
    released.key("crystal", "position", RELEASE_TIME, (0, 0, 0))
    released.key("crystal", "scale", 0.0, (1.05, 1.05, 1.05))
    released.key("crystal", "scale", RELEASE_TIME, (1, 1, 1))
    animations.append(released)

    broken = Animation("animation.cc_black_reliquary.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("crystal", "scale", 0.0, (1, 1, 1))
    broken.key("crystal", "scale", 0.4, (1.6, 1.6, 1.6))
    broken.key("crystal", "scale", 0.8, (0, 0, 0))
    broken.key("crystal", "scale", BROKEN_TIME, (0, 0, 0))
    broken.key("crystal", "position", 0.0, (0, 0, 0))
    broken.key("crystal", "position", 0.8, (0, -3, 0))
    broken.key("crystal", "position", BROKEN_TIME, (0, -24, 0))
    broken.key("crystal", "rotation", 0.0, (0, 0, 0))
    broken.key("crystal", "rotation", BROKEN_TIME, (0, 220, 30))
    broken.key("door_left", "rotation", 0.0, (0, 0, 0))
    broken.key("door_left", "rotation", 1.0, (0, -62, 0))
    broken.key("door_left", "rotation", BROKEN_TIME, (0, -54, 0))
    broken.key("door_right", "rotation", 0.0, (0, 0, 0))
    broken.key("door_right", "rotation", 1.0, (0, 74, 0))
    broken.key("door_right", "rotation", BROKEN_TIME, (0, 66, 0))
    broken.key("top", "rotation", 0.0, (0, 0, 0))
    broken.key("top", "rotation", 1.4, (2, 0, -6))
    broken.key("top", "rotation", BROKEN_TIME, (3, 0, -5))
    broken.key("brazier_left", "rotation", 0.0, (0, 0, 0))
    broken.key("brazier_left", "rotation", 1.2, (0, 0, -96))
    broken.key("brazier_left", "rotation", BROKEN_TIME, (0, 0, -88))
    broken.key("brazier_left", "position", 0.0, (0, 0, 0))
    broken.key("brazier_left", "position", 1.2, (2, -3, 0))
    broken.key("brazier_left", "position", BROKEN_TIME, (2, -3, 0))
    broken.key("brazier_right", "rotation", 0.0, (0, 0, 0))
    broken.key("brazier_right", "rotation", 1.2, (0, 0, 94))
    broken.key("brazier_right", "rotation", BROKEN_TIME, (0, 0, 86))
    broken.key("brazier_right", "position", 0.0, (0, 0, 0))
    broken.key("brazier_right", "position", 1.2, (-2, -3, 0))
    broken.key("brazier_right", "position", BROKEN_TIME, (-2, -3, 0))
    broken.key("rune_disc", "rotation", 0.0, (0, 0, 0))
    broken.key("rune_disc", "rotation", BROKEN_TIME, (0, 120, 0))
    broken.key("chain_left", "rotation", 0.0, (0, 0, 0))
    broken.key("chain_left", "rotation", 0.9, (0, 0, -20))
    broken.key("chain_left", "rotation", BROKEN_TIME, (0, 0, -14))
    broken.key("chain_right", "rotation", 0.0, (0, 0, 0))
    broken.key("chain_right", "rotation", 0.9, (0, 0, 18))
    broken.key("chain_right", "rotation", BROKEN_TIME, (0, 0, 12))
    animations.append(broken)

    return animations
