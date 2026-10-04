"""Gravebinder Cage — a hanging cage whose gate swings, spikes drop, soul glows.

Layout: an iron frame around the captive's own tile with a small roof, a
swinging gate on the north face, a ring of soul lanterns under the roof and a
crown of spikes that descends when the cage closes.
"""

from __future__ import annotations

from anim import Animation
from artkit import (
    BONE,
    IRON_BLACK,
    RUST,
    SOUL,
    SOUL_LIGHT,
    SOUL_PALE,
    STEEL,
    STEEL_DARK,
    STEEL_HIGHLIGHT,
    STEEL_LIGHT,
    bone,
    chain,
    iron_bar,
    soul_glow,
    spike as spike_art,
    steel_plate,
)
from model import Model
from pipeline import DeviceArt
from _kit import finalize, flat_face, shared_face

CAPTURE_DELAY = 1.25
CLOSE_DURATION = 1.75
CLOSED_PAUSE = 0.5
TORTURE_INTERVAL = 2.5
RELEASE_TIME = 1.0
BROKEN_TIME = 1.6


def build() -> DeviceArt:
    model = Model(
        identifier="geometry.cc_gravebinder_cage",
        texture_width=64,
        texture_height=128,
        visible_bounds=(2.0, 2.6),
        visible_offset=(0.0, 1.3, 0.0),
    )

    # ------------------------------------------------------------- frame --
    frame = model.bone("frame", [0, 0, 0])
    frame.cube(
        [-7, 0, -7], [14, 2, 14],
        {
            "up": shared_face(steel_plate(STEEL, rivets=True, grime=0.2, rust=0.4), "cage_floor"),
            "north": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_floor_side"),
            "south": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_floor_side"),
            "east": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_floor_side"),
            "west": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_floor_side"),
            "down": flat_face(IRON_BLACK, "iron_black"),
        },
    )
    for column, row, key in ((-7, -7, "cage_post"), (6, -7, "cage_post"), (-7, 6, "cage_post"), (6, 6, "cage_post")):
        frame.cube(
            [column, 2, row], [1, 20, 1],
            {
                "north": shared_face(iron_bar(STEEL), key),
                "south": shared_face(iron_bar(STEEL), key),
                "east": shared_face(iron_bar(STEEL_DARK, light=STEEL_LIGHT), "cage_post_side"),
                "west": shared_face(iron_bar(STEEL_DARK, light=STEEL_LIGHT), "cage_post_side"),
                "up": flat_face(IRON_BLACK, "iron_black"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Roof slab with a soul lantern.
    frame.cube(
        [-7, 22, -7], [14, 2, 14],
        {
            "up": shared_face(steel_plate(STEEL, rivets=True, grime=0.25, rust=0.4), "cage_roof"),
            "north": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_roof_side"),
            "south": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_roof_side"),
            "east": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_roof_side"),
            "west": shared_face(steel_plate(STEEL_DARK, rivets=True, grime=0.25, rust=0.5), "cage_roof_side"),
            "down": shared_face(steel_plate(STEEL_DARK, bands=2, grime=0.3), "cage_roof_under"),
        },
    )
    # Skull hanging from the roof: the cage's gravebinder seal.
    frame.cube(
        [-2, 19, 5], [4, 3, 1],
        {
            "north": shared_face(bone(), "cage_skull"),
            "south": flat_face(IRON_BLACK, "iron_black"),
            "east": shared_face(bone(BONE, dark=(120, 112, 96, 255)), "cage_skull_side"),
            "west": shared_face(bone(BONE, dark=(120, 112, 96, 255)), "cage_skull_side"),
            "up": flat_face(BONE, "bone_flat"),
            "down": flat_face((120, 112, 96, 255), "bone_dark_flat"),
        },
    )

    # -------------------------------------------------------------- bars --
    # Vertical bars on the two closed faces (east and west), leaving the south
    # wall solid so the captive is clearly held against it.
    for index, row in enumerate(range(-5, 6, 2)):
        for side, column in (("west", -7), ("east", 6)):
            frame.cube(
                [column, 2, row], [1, 20, 1],
                {
                    "north": shared_face(iron_bar(STEEL, light=STEEL_HIGHLIGHT), "cage_bar"),
                    "south": shared_face(iron_bar(STEEL, light=STEEL_HIGHLIGHT), "cage_bar"),
                    "east": shared_face(iron_bar(STEEL, light=STEEL_HIGHLIGHT), "cage_bar"),
                    "west": shared_face(iron_bar(STEEL, light=STEEL_HIGHLIGHT), "cage_bar"),
                    "up": flat_face(IRON_BLACK, "iron_black"),
                    "down": flat_face(IRON_BLACK, "iron_black"),
                },
            )
    frame.cube(
        [-6, 2, 5], [12, 20, 2],
        {
            "north": shared_face(steel_plate(STEEL_DARK, bands=4, grime=0.3, rust=0.5), "cage_back"),
            "south": shared_face(steel_plate(STEEL_DARK, bands=4, grime=0.3, rust=0.5), "cage_back"),
            "east": flat_face(STEEL_DARK, "steel_dark"),
            "west": flat_face(STEEL_DARK, "steel_dark"),
            "up": flat_face(IRON_BLACK, "iron_black"),
            "down": flat_face(IRON_BLACK, "iron_black"),
        },
    )

    # ------------------------------------------------------------ spikes --
    spikes = model.bone("spikes", [0, 22, 0], parent="frame")
    for column in (-5, -2, 1, 4):
        spikes.cube(
            [column, 17, -1], [1, 5, 1],
            {
                "north": shared_face(spike_art(STEEL, light=STEEL_HIGHLIGHT), "cage_spike"),
                "south": shared_face(spike_art(STEEL, light=STEEL_HIGHLIGHT), "cage_spike"),
                "east": flat_face(STEEL_DARK, "steel_dark"),
                "west": flat_face(STEEL_DARK, "steel_dark"),
                "up": flat_face(IRON_BLACK, "iron_black"),
                "down": shared_face(spike_art(STEEL_HIGHLIGHT, light=(240, 246, 255, 255)), "cage_spike_tip", flip_v=True),
            },
        )

    # -------------------------------------------------------------- gate --
    gate = model.bone("gate", [-6, 2, -6], parent="frame")
    # The gate is a barred door: verticals the captive can be seen through.
    for column in (-6, -3, 0, 3, 5):
        gate.cube(
            [column, 2, -7], [1, 20, 1],
            {
                "north": shared_face(iron_bar(STEEL, light=STEEL_HIGHLIGHT), "cage_bar"),
                "south": shared_face(iron_bar(STEEL_DARK, light=STEEL_LIGHT), "cage_bar_inner"),
                "east": shared_face(iron_bar(STEEL_DARK, light=STEEL_LIGHT), "cage_bar_side"),
                "west": shared_face(iron_bar(STEEL_DARK, light=STEEL_LIGHT), "cage_bar_side"),
                "up": flat_face(IRON_BLACK, "iron_black"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Gate frame rails.
    for row in (3, 19):
        gate.cube(
            [-6, row, -7], [12, 2, 1],
            {
                "north": shared_face(steel_plate(STEEL, rivets=True, grime=0.2), "cage_gate_rail"),
                "south": flat_face(STEEL_DARK, "steel_dark"),
                "east": flat_face(STEEL_DARK, "steel_dark"),
                "west": flat_face(STEEL_DARK, "steel_dark"),
                "up": flat_face(STEEL, "steel_flat"),
                "down": flat_face(IRON_BLACK, "iron_black"),
            },
        )
    # Padlock on the gate.
    gate.cube(
        [4, 9, -8], [3, 3, 1],
        {
            "north": shared_face(steel_plate(STEEL_LIGHT, rivets=False), "cage_lock"),
            "south": flat_face(IRON_BLACK, "iron_black"),
            "east": flat_face(STEEL_DARK, "steel_dark"),
            "west": flat_face(STEEL_DARK, "steel_dark"),
            "up": flat_face(STEEL, "steel_flat"),
            "down": flat_face(IRON_BLACK, "iron_black"),
        },
    )

    # ------------------------------------------------------------ lantern --
    lantern = model.bone("lantern", [0, 22, 0], parent="frame")
    lantern.cube(
        [-2, 19, -2], [4, 3, 4],
        {
            "north": shared_face(soul_glow(SOUL), "cage_soul"),
            "south": shared_face(soul_glow(SOUL), "cage_soul"),
            "east": shared_face(soul_glow(SOUL), "cage_soul"),
            "west": shared_face(soul_glow(SOUL), "cage_soul"),
            "up": shared_face(soul_glow(SOUL_PALE, light=SOUL_PALE, pale=(255, 255, 255, 255)), "cage_soul_top"),
            "down": shared_face(soul_glow(SOUL, light=SOUL, pale=SOUL_LIGHT), "cage_soul_bottom"),
        },
    )
    # Chain running from the roof into the lantern.
    lantern.cube(
        [0, 21, 0], [1, 1, 1],
        {
            "north": shared_face(chain(STEEL_DARK), "cage_lantern_chain"),
            "south": shared_face(chain(STEEL_DARK), "cage_lantern_chain"),
            "east": shared_face(chain(STEEL_DARK), "cage_lantern_chain"),
            "west": shared_face(chain(STEEL_DARK), "cage_lantern_chain"),
            "up": flat_face(IRON_BLACK, "iron_black"),
            "down": flat_face(IRON_BLACK, "iron_black"),
        },
    )

    animations = _animations()
    art = DeviceArt(
        slug="gravebinder_cage",
        display_name="Gravebinder Cage",
        model=model,
        animations=animations,
        state_animations={},
        particle="minecraft:basic_smoke_particle",
        accent_particle="minecraft:soul_particle",
    )
    return finalize(art)


def _animations() -> list[Animation]:
    animations: list[Animation] = []

    idle = Animation("animation.cc_gravebinder_cage.idle", 5.0, loop=True)
    idle.key("gate", "rotation", 0.0, (0, -74, 0))
    idle.key("gate", "rotation", 1.2, (0, -68, 0))
    idle.key("gate", "rotation", 2.5, (0, -76, 0))
    idle.key("gate", "rotation", 3.8, (0, -70, 0))
    idle.key("gate", "rotation", 5.0, (0, -74, 0))
    idle.key("lantern", "rotation", 0.0, (0, 0, 0))
    idle.key("lantern", "rotation", 2.5, (2.5, 0, 0))
    idle.key("lantern", "rotation", 5.0, (0, 0, 0))
    idle.key("spikes", "position", 0.0, (0, 0, 0))
    idle.key("spikes", "position", 5.0, (0, 0, 0))
    animations.append(idle)

    detect = Animation("animation.cc_gravebinder_cage.detect", CAPTURE_DELAY, loop=True)
    detect.key("gate", "rotation", 0.0, (0, -74, 0))
    detect.key("gate", "rotation", 0.6, (0, -128, 0))
    detect.key("gate", "rotation", 1.25, (0, -122, 0))
    detect.key("lantern", "rotation", 0.0, (0, 0, 0))
    detect.key("lantern", "rotation", 0.6, (0, 0, 7))
    detect.key("lantern", "rotation", 1.25, (0, 0, 4))
    detect.key("lantern", "scale", 0.0, (1, 1, 1))
    detect.key("lantern", "scale", 1.25, (1.15, 1.15, 1.15))
    animations.append(detect)

    close = Animation("animation.cc_gravebinder_cage.close", CLOSE_DURATION, loop=False)
    close.key("gate", "rotation", 0.0, (0, -122, 0))
    close.key("gate", "rotation", 0.5, (0, 8, 0))
    close.key("gate", "rotation", 0.7, (0, -6, 0))
    close.key("gate", "rotation", 0.95, (0, 0, 0))
    close.key("gate", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("frame", "rotation", 0.0, (0, 0, 0))
    close.key("frame", "rotation", 0.5, (0, 0, 0))
    close.key("frame", "rotation", 0.6, (0, 0, 3.5))
    close.key("frame", "rotation", 0.85, (0, 0, -1.5))
    close.key("frame", "rotation", CLOSE_DURATION, (0, 0, 0))
    close.key("spikes", "position", 0.0, (0, 5, 0))
    close.key("spikes", "position", 0.7, (0, -0.6, 0))
    close.key("spikes", "position", 0.95, (0, 0.25, 0))
    close.key("spikes", "position", CLOSE_DURATION, (0, 0, 0))
    close.key("lantern", "scale", 0.0, (1.15, 1.15, 1.15))
    close.key("lantern", "scale", 0.5, (0.85, 1.25, 0.85))
    close.key("lantern", "scale", 1.0, (1, 1, 1))
    close.key("lantern", "scale", CLOSE_DURATION, (1, 1, 1))
    animations.append(close)

    closed = Animation("animation.cc_gravebinder_cage.closed", CLOSED_PAUSE, loop=True)
    closed.key("gate", "rotation", 0.0, (0, 0, 0))
    closed.key("gate", "rotation", 0.25, (0, 1.4, 0))
    closed.key("gate", "rotation", 0.5, (0, 0, 0))
    closed.key("spikes", "position", 0.0, (0, 0, 0))
    closed.key("spikes", "position", 0.5, (0, 0, 0))
    animations.append(closed)

    torture = Animation("animation.cc_gravebinder_cage.torture", TORTURE_INTERVAL, loop=True)
    torture.key("frame", "scale", 0.0, (1, 1, 1))
    torture.key("frame", "scale", 0.5, (0.985, 1, 0.985))
    torture.key("frame", "scale", 1.05, (1, 1, 1))
    torture.key("frame", "scale", 1.6, (0.99, 1, 0.99))
    torture.key("frame", "scale", 2.5, (1, 1, 1))
    torture.key("frame", "rotation", 0.0, (0, 0, 0))
    torture.key("frame", "rotation", 0.7, (0, 0, 2.2))
    torture.key("frame", "rotation", 1.2, (0, 0, -1.6))
    torture.key("frame", "rotation", 1.9, (0, 0, 0))
    torture.key("frame", "rotation", 2.5, (0, 0, 0))
    torture.key("spikes", "position", 0.0, (0, 0, 0))
    torture.key("spikes", "position", 0.6, (0, 0.4, 0))
    torture.key("spikes", "position", 1.25, (0, 0, 0))
    torture.key("spikes", "position", 2.5, (0, 0, 0))
    torture.key("spikes", "scale", 0.0, (1, 1, 1))
    torture.key("spikes", "scale", 1.25, (1, 1.06, 1))
    torture.key("spikes", "scale", 2.5, (1, 1, 1))
    torture.key("lantern", "rotation", 0.0, (0, 0, -5))
    torture.key("lantern", "rotation", 1.25, (0, 0, 6))
    torture.key("lantern", "rotation", 2.5, (0, 0, -5))
    torture.key("lantern", "scale", 0.0, (1, 1, 1))
    torture.key("lantern", "scale", 1.25, (1.1, 1.1, 1.1))
    torture.key("lantern", "scale", 2.5, (1, 1, 1))
    animations.append(torture)

    strain = Animation("animation.cc_gravebinder_cage.strain", 0.6, loop=False)
    for time, angle in ((0.0, 0), (0.08, 5), (0.16, -4.5), (0.26, 3.5), (0.36, -2.5), (0.48, 1), (0.6, 0)):
        strain.key("frame", "rotation", time, (0, 0, angle))
    strain.key("gate", "rotation", 0.0, (0, 0, 0))
    strain.key("gate", "rotation", 0.1, (0, -6, 0))
    strain.key("gate", "rotation", 0.3, (0, 2, 0))
    strain.key("gate", "rotation", 0.55, (0, 0, 0))
    strain.key("lantern", "rotation", 0.0, (0, 0, 0))
    strain.key("lantern", "rotation", 0.15, (0, 0, 12))
    strain.key("lantern", "rotation", 0.35, (0, 0, -8))
    strain.key("lantern", "rotation", 0.6, (0, 0, 0))
    animations.append(strain)

    open_animation = Animation("animation.cc_gravebinder_cage.open", RELEASE_TIME + 0.4, loop=False)
    open_animation.key("gate", "rotation", 0.0, (0, 0, 0))
    open_animation.key("gate", "rotation", 0.35, (0, 18, 0))
    open_animation.key("gate", "rotation", 0.7, (0, -134, 0))
    open_animation.key("gate", "rotation", RELEASE_TIME + 0.4, (0, -126, 0))
    open_animation.key("spikes", "position", 0.0, (0, 0, 0))
    open_animation.key("spikes", "position", 0.8, (0, 5.5, 0))
    open_animation.key("spikes", "position", RELEASE_TIME + 0.4, (0, 5, 0))
    open_animation.key("frame", "rotation", 0.0, (0, 0, 0))
    open_animation.key("frame", "rotation", 0.6, (0, 0, -2))
    open_animation.key("frame", "rotation", RELEASE_TIME + 0.4, (0, 0, 0))
    open_animation.key("lantern", "scale", 0.0, (1, 1, 1))
    open_animation.key("lantern", "scale", RELEASE_TIME + 0.4, (1.25, 1.25, 1.25))
    animations.append(open_animation)

    released = Animation("animation.cc_gravebinder_cage.released", RELEASE_TIME, loop=False)
    released.key("gate", "rotation", 0.0, (0, -126, 0))
    released.key("gate", "rotation", 0.4, (0, -70, 0))
    released.key("gate", "rotation", 0.75, (0, -79, 0))
    released.key("gate", "rotation", RELEASE_TIME, (0, -74, 0))
    released.key("lantern", "scale", 0.0, (1.25, 1.25, 1.25))
    released.key("lantern", "scale", RELEASE_TIME, (1, 1, 1))
    animations.append(released)

    broken = Animation("animation.cc_gravebinder_cage.broken", BROKEN_TIME, loop="hold_on_last_frame")
    broken.key("frame", "rotation", 0.0, (0, 0, 0))
    broken.key("frame", "rotation", 0.8, (4, 0, 7))
    broken.key("frame", "rotation", BROKEN_TIME, (3, 0, 6))
    broken.key("frame", "position", 0.0, (0, 0, 0))
    broken.key("frame", "position", 1.0, (0, -2, 0))
    broken.key("frame", "position", BROKEN_TIME, (0, -2, 0))
    broken.key("gate", "rotation", 0.0, (0, -74, 0))
    broken.key("gate", "rotation", 0.6, (0, -46, 0))
    broken.key("gate", "rotation", BROKEN_TIME, (0, -52, 0))
    broken.key("spikes", "position", 0.0, (0, 0, 0))
    broken.key("spikes", "position", 0.6, (0, -8, 0))
    broken.key("spikes", "position", 1.0, (0, -21, 0))
    broken.key("spikes", "position", BROKEN_TIME, (0, -21, 0))
    broken.key("spikes", "rotation", 0.8, (0, 0, 0))
    broken.key("spikes", "rotation", BROKEN_TIME, (0, 0, 34))
    broken.key("lantern", "scale", 0.0, (1, 1, 1))
    broken.key("lantern", "scale", 0.5, (1.3, 1.3, 1.3))
    broken.key("lantern", "scale", 1.2, (0, 0, 0))
    broken.key("lantern", "scale", BROKEN_TIME, (0, 0, 0))
    broken.key("lantern", "position", 0.0, (0, 0, 0))
    broken.key("lantern", "position", 1.0, (0, -4, 0))
    broken.key("lantern", "position", BROKEN_TIME, (0, -22, 0))
    animations.append(broken)

    return animations
