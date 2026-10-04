"""Build the shipped Cursed Contraptions assets from the Python definitions.

Run from the repository root::

    python3 tools/texturegen/build_assets.py

Writes (and validates) the resource-pack geometry, textures, animations and
animation controllers, plus the behavior-pack entity files. Everything it emits
is ordinary pack content; the generator is dev-only and never ships.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "devices"))

import zlib

from anim import write_animations  # noqa: E402
from model import bake_atlas, face_pixel_size, pack_faces, write_geometry  # noqa: E402
from canvas import Painter, Rect, rgba  # noqa: E402
from png_io import Image, png_color_type  # noqa: E402
from artkit import (  # noqa: E402
    BONE, BONE_DARK, CRYSTAL, CRYSTAL_DARK, CRYSTAL_LIGHT, GOLD, GOLD_LIGHT,
    IRON_BLACK, OBSIDIAN, OBSIDIAN_DARK, OBSIDIAN_FACET, OBSIDIAN_LIGHT, ROPE,
    ROPE_DARK, RUST, SOUL, SOUL_PALE, STEEL, STEEL_DARK, STEEL_HIGHLIGHT,
    STEEL_LIGHT, STEEL_MID, WOOD, WOOD_DARK, WOOD_LIGHT, WOOD_MID,
    obsidian, planks, steel_plate,
)  # noqa: E402
from pipeline import (  # noqa: E402
    DEVICE_STATES,
    DeviceArt,
    client_entity_json,
    controller_json,
    write_json,
)

BP = ROOT / "behavior_pack"
RP = ROOT / "resource_pack"

DEVICE_MODULES = (
    "iron_maiden",
    "cursed_stocks",
    "gravebinder_cage",
    "regret_rack",
    "black_reliquary",
)

# Collision footprint per device, in blocks. The device occupies its own tile
# so the captive is contained inside the contraption.
COLLISION = {
    "iron_maiden": {"width": 1.3, "height": 2.5},
    "cursed_stocks": {"width": 1.8, "height": 1.0},
    "gravebinder_cage": {"width": 1.5, "height": 2.5},
    "regret_rack": {"width": 2.0, "height": 0.9},
    "black_reliquary": {"width": 1.7, "height": 2.8},
}

# Where the captive's feet rest relative to the device origin.
SEAT_HEIGHT = {
    "iron_maiden": 0.0,
    "cursed_stocks": 0.0,
    "gravebinder_cage": 0.0,
    "regret_rack": 0.35,
    "black_reliquary": 0.0,
}

FAMILY = {
    "iron_maiden": "iron_maiden",
    "cursed_stocks": "cursed_stocks",
    "gravebinder_cage": "gravebinder_cage",
    "regret_rack": "regret_rack",
    "black_reliquary": "black_reliquary",
}

DISPLAY_NAMES = {
    "iron_maiden": "Iron Maiden",
    "cursed_stocks": "Cursed Stocks",
    "gravebinder_cage": "Gravebinder Cage",
    "regret_rack": "The Regret Rack",
    "black_reliquary": "The Black Reliquary",
}

# Interaction prompts. The stock "action.interact.*" namespace is owned by the
# vanilla strings, so custom keys live in the pack's own lang file.
INTERACT_KEYS = {
    "idle": "action.cc.use_device",
    "occupied": "action.cc.rescue_captive",
}

BLOCK_MATERIALS = {
    "iron_maiden": ("cc_iron_maiden_side", "metal"),
    "cursed_stocks": ("cc_cursed_stocks_side", "wood"),
    "gravebinder_cage": ("cc_gravebinder_cage_side", "metal"),
    "regret_rack": ("cc_regret_rack_side", "wood"),
    "black_reliquary": ("cc_black_reliquary_side", "stone"),
}

ITEM_ICONS = {
    "iron_maiden": "cc_item_iron_maiden",
    "cursed_stocks": "cc_item_cursed_stocks",
    "gravebinder_cage": "cc_item_gravebinder_cage",
    "regret_rack": "cc_item_regret_rack",
    "black_reliquary": "cc_item_black_reliquary",
}


def behavior_entity(art: DeviceArt) -> dict:
    slug = art.slug
    collision = COLLISION[slug]

    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": f"cc:{slug}",
                "is_spawnable": False,
                "is_summonable": True,
                "is_experimental": False,
                "properties": {
                    "cc:state": {
                        "type": "enum",
                        "values": list(DEVICE_STATES),
                        "default": "idle",
                        "client_sync": True,
                    },
                    "cc:durability": {
                        "type": "int",
                        "range": [0, 1000],
                        "default": 100,
                        "client_sync": True,
                    },
                    "cc:armor_count": {
                        "type": "int",
                        "range": [0, 4],
                        "default": 0,
                        "client_sync": True,
                    },
                },
            },
            "components": {
                "minecraft:type_family": {"family": ["cc_device", FAMILY[slug], "inanimate"]},
                "minecraft:collision_box": {"width": collision["width"], "height": collision["height"]},
                # A device is a fixture, not a creature: no gravity (so a device
                # can never sink through a floor that unloads for a tick) and no
                # collision (so the device never squeezes a captive out of its
                # own seat, which was feeding the v0.1.2 stutter report). The
                # hitbox stays targetable for attacks and interaction.
                "minecraft:physics": {
                    "has_gravity": False,
                    "has_collision": False,
                    "push_towards_closest_space": False,
                },
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:health": {"value": 1000, "max": 1000},
                "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": True}]},
                "minecraft:persistent": {},
                "minecraft:breathable": {
                    "total_supply": 999,
                    "suffocate_time": -1,
                    "breathes_air": True,
                    "breathes_water": True,
                },
                "minecraft:interact": {
                    "interactions": [
                        {
                            "on_interact": {
                                "filters": {
                                    "all_of": [
                                        {"test": "is_family", "subject": "other", "value": "player"}
                                    ]
                                },
                                "event": "cc:on_interact",
                                "target": "self",
                            },
                            "use_item": False,
                            "interact_text": INTERACT_KEYS["idle"],
                            "cooldown": 0.3,
                            "swing": False,
                        },
                        {
                            "on_interact": {
                                "filters": {
                                    "all_of": [
                                        {"test": "is_family", "subject": "other", "value": "player"},
                                        {"test": "has_tag", "subject": "self", "value": "cc:anim_torturing"},
                                    ]
                                },
                                "event": "cc:on_interact",
                                "target": "self",
                            },
                            "use_item": False,
                            "interact_text": INTERACT_KEYS["occupied"],
                            "cooldown": 0.3,
                            "swing": False,
                        },
                        {
                            "on_interact": {
                                "filters": {
                                    "all_of": [
                                        {"test": "is_family", "subject": "other", "value": "player"},
                                        {"test": "has_tag", "subject": "self", "value": "cc:anim_closed"},
                                    ]
                                },
                                "event": "cc:on_interact",
                                "target": "self",
                            },
                            "use_item": False,
                            "interact_text": INTERACT_KEYS["occupied"],
                            "cooldown": 0.3,
                            "swing": False,
                        },
                    ]
                },
            },
            "component_groups": {
                # The hitbox covers the whole contraption whether or not someone
                # is inside it. An earlier build shrank the occupied hitbox to a
                # sub-block box parked below the world, which meant a rescuer
                # aiming at a full device could never hit it and the rescue
                # interaction was unreachable. A frame that shelters its captive
                # is also the right behaviour: hitting the device damages the
                # frame, not the prisoner.
                "cc:seated": {
                    "minecraft:custom_hit_test": {
                        "hitboxes": [
                            {
                                "width": collision["width"],
                                "height": collision["height"],
                                "pivot": [0, collision["height"] / 2, 0],
                            }
                        ]
                    }
                },
                # Kept separate so the two states stay independently tunable.
                "cc:empty": {
                    "minecraft:custom_hit_test": {
                        "hitboxes": [
                            {
                                "width": collision["width"],
                                "height": collision["height"],
                                "pivot": [0, collision["height"] / 2, 0],
                            }
                        ]
                    }
                },
            },
            "events": {
                # The script API drives everything through these events; the
                # interaction event carries no payload on the stable API, so the
                # server event is the authoritative handler.
                "cc:on_interact": {},
                "cc:seat_victim": {
                    "remove": {"component_groups": ["cc:empty"]},
                    "add": {"component_groups": ["cc:seated"]},
                },
                "cc:clear_victim": {
                    "remove": {"component_groups": ["cc:seated"]},
                    "add": {"component_groups": ["cc:empty"]},
                },
            },
        },
    }


def write_devices() -> list[DeviceArt]:
    built: list[DeviceArt] = []
    for module_name in DEVICE_MODULES:
        module = __import__(module_name)
        art = module.build()
        built.append(art)

        # Deterministic per-device seed: Python's str hash is salted per process,
        # so using it here made every rebuild produce slightly different art.
        seed = zlib.crc32(module_name.encode("utf-8")) % 9973
        atlas, uv_map = bake_atlas(art.model, seed=seed)
        atlas_path = RP / "textures" / "entity" / f"{art.slug}.png"
        atlas_path.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(atlas_path)

        write_geometry(art.model, RP / "models" / "entity" / f"{art.slug}.geo.json", uv_map)
        write_animations(RP / "animations" / f"{art.slug}.animation.json", art.animations)
        write_json(
            RP / "animation_controllers" / f"{art.slug}.animation_controllers.json",
            controller_json(art),
        )
        write_json(RP / "entity" / f"{art.slug}.entity.json", client_entity_json(art))
        write_json(BP / "entities" / f"{art.slug}.json", behavior_entity(art))
        write_json(
            BP / "blocks" / f"{art.slug}_block.json",
            {
                "format_version": "1.21.0",
                "minecraft:block": {
                    "description": {
                        "identifier": f"cc:{art.slug}_block",
                        "menu_category": {"category": "items", "group": "itemGroup.name.miscellaneous"},
                    },
                    "components": {
                        "minecraft:destructible_by_mining": {"seconds_to_destroy": 1.0},
                        "minecraft:destructible_by_explosion": {"explosion_resistance": 6.0},
                        # Anchor blocks are a plain full cube. v0.1.2 pointed them
                        # at geometry.cc_iron_maiden_block, a model that was never
                        # written, so a placed device that failed to convert drew
                        # nothing at all -- one half of the reported "I place it
                        # and it is invisible". A default cube cannot go missing.
                        "minecraft:material_instances": {
                            "*": {
                                "texture": f"cc_{art.slug}_side",
                                "render_method": "opaque",
                            }
                        },
                    },
                },
            },
        )
        write_json(
            BP / "items" / f"{art.slug}.json",
            {
                "format_version": "1.21.0",
                "minecraft:item": {
                    "description": {
                        "identifier": f"cc:item_{art.slug}",
                        "menu_category": {"category": "items", "group": "itemGroup.name.miscellaneous"},
                    },
                    "components": {
                        "minecraft:display_name": {"value": f"item.cc:item_{art.slug}.name"},
                        "minecraft:icon": {"textures": {"default": ITEM_ICONS[art.slug]}},
                        "minecraft:max_stack_size": 1,
                        "minecraft:block_placer": {"block": f"cc:{art.slug}_block"},
                    },
                },
            },
        )
    return built


# ---------------------------------------------------------------------------
# Inventory icons
# ---------------------------------------------------------------------------
# Hand-painted 16x16 silhouettes. These are drawn as explicit ASCII stencils so
# every texel is a deliberate choice, the same way the entity atlases are
# painted. v0.1.2 shipped a single generic crate shape for all five devices.
ICON_PALETTES = {
    "iron_maiden": {
        ".": None, "o": IRON_BLACK, "L": STEEL_LIGHT, "#": STEEL_MID,
        "D": STEEL_DARK, "e": rgba("#141820"), "r": STEEL_HIGHLIGHT, "x": RUST,
    },
    "cursed_stocks": {
        ".": None, "o": rgba("#2a1c10"), "L": WOOD_LIGHT, "#": WOOD,
        "D": WOOD_DARK, "d": WOOD_MID, "e": rgba("#1a1108"), "r": ROPE,
        "k": ROPE_DARK,
    },
    "gravebinder_cage": {
        ".": None, "o": IRON_BLACK, "L": STEEL_LIGHT, "#": STEEL,
        "D": STEEL_DARK, "e": rgba("#12161d"), "b": BONE, "B": BONE_DARK,
        "x": RUST,
    },
    "regret_rack": {
        ".": None, "o": rgba("#2a1c10"), "L": WOOD_LIGHT, "#": WOOD,
        "D": WOOD_DARK, "d": WOOD_MID, "m": STEEL_MID, "M": STEEL_LIGHT,
        "e": rgba("#161a20"), "r": ROPE, "k": ROPE_DARK,
    },
    "black_reliquary": {
        ".": None, "o": OBSIDIAN_DARK, "L": OBSIDIAN_LIGHT, "#": OBSIDIAN,
        "D": rgba("#100c1c"), "g": GOLD, "G": GOLD_LIGHT, "e": CRYSTAL_DARK,
        "c": CRYSTAL, "C": CRYSTAL_LIGHT, "s": SOUL, "S": SOUL_PALE,
        "x": STEEL_MID,
    },
}

ITEM_PATTERNS = {
    # Arched cabinet with a riveted face mask, narrow eye slits and a grille.
    "iron_maiden": [
        "................",
        "......oooo......",
        "....ooLLLLoo....",
        "...oLL####DDo...",
        "..oLLr#####rDo..",
        "..oL#ee##ee#Do..",
        "..oL########Do..",
        "..oL##eeee##Do..",
        "..oL########Do..",
        "..oL#r####r#Do..",
        "..oL########Do..",
        "..oLD######DDo..",
        "..oLD######DDo..",
        "..oLD######DDo..",
        "...oDDDDDDDDo...",
        "...oo......oo...",
    ],
    # Dark posts carrying a light cross board with two black leg holes.
    "cursed_stocks": [
        "................",
        ".ooo........ooo.",
        ".oDo........oDo.",
        ".oDo........oDo.",
        ".oooooooooooooo.",
        ".oLLLLLLLLLLLLo.",
        ".oL#ee####ee#Do.",
        ".oL#ee####ee#Do.",
        ".o############o.",
        ".oooooooooooooo.",
        ".oDo........oDo.",
        ".oDo........oDo.",
        ".oDo........oDo.",
        ".oooo......oooo.",
        ".o##o......o##o.",
        "................",
    ],
    # Domed barred cage: near-black interior, steel bars, skull behind them.
    "gravebinder_cage": [
        "................",
        ".....oooooo.....",
        "...oooooooooo...",
        "..oLLLLLLLLLLo..",
        "..oDDDDDDDDDDo..",
        "..oee#eeee#eeo..",
        "..oee#bbbb#eeo..",
        "..oee#bBBb#eeo..",
        "..oee#bbbb#eeo..",
        "..oee#ebbe#eeo..",
        "..oee#eeee#eeo..",
        "..oee#eeee#eeo..",
        "..oee#eeee#eeo..",
        "..oDDDDDDDDDDo..",
        "..oLLLLLLLLLLo..",
        "..oooooooooooo..",
    ],
    # Crank wheel on a timber bed with two hanging restraint straps.
    "regret_rack": [
        "................",
        "..........MMMM..",
        ".........MM..MM.",
        ".........M.mm.M.",
        ".........M.mm.M.",
        ".........MM..MM.",
        "..........MMMM..",
        ".ooo........ooo.",
        ".oDo........oDo.",
        ".oooooooooooooo.",
        ".oLLLrLLLLrLLLo.",
        ".oDDDrrDDrrDDDo.",
        ".oDo........oDo.",
        ".oDo........oDo.",
        ".oooo......oooo.",
        ".o##o......o##o.",
    ],
    # Obsidian casket, gold bands, faceted soul gem on the lid.
    "black_reliquary": [
        "................",
        "................",
        "...oooooooooo...",
        "..oLLLLLLLLLLo..",
        "..oGGGGGGGGGGo..",
        "..o##########o..",
        "..o##ooCCoo##o..",
        "..o#oCCCCCCo#o..",
        "..o#oCCeeCCo#o..",
        "..o##oCCCCo##o..",
        "..o###oooo###o..",
        "..o##########o..",
        "..oGGGGGGGGGGo..",
        "..oLLo##o##oLo..",
        "..oooooooooooo..",
        "...oo......oo...",
    ],
}


def write_item_textures() -> None:
    """Paint the five 16x16 inventory icons as 32-bit RGBA PNGs."""
    for slug, pattern in ITEM_PATTERNS.items():
        mapping = ICON_PALETTES[slug]
        for index, row in enumerate(pattern):
            if len(row) != 16:
                raise ValueError(f"{slug} icon row {index} is {len(row)} texels, expected 16")
        image = Image(16, 16)
        painter = Painter(image, Rect(0, 0, 16, 16), seed=len(slug) * 17 + 3)
        painter.stencil_map(pattern, mapping)
        painter.opaque()
        target = RP / "textures" / "items" / f"{ITEM_ICONS[slug]}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target)


# Files this generator used to emit, or that an earlier release hand-authored.
# They must not survive a rebuild: a leftover copy of the behavior block
# declares the same identifier twice and Bedrock refuses to load either.
STALE_OUTPUTS = (
    "resource_pack/models/entity/anchor_block.geo.json",
)


def remove_stale_outputs() -> None:
    for relative in STALE_OUTPUTS:
        path = ROOT / relative
        if path.is_file():
            path.unlink()
    for module_name in DEVICE_MODULES:
        legacy = BP / "blocks" / f"{module_name}.json"
        if legacy.is_file():
            legacy.unlink()


def write_block_textures() -> None:
    """The anchor block's own textures, painted at 64x64 and written as RGBA.

    These are almost never seen (the anchor is swapped for the device entity on
    the next tick) but they must still be valid 32-bit RGBA art, because the
    v0.1.2 invisibility report was traced to indexed/grayscale PNGs.
    """
    recipes = {
        "iron_maiden": steel_plate(STEEL, rivets=True, grime=0.18, rust=0.25),
        "cursed_stocks": planks(WOOD, count=5, knots=4),
        "gravebinder_cage": steel_plate(STEEL_DARK, rivets=True, grime=0.24, rust=0.4),
        "regret_rack": planks(WOOD_DARK, count=5, knots=3),
        "black_reliquary": obsidian(OBSIDIAN, facet=OBSIDIAN_FACET),
    }
    for slug, paint in recipes.items():
        image = Image(64, 64)
        painter = Painter(image, Rect(0, 0, 64, 64), seed=len(slug) * 31)
        paint(painter)
        painter.opaque()
        target = RP / "textures" / "blocks" / f"{slug}_side.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target)


def write_block_registry_and_atlas() -> None:
    blocks = {f"cc:{slug}_block": {"textures": texture, "sound": sound}
              for slug, (texture, sound) in BLOCK_MATERIALS.items()}
    write_json(RP / "blocks.json", blocks)

    texture_data = {
        f"cc_{slug}_side": {"textures": f"textures/blocks/{slug}_side.png"}
        for slug in DEVICE_MODULES
    }
    write_json(
        RP / "textures" / "terrain_texture.json",
        {
            "resource_pack_name": "Cursed Contraptions",
            "texture_name": "atlas.terrain",
            "texture_data": texture_data,
        },
    )
    write_json(
        RP / "textures" / "item_texture.json",
        {
            "resource_pack_name": "Cursed Contraptions",
            "texture_name": "atlas.items",
            "texture_data": {
                icon: {"textures": f"textures/items/{icon}.png"}
                for icon in ITEM_ICONS.values()
            },
        },
    )


def write_language() -> None:
    lines = ["# Cursed Contraptions — English (US)", ""]
    for slug in DEVICE_MODULES:
        name = DISPLAY_NAMES[slug]
        lines.append(f"item.cc:item_{slug}.name={name}")
    lines.append("")
    for slug in DEVICE_MODULES:
        name = DISPLAY_NAMES[slug]
        lines.append(f"tile.cc:{slug}_block.name={name}")
    lines.append("")
    for slug in DEVICE_MODULES:
        name = DISPLAY_NAMES[slug]
        lines.append(f"entity.cc:{slug}.name={name}")
    lines.extend(
        [
            "",
            "action.cc.use_device=Inspect / Reinforce",
            "action.cc.rescue_captive=Use / Rescue",
            "",
            "pack.name=Cursed Contraptions",
            "pack.description=Medieval torture contraptions for chaotic multiplayer fun",
            "",
        ]
    )
    (RP / "texts" / "en_US.lang").write_text("\n".join(lines), encoding="utf-8")


def verify(arts: list[DeviceArt]) -> list[str]:
    problems: list[str] = []
    for art in arts:
        # 1. Entity textures must be 32-bit RGBA; indexed/grayscale PNGs are the
        #    root cause of the v0.1.2 invisible-device report.
        texture = RP / "textures" / "entity" / f"{art.slug}.png"
        bit_depth, color_type, _ = png_color_type(texture)
        if (bit_depth, color_type) != (8, 6):
            problems.append(f"{art.slug}: texture is bit depth {bit_depth} color type {color_type}, expected 8/6 RGBA")

        # 2. Every cube face must have a UV rect inside the atlas, and the
        #    per-face uv_size must match Bedrock's rounded face size.
        rects, _ = pack_faces(art.model)
        for bone in art.model.bones:
            for cube_index, cube in enumerate(bone.cubes):
                for face in cube.faces:
                    rect = rects.get(bone.name, {}).get(f"{cube_index}:{face}")
                    if rect is None:
                        problems.append(f"{art.slug}: {bone.name} cube {cube_index} face {face} has no atlas rect")
                        continue
                    if rect.right > art.model.texture_width or rect.bottom > art.model.texture_height:
                        problems.append(f"{art.slug}: {bone.name}.{face} atlas rect escapes the texture")
                    # Faces without an explicit size must match Bedrock's
                    # integer rounding of the cube face, otherwise the UV rect
                    # and the rendered face disagree and the texture stretches.
                    if cube.faces[face].size is None:
                        expected = face_pixel_size(face, cube.size, cube.inflate)
                        if (rect.width, rect.height) != expected:
                            problems.append(
                                f"{art.slug}: {bone.name} cube {cube_index} face {face} is "
                                f"{rect.width}x{rect.height}, Bedrock rounds it to {expected[0]}x{expected[1]}"
                            )

        # 3. Every face covered by one shared atlas patch must agree on size.
        seen: dict[str, tuple[int, int]] = {}
        for bone in art.model.bones:
            for cube_index, cube in enumerate(bone.cubes):
                for face, spec in cube.faces.items():
                    if not spec.share:
                        continue
                    dimensions = spec.dimensions(face, cube.size, cube.inflate)
                    previous = seen.get(spec.share)
                    if previous is None:
                        seen[spec.share] = dimensions
                    elif previous != dimensions:
                        problems.append(
                            f"{art.slug}: patch '{spec.share}' is used at {previous} and {dimensions}"
                        )

        # 4. Animation bones must exist in the model.
        bone_names = {bone.name for bone in art.model.bones}
        for animation in art.animations:
            missing = set(animation.bones) - bone_names
            if missing:
                problems.append(f"{art.slug}: {animation.identifier} animates missing bones {sorted(missing)}")

        # 5. Every device state needs controller coverage.
        controller = controller_json(art)
        states = controller["animation_controllers"][art.controller_id]["states"]
        for state in DEVICE_STATES:
            if state not in states:
                problems.append(f"{art.slug}: controller is missing the {state} state")
        aliases = set(client_entity_json(art)["minecraft:client_entity"]["description"]["animations"])
        for state_name, state in states.items():
            for alias in state.get("animations", []):
                if alias not in aliases:
                    problems.append(f"{art.slug}: state {state_name} uses unknown animation alias {alias}")
            for transition in state.get("transitions", []):
                for target in transition:
                    if target not in states:
                        problems.append(f"{art.slug}: state {state_name} transitions to missing state {target}")
    return problems


def main() -> int:
    arts = write_devices()
    write_block_textures()
    write_item_textures()
    write_block_registry_and_atlas()
    write_language()
    remove_stale_outputs()

    problems = verify(arts)
    for problem in problems:
        print(f"  FAIL  {problem}")
    if problems:
        print(f"\n{len(problems)} asset problem(s); nothing else was written")
        return 1

    print("Assets written and verified:")
    for art in arts:
        cubes = sum(len(bone.cubes) for bone in art.model.bones)
        print(
            f"  {art.slug:>18}: {len(art.model.bones)} bones, {cubes} cubes, "
            f"{len(art.animations)} animations, {art.model.texture_width}x{art.model.texture_height} atlas"
        )
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
