#!/usr/bin/env python3
"""Validate pack manifests, references, scripts, and optional .mcaddon output."""

from __future__ import annotations

import argparse
import io
import json
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BP = ROOT / "behavior_pack"
RP = ROOT / "resource_pack"
RELEASE_VERSION = [0, 1, 4]
MIN_ENGINE_VERSION = [1, 21, 60]
SERVER_API_VERSION = "1.17.0"
EXPECTED_PACKAGES = {
    "Cursed-Contraptions_BP.mcpack": BP / "manifest.json",
    "Cursed-Contraptions_RP.mcpack": RP / "manifest.json",
}
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
# Creative-menu placement rules. "none" hides an item from the creative
# inventory entirely, so it is deliberately not accepted here: this pack's items
# exist to be seen and placed.
CREATIVE_CATEGORIES = {"construction", "equipment", "items", "nature"}
NAMESPACED_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.]+:[A-Za-z0-9_.]+$")
ITEM_CATALOG = BP / "item_catalog" / "crafting_item_catalog.json"
# minecraft:block_placer is only honoured from this item format version on.
BLOCK_PLACER_MIN_FORMAT = (1, 21, 50)
DEVICE_CONFIG_KEYS = {
    "iron_maiden": "ironMaiden",
    "cursed_stocks": "cursedStocks",
    "gravebinder_cage": "gravebinderCage",
    "regret_rack": "regretRack",
    "black_reliquary": "blackReliquary",
}

errors: list[str] = []
json_data: dict[Path, dict] = {}


def report_error(message: str) -> None:
    errors.append(message)
    print(f"  FAIL  {message}")


def report_ok(message: str) -> None:
    print(f"  PASS  {message}")


def load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        json_data[path] = data
        return data
    except (OSError, json.JSONDecodeError) as error:
        report_error(f"Invalid or unreadable JSON {path.relative_to(ROOT)}: {error}")
        return None


def asset_path_from_texture(texture: str) -> Path:
    normalized = str(texture).removesuffix(".png").lstrip("/")
    return RP / f"{normalized}.png"


def texture_paths_from_reference(reference: object) -> list[str]:
    """Return texture paths from the string/object/list shapes used by atlases."""
    if isinstance(reference, str):
        return [reference]
    if isinstance(reference, list):
        return [path for value in reference for path in texture_paths_from_reference(value)]
    if isinstance(reference, dict):
        paths: list[str] = []
        for key in ("textures", "path"):
            if key in reference:
                paths.extend(texture_paths_from_reference(reference[key]))
        return paths
    return []


def read_png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", header[16:24])
    except (OSError, struct.error):
        return None


def validate_uuid(value: object, label: str, seen: set[str]) -> None:
    if not isinstance(value, str) or not UUID_PATTERN.fullmatch(value):
        report_error(f"{label} has an invalid UUID: {value!r}")
        return
    normalized = value.lower()
    if normalized in seen:
        report_error(f"Duplicate UUID: {value} ({label})")
    seen.add(normalized)


def validate_manifests() -> tuple[dict | None, dict | None]:
    print("\n=== Manifests and API compatibility ===")
    bp = load_json(BP / "manifest.json")
    rp = load_json(RP / "manifest.json")
    package = load_json(ROOT / "package.json")
    lockfile = load_json(ROOT / "package-lock.json")
    release_version = ".".join(map(str, RELEASE_VERSION))
    if package and package.get("version") != release_version:
        report_error(f"package.json must be version {release_version}")
    if lockfile and (
        lockfile.get("version") != release_version
        or lockfile.get("packages", {}).get("", {}).get("version") != release_version
    ):
        report_error(f"package-lock.json root versions must be {release_version}")
    seen_uuids: set[str] = set()

    for name, pack, expected_module_type in (
        ("behavior", bp, {"data", "script"}),
        ("resource", rp, {"resources"}),
    ):
        if not pack:
            continue
        header = pack.get("header", {})
        validate_uuid(header.get("uuid"), f"{name} header", seen_uuids)
        if not header.get("name"):
            report_error(f"{name} manifest has no header name")
        if header.get("version") != RELEASE_VERSION:
            report_error(f"{name} manifest must be version {release_version}")
        if header.get("min_engine_version") != MIN_ENGINE_VERSION:
            report_error(f"{name} minimum engine version must be 1.21.60")

        modules = pack.get("modules", [])
        module_types = {module.get("type") for module in modules}
        if module_types != expected_module_type:
            report_error(f"{name} manifest modules are {module_types}, expected {expected_module_type}")
        for index, module in enumerate(modules):
            validate_uuid(module.get("uuid"), f"{name} module[{index}]", seen_uuids)
            if module.get("version") != RELEASE_VERSION:
                report_error(f"{name} module[{index}] must be version {release_version}")
            entry = module.get("entry")
            if entry:
                entry_path = pack_root(name) / entry
                if not entry_path.is_file():
                    report_error(f"{name} script entry does not exist: {entry}")

    if bp and rp:
        resource_uuid = rp.get("header", {}).get("uuid")
        pack_dependencies = [d for d in bp.get("dependencies", []) if "uuid" in d]
        if len(pack_dependencies) != 1:
            report_error("behavior pack must depend on exactly one resource pack UUID")
        elif pack_dependencies[0].get("uuid") != resource_uuid or pack_dependencies[0].get("version") != RELEASE_VERSION:
            report_error("behavior pack resource dependency UUID/version does not match resource pack v0.1.2")

        server_dependencies = [
            dependency for dependency in bp.get("dependencies", [])
            if dependency.get("module_name") == "@minecraft/server"
        ]
        if len(server_dependencies) != 1 or server_dependencies[0].get("version") != SERVER_API_VERSION:
            report_error(f"behavior pack must use stable @minecraft/server {SERVER_API_VERSION}")

    if not errors:
        report_ok("Pack UUIDs, versions, entries, and stable API dependency are consistent")
    return bp, rp


def pack_root(name: str) -> Path:
    return BP if name == "behavior" else RP


def validate_json_and_pngs() -> int:
    print("\n=== Source asset validation ===")
    json_files = sorted([*BP.rglob("*.json"), *RP.rglob("*.json")])
    for path in json_files:
        load_json(path)
    report_ok(f"Parsed {len(json_files)} JSON files")

    png_files = sorted(RP.rglob("*.png")) + [BP / "pack_icon.png"]
    png_count = 0
    for path in png_files:
        if not path.is_file():
            report_error(f"Missing PNG: {path.relative_to(ROOT)}")
            continue
        try:
            header = path.read_bytes()[:26]
            if len(header) != 26 or header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("invalid PNG signature/header")
            width, height = struct.unpack(">II", header[16:24])
            if width < 1 or height < 1:
                raise ValueError(f"invalid dimensions {width}x{height}")
            # v0.1.3: Bedrock quietly drops indexed and grayscale textures, which
            # is what turned every device model invisible in v0.1.2. Every shipped
            # texture must be true-colour RGBA (8-bit, colour type 6).
            bit_depth, color_type = header[24], header[25]
            if (bit_depth, color_type) != (8, 6):
                raise ValueError(
                    f"texture is {bit_depth}-bit colour type {color_type}; "
                    "Bedrock requires 8-bit RGBA (colour type 6)"
                )
            png_count += 1
        except (OSError, ValueError, struct.error) as error:
            report_error(f"Invalid PNG {path.relative_to(ROOT)}: {error}")
    report_ok(f"Validated {png_count} PNG files")
    return len(json_files)


def validate_scripts(bp_manifest: dict | None) -> int:
    print("\n=== JavaScript validation ===")
    scripts = sorted((BP / "scripts").rglob("*.js"))
    if not scripts:
        report_error("No behavior-pack scripts found")
        return 0

    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        report_error("Node.js is required to syntax-check behavior-pack scripts")
        return len(scripts)

    import_pattern = re.compile(r"(?:\bfrom\s+|\bimport\s*)[\"']([^\"']+)[\"']")
    for path in scripts:
        try:
            subprocess.run(["node", "--check", str(path)], check=True, capture_output=True, text=True, cwd=ROOT)
        except subprocess.CalledProcessError as error:
            report_error(f"JavaScript syntax error in {path.relative_to(ROOT)}: {error.stderr.strip()}")

        for specifier in import_pattern.findall(path.read_text(encoding="utf-8")):
            if specifier.startswith(".") and not (path.parent / specifier).is_file():
                report_error(f"Missing import {specifier} from {path.relative_to(ROOT)}")
            elif not specifier.startswith(".") and specifier != "@minecraft/server":
                report_error(f"Unexpected external script dependency {specifier} in {path.relative_to(ROOT)}")

    if bp_manifest:
        main = BP / "scripts" / "main.js"
        if not main.is_file():
            report_error("Behavior pack entry point scripts/main.js is missing")
    report_ok(f"Syntax-checked and resolved imports for {len(scripts)} scripts")
    return len(scripts)


def validate_item_catalog(menu_categories: dict[str, tuple[Path, dict]]) -> tuple[dict[str, list[str]], set[str]]:
    """Check the creative item catalog and return its groups and item lists.

    The catalog is what defines the pack's creative group (its icon and its
    localized hover name), so ``menu_category.group`` has a real group to point
    at instead of an un-namespaced name the game silently rejects.
    """
    print("\n=== Creative inventory registration ===")
    data = json_data.get(ITEM_CATALOG) or load_json(ITEM_CATALOG)
    if not data:
        report_error(
            f"Missing {ITEM_CATALOG.relative_to(ROOT)}: without it the pack's creative group "
            "cannot be resolved and the devices never appear in the creative inventory"
        )
        return {}, set()

    catalog = data.get("minecraft:crafting_items_catalog", {})
    if not catalog:
        report_error(f"{ITEM_CATALOG.name} has no minecraft:crafting_items_catalog block")
        return {}, set()

    groups: dict[str, list[str]] = {}
    listed: set[str] = set()
    for category in catalog.get("categories", []):
        category_name = category.get("category_name")
        if category_name not in CREATIVE_CATEGORIES:
            report_error(f"{ITEM_CATALOG.name} declares unknown creative category {category_name!r}")
        for group in category.get("groups", []):
            identifier = group.get("group_identifier") or {}
            name = identifier.get("name")
            items = group.get("items", [])
            if not name:
                report_error(f"{ITEM_CATALOG.name} has a group without a group_identifier name")
                continue
            if not NAMESPACED_IDENTIFIER.fullmatch(str(name)):
                report_error(
                    f"{ITEM_CATALOG.name} group name {name!r} is not namespaced; "
                    "menu_category.group must be <namespace>:<name>"
                )
            if name in groups:
                report_error(f"{ITEM_CATALOG.name} defines creative group {name} twice")
            groups[name] = list(items)
            listed.update(items)
            icon = identifier.get("icon")
            if icon and icon not in menu_categories:
                report_error(f"{ITEM_CATALOG.name} group {name} uses unknown icon {icon}")

    for item in sorted(listed):
        if item not in menu_categories:
            report_error(f"{ITEM_CATALOG.name} lists {item}, which no item or block defines")

    lang_file = RP / "texts" / "en_US.lang"
    lang_text = lang_file.read_text(encoding="utf-8") if lang_file.is_file() else ""
    for name in sorted(groups):
        if f"{name}=" not in lang_text:
            report_error(f"{lang_file.name} does not define the creative group name key {name}")

    missing = sorted(identifier for identifier in menu_categories if identifier not in listed)
    if missing and groups:
        report_error(
            f"{ITEM_CATALOG.name} does not list {len(missing)} declared item(s)/block(s): "
            f"{', '.join(missing[:5])}"
        )

    if groups:
        report_ok(f"Creative catalog defines {len(groups)} group(s) covering {len(listed)} entries")
    return groups, listed


def parse_version(value: object) -> tuple[int, ...] | None:
    """Turn a manifest/format version list into a comparable tuple."""
    if isinstance(value, str):
        parts = [part for part in value.split(".") if part.isdigit()]
        return tuple(int(part) for part in parts) if parts else None
    if isinstance(value, list) and all(isinstance(part, int) for part in value):
        return tuple(value)
    return None


def configured_base_durability(slug: str) -> int | None:
    """Read a device's baseDurability out of behavior_pack/scripts/config.js."""
    source = (BP / "scripts" / "config.js").read_text(encoding="utf-8")
    key = DEVICE_CONFIG_KEYS.get(slug)
    if not key:
        return None
    start = source.find(f"{key}: {{")
    if start < 0:
        return None
    match = re.search(r"baseDurability:\s*(\d+)", source[start:])
    return int(match.group(1)) if match else None


def validate_placement_chain() -> None:
    """Validate the item -> block -> entity chain a player uses to place a device.

    Two defects shipped because nothing checked this chain:

    * ``minecraft:block_placer`` only applies from item format version 1.21.50
      on. Below it the item still loads and still appears in the creative menu,
      but cannot place anything - the reported "I see it, but I can't place it".
    * a device entity's ``cc:durability`` property default *is* the durability a
      fresh device starts with (a new entity has no dynamic properties yet), so
      a hand-written default made every newly placed device spawn half-worn.
    """
    print("\n=== Placement chain (item -> block -> entity) ===")

    # Geometry ids the resource pack actually ships, so a block that points at a
    # file-based geometry is checked while built-ins (minecraft:geometry.*) pass.
    shipped_geometries: set[str] = set()
    for path in RP.rglob("*.geo.json"):
        data = json_data.get(path) or load_json(path) or {}
        for geometry in data.get("minecraft:geometry", []):
            identifier = geometry.get("description", {}).get("identifier")
            if identifier:
                shipped_geometries.add(identifier)

    block_ids_found = set()
    for path in (BP / "blocks").glob("*.json"):
        data = json_data.get(path) or load_json(path) or {}
        definition = data.get("minecraft:block", {})
        identifier = definition.get("description", {}).get("identifier")
        if not identifier:
            continue
        block_ids_found.add(identifier)
        components = definition.get("components", {})
        instances = components.get("minecraft:material_instances")
        if not instances:
            report_error(f"{path.name} ({identifier}) declares no minecraft:material_instances")
        geometry = components.get("minecraft:geometry")
        if isinstance(geometry, dict):
            geometry_id = geometry.get("identifier")
            if (geometry_id and not str(geometry_id).startswith("minecraft:geometry.")
                    and geometry_id not in shipped_geometries):
                report_error(f"{path.name} references undefined block geometry {geometry_id}")

    placed = 0
    for path in (BP / "items").glob("*.json"):
        data = json_data.get(path) or load_json(path) or {}
        item = data.get("minecraft:item", {})
        identifier = item.get("description", {}).get("identifier")
        components = item.get("components", {})
        placer = components.get("minecraft:block_placer")
        if not placer:
            continue
        placed += 1

        version = parse_version(data.get("format_version"))
        if version is None or version < BLOCK_PLACER_MIN_FORMAT:
            report_error(
                f"{path.name} ({identifier}) declares minecraft:block_placer at "
                f"format_version {data.get('format_version')!r}; the documented minimum is "
                f"{'.'.join(str(part) for part in BLOCK_PLACER_MIN_FORMAT)}, below which the "
                "component is ignored and the item cannot place its block"
            )

        target = placer.get("block") if isinstance(placer, dict) else placer
        if target not in block_ids_found:
            report_error(f"{path.name} ({identifier}) places {target}, which no block defines")

    for path in (BP / "entities").glob("*.json"):
        data = json_data.get(path) or load_json(path) or {}
        entity = data.get("minecraft:entity", {})
        identifier = entity.get("description", {}).get("identifier", "")
        slug = identifier.split(":", 1)[-1]
        properties = entity.get("description", {}).get("properties", {})
        if not properties:
            continue

        # A fresh device starts from these defaults, so they have to be usable.
        state_default = properties.get("cc:state", {}).get("default")
        if state_default != "idle":
            report_error(f"{path.name} cc:state default is {state_default!r}, expected 'idle'")

        durability_default = properties.get("cc:durability", {}).get("default")
        configured = configured_base_durability(slug)
        if configured is None:
            report_error(f"{path.name}: no baseDurability in config.js for device {slug}")
        elif durability_default != configured:
            report_error(
                f"{path.name} cc:durability default is {durability_default}, but config.js "
                f"sets baseDurability {configured} for {slug}; a fresh device spawns at the "
                "property default, so it would start damaged"
            )

    if placed:
        report_ok(f"{placed} devices declare a valid block_placer for a defined block")


def validate_pack_references() -> tuple[int, int, int, int]:
    print("\n=== Entity, block, item, texture, and animation references ===")
    bp_entities: dict[str, Path] = {}
    rp_entities: dict[str, tuple[Path, dict]] = {}
    block_ids: dict[str, Path] = {}
    item_ids: dict[str, Path] = {}
    geometry_by_id: dict[str, dict] = {}
    animations: dict[str, dict] = {}
    controllers: dict[str, dict] = {}

    for path in sorted((BP / "entities").glob("*.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        description = data.get("minecraft:entity", {}).get("description", {})
        identifier = description.get("identifier")
        if not identifier:
            report_error(f"Behavior entity has no identifier: {path.relative_to(ROOT)}")
        elif identifier in bp_entities:
            report_error(f"Duplicate behavior entity identifier: {identifier}")
        else:
            bp_entities[identifier] = path

    for path in sorted((RP / "entity").glob("*.entity.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        description = data.get("minecraft:client_entity", {}).get("description", {})
        identifier = description.get("identifier")
        if not identifier:
            report_error(f"Resource client entity has no identifier: {path.relative_to(ROOT)}")
        elif identifier in rp_entities:
            report_error(f"Duplicate resource entity identifier: {identifier}")
        else:
            rp_entities[identifier] = (path, description)

    if set(bp_entities) != set(rp_entities):
        report_error(
            f"Behavior/resource entity identifiers differ: BP-only={sorted(set(bp_entities)-set(rp_entities))}, "
            f"RP-only={sorted(set(rp_entities)-set(bp_entities))}"
        )
    else:
        report_ok(f"Matched {len(bp_entities)} behavior/resource entities")

    # Creative-menu placement. A custom item or block only appears in the
    # creative inventory when menu_category is valid: the category has to be one
    # of the three visible tabs, and (since Bedrock 26.x) the optional group must
    # be namespaced. v0.1.4 shipped the un-namespaced
    # "itemGroup.name.miscellaneous", which the game rejects, so the add-on
    # looked like it contained no items at all.
    menu_categories: dict[str, tuple[Path, dict]] = {}
    for state in ("block", "item"):
        container = "minecraft:block" if state == "block" else "minecraft:item"
        for path in sorted((BP / f"{state}s").glob("*.json")):
            data = json_data.get(path) or load_json(path)
            if not data:
                continue
            definition = data.get(container, {})
            description = definition.get("description", {})
            identifier = description.get("identifier")
            if not identifier:
                report_error(f"{state.capitalize()} has no identifier: {path.relative_to(ROOT)}")
                continue
            registry = block_ids if state == "block" else item_ids
            if identifier in registry:
                report_error(f"Duplicate {state} identifier: {identifier}")
            registry[identifier] = path
            menu_categories[identifier] = (path, description.get("menu_category") or {})

    catalog_groups, catalog_items = validate_item_catalog(menu_categories)

    for identifier, (path, menu_category) in menu_categories.items():
        category = menu_category.get("category")
        if category not in CREATIVE_CATEGORIES:
            report_error(
                f"{path.name} ({identifier}) has menu_category category {category!r}; "
                f"creative placement needs one of {sorted(CREATIVE_CATEGORIES)}"
            )
        group = menu_category.get("group")
        if group is None:
            continue
        if not isinstance(group, str) or not re.fullmatch(NAMESPACED_IDENTIFIER, group):
            report_error(
                f"{path.name} ({identifier}) has menu_category group {group!r}; "
                "the group must be namespaced as <namespace>:<name>"
            )
            continue
        if group not in catalog_groups:
            report_error(
                f"{path.name} ({identifier}) references creative group {group}, "
                "which the item catalog does not define"
            )
        elif identifier not in catalog_groups[group]:
            report_error(
                f"{path.name} ({identifier}) declares creative group {group} "
                "but the item catalog does not list it in that group"
            )

    terrain = json_data.get(RP / "textures" / "terrain_texture.json") or load_json(RP / "textures" / "terrain_texture.json") or {}
    item_atlas = json_data.get(RP / "textures" / "item_texture.json") or load_json(RP / "textures" / "item_texture.json") or {}
    terrain_data = terrain.get("texture_data", {})
    item_data = item_atlas.get("texture_data", {})
    terrain_aliases = set(terrain_data)
    item_aliases = set(item_data)

    for atlas_name, entries in (("terrain", terrain_data), ("item", item_data)):
        for alias, entry in entries.items():
            texture_paths = texture_paths_from_reference(entry)
            if not texture_paths:
                report_error(f"{atlas_name.title()} atlas alias {alias} has no texture path")
                continue
            for texture in texture_paths:
                texture_file = asset_path_from_texture(texture)
                if not texture_file.is_file():
                    report_error(f"{atlas_name.title()} atlas alias {alias} references missing PNG {texture_file.relative_to(ROOT)}")

    for path in block_ids.values():
        block = (json_data.get(path) or {}).get("minecraft:block", {})
        components = block.get("components", {})
        material_instances = components.get("minecraft:material_instances", {})
        for instance in material_instances.values():
            alias = instance.get("texture") if isinstance(instance, dict) else None
            if alias and alias not in terrain_aliases:
                report_error(f"Block {path.name} references missing terrain texture alias {alias}")

    for path in sorted((RP / "models" / "entity").glob("*.geo.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        for geometry in data.get("minecraft:geometry", []):
            description = geometry.get("description", {})
            identifier = description.get("identifier")
            if not identifier:
                report_error(f"Geometry has no identifier: {path.relative_to(ROOT)}")
            elif identifier in geometry_by_id:
                report_error(f"Duplicate geometry identifier: {identifier}")
            else:
                geometry_by_id[identifier] = geometry

            texture_width = description.get("texture_width")
            texture_height = description.get("texture_height")
            if not isinstance(texture_width, int) or texture_width < 1 or not isinstance(texture_height, int) or texture_height < 1:
                report_error(f"Geometry {identifier or path.name} has invalid texture dimensions {texture_width}x{texture_height}")
                continue

            # Legacy two-number cube UVs use the standard Bedrock box unwrap:
            # U span = 2 * (x + z), V span = y + z. Catch out-of-atlas UVs
            # before they turn into wrapped/clamped texture patches in-game.
            for bone in geometry.get("bones", []):
                for cube in bone.get("cubes", []):
                    uv = cube.get("uv")
                    size = cube.get("size")
                    if not (
                        isinstance(uv, list) and len(uv) == 2
                        and isinstance(size, list) and len(size) == 3
                        and all(isinstance(value, (int, float)) for value in [*uv, *size])
                    ):
                        continue
                    u, v = uv
                    size_x, size_y, size_z = size
                    if (
                        u < 0 or v < 0
                        or u + 2 * (size_x + size_z) > texture_width
                        or v + size_y + size_z > texture_height
                    ):
                        report_error(
                            f"Geometry {identifier or path.name} bone {bone.get('name')} has box UV {uv} "
                            f"for size {size} outside its {texture_width}x{texture_height} texture"
                        )

    for path in sorted((RP / "animations").glob("*.animation.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        for identifier, definition in data.get("animations", {}).items():
            if identifier in animations:
                report_error(f"Duplicate animation identifier: {identifier}")
            animations[identifier] = definition

    for path in block_ids.values():
        block = (json_data.get(path) or {}).get("minecraft:block", {})
        # Block geometry is declared either as a bare identifier or as an object
        # with an identifier; built-ins (minecraft:geometry.*) are always valid.
        # v0.1.4's anchor blocks are the first to declare one, which is how the
        # old string-only branch went unnoticed until it raised a TypeError.
        geometry = block.get("components", {}).get("minecraft:geometry")
        geometry_id = geometry.get("identifier") if isinstance(geometry, dict) else geometry
        if (geometry_id and not str(geometry_id).startswith("minecraft:geometry.")
                and geometry_id not in geometry_by_id):
            report_error(f"Block {path.name} references undefined geometry {geometry_id}")

    for identifier, path in item_ids.items():
        item = (json_data.get(path) or {}).get("minecraft:item", {})
        components = item.get("components", {})
        icon = components.get("minecraft:icon", {}).get("textures", {}).get("default")
        if icon and icon not in item_aliases:
            report_error(f"Item {identifier} references missing item texture alias {icon}")
        target_block = components.get("minecraft:block_placer", {}).get("block")
        if target_block and target_block not in block_ids:
            report_error(f"Item {identifier} references missing block {target_block}")

    for path in sorted((RP / "animation_controllers").glob("*.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        for identifier, definition in data.get("animation_controllers", {}).items():
            if identifier in controllers:
                report_error(f"Duplicate animation controller identifier: {identifier}")
            controllers[identifier] = definition

    for path, description in rp_entities.values():
        texture_refs = description.get("textures", {}).values()
        texture_files: list[Path] = []
        for texture_reference in texture_refs:
            for texture in texture_paths_from_reference(texture_reference):
                texture_file = asset_path_from_texture(texture)
                texture_files.append(texture_file)
                if not texture_file.is_file():
                    report_error(f"Client entity {path.name} references missing texture {texture}")

        geometry_refs = description.get("geometry", {}).values()
        for geometry_id in geometry_refs:
            geometry = geometry_by_id.get(geometry_id)
            if not geometry:
                report_error(f"Client entity {path.name} references undefined geometry {geometry_id}")
                continue
            description_data = geometry.get("description", {})
            declared_dimensions = (
                description_data.get("texture_width"),
                description_data.get("texture_height"),
            )
            for texture_file in texture_files:
                actual_dimensions = read_png_dimensions(texture_file)
                if actual_dimensions and declared_dimensions != actual_dimensions:
                    report_error(
                        f"Geometry {geometry_id} declares texture size {declared_dimensions}, "
                        f"but {texture_file.relative_to(ROOT)} is {actual_dimensions}"
                    )
            bone_names = {bone.get("name") for bone in geometry.get("bones", [])}
            for alias, animation_id in description.get("animations", {}).items():
                # Controller aliases are validated below, where the controller
                # files are already loaded.
                if str(animation_id).startswith("controller.animation."):
                    continue
                animation = animations.get(animation_id)
                if not animation:
                    report_error(f"Client entity {path.name} references undefined animation {animation_id}")
                    continue
                missing_bones = set(animation.get("bones", {})) - bone_names
                if missing_bones:
                    report_error(f"Animation {animation_id} references missing bones {sorted(missing_bones)}")

        # An alias points at either an animation or an animation controller; the
        # wear controller added in v0.1.4 is a second controller alias, so the
        # name "controller" is no longer the only legal one.
        animation_aliases = description.get("animations", {})
        controller_aliases = {
            alias: target for alias, target in animation_aliases.items()
            if str(target).startswith("controller.animation.")
        }
        for alias, target in animation_aliases.items():
            if str(target).startswith("controller.animation."):
                if target not in controllers:
                    report_error(f"Client entity {path.name} references undefined controller {target}")
            elif target not in animations:
                report_error(f"Client entity {path.name} maps {alias} to missing animation {target}")

        scripts = description.get("scripts", {})
        for animated_alias in scripts.get("animate", []):
            if animated_alias not in animation_aliases:
                report_error(f"Client entity {path.name} animates undefined alias {animated_alias}")

        for controller_id in controller_aliases.values():
            if controller_id not in controllers:
                continue
            definition = controllers[controller_id]
            states = definition.get("states", {})
            for state_name, state in states.items():
                for animation_alias in state.get("animations", []):
                    if animation_alias not in animation_aliases:
                        report_error(f"Controller {controller_id}:{state_name} uses undefined animation alias {animation_alias}")
                for transition in state.get("transitions", []):
                    for target_state in transition:
                        if target_state not in states:
                            report_error(f"Controller {controller_id}:{state_name} transitions to missing state {target_state}")

    # The block registry also maps each custom block to a terrain-atlas alias.
    block_registry_path = RP / "blocks.json"
    block_registry = json_data.get(block_registry_path) or load_json(block_registry_path) or {}
    for identifier, definition in block_registry.items():
        if identifier not in block_ids:
            report_error(f"Resource block registry has no behavior block {identifier}")
        if definition.get("textures") not in terrain_aliases:
            report_error(f"Resource block registry {identifier} references missing texture alias {definition.get('textures')}")

        behavior_path = block_ids.get(identifier)
        if not behavior_path:
            continue
        block = (json_data.get(behavior_path) or {}).get("minecraft:block", {})
        components = block.get("components", {})
        geometry_component = components.get("minecraft:geometry")
        geometry_id = (
            geometry_component.get("identifier")
            if isinstance(geometry_component, dict)
            else geometry_component
        )
        geometry = geometry_by_id.get(geometry_id)
        if not geometry:
            # Built-in geometries (a full block) carry no texture dimensions to
            # compare, so there is nothing further to check for this block.
            continue
        declared_dimensions = (
            geometry.get("description", {}).get("texture_width"),
            geometry.get("description", {}).get("texture_height"),
        )
        material_instances = components.get("minecraft:material_instances", {})
        aliases = {
            instance.get("texture")
            for instance in material_instances.values()
            if isinstance(instance, dict) and instance.get("texture")
        }
        aliases.add(definition.get("textures"))
        for alias in aliases:
            if alias not in terrain_data:
                continue
            for texture in texture_paths_from_reference(terrain_data[alias]):
                texture_file = asset_path_from_texture(texture)
                actual_dimensions = read_png_dimensions(texture_file)
                if actual_dimensions and declared_dimensions != actual_dimensions:
                    report_error(
                        f"Block geometry {geometry_id} declares texture size {declared_dimensions}, "
                        f"but terrain alias {alias} resolves to {actual_dimensions}"
                    )
    if set(block_registry) != set(block_ids):
        report_error("Behavior block identifiers and resource block registry identifiers differ")

    language_path = RP / "texts" / "en_US.lang"
    language_entries: dict[str, str] = {}
    if language_path.is_file():
        for line_number, line in enumerate(language_path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                report_error(f"Invalid language entry at {language_path.relative_to(ROOT)}:{line_number}")
                continue
            key, value = line.split("=", 1)
            if key in language_entries:
                report_error(f"Duplicate language key {key}")
            language_entries[key] = value
    else:
        report_error("Missing resource_pack/texts/en_US.lang")

    for identifier in item_ids:
        if f"item.{identifier}.name" not in language_entries:
            report_error(f"Missing localized item name for {identifier}")
    for identifier in block_ids:
        if f"tile.{identifier}.name" not in language_entries:
            report_error(f"Missing localized block name for {identifier}")
    for identifier, path in bp_entities.items():
        if f"entity.{identifier}.name" not in language_entries:
            report_error(f"Missing localized entity name for {identifier}")

        entity_data = (json_data.get(path) or {}).get("minecraft:entity", {})
        components = entity_data.get("components", {})
        interaction_component = components.get("minecraft:interact", {})
        interactions = interaction_component.get("interactions", [])
        if not interactions:
            report_error(f"Behavior entity {identifier} has no minecraft:interact entries")
        for index, interaction in enumerate(interactions):
            prompt = interaction.get("interact_text")
            if not prompt or prompt not in language_entries:
                report_error(f"Behavior entity {identifier} interaction[{index}] has no localized prompt {prompt!r}")
            on_interact = interaction.get("on_interact", {})
            event_name = on_interact.get("event") if isinstance(on_interact, dict) else on_interact
            if not event_name or event_name not in entity_data.get("events", {}):
                report_error(f"Behavior entity {identifier} interaction[{index}] references undefined event {event_name!r}")

    recipe_count = 0
    for path in sorted((BP / "recipes").glob("*.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        recipe_count += 1
        for recipe_type in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
            recipe = data.get(recipe_type)
            if recipe is None:
                continue
            result_item = recipe.get("result", {}).get("item")
            if not result_item:
                report_error(f"Recipe {path.name} has no result item")
            elif result_item.startswith("cc:") and result_item not in item_ids:
                report_error(f"Recipe {path.name} produces missing custom item {result_item}")

            key_items = set()
            for key_value in recipe.get("key", {}).values():
                ingredient = key_value.get("item")
                if ingredient:
                    key_items.add(ingredient)
            for ingredient in recipe.get("ingredients", []):
                if ingredient.get("item"):
                    key_items.add(ingredient["item"])
            for ingredient in key_items:
                if ingredient.startswith("cc:") and ingredient not in item_ids and ingredient not in block_ids:
                    report_error(f"Recipe {path.name} uses missing custom ingredient {ingredient}")

            if recipe_type == "minecraft:recipe_shaped":
                pattern = recipe.get("pattern", [])
                key_map = recipe.get("key", {})
                if not pattern or any(len(row) > 3 for row in pattern) or len(pattern) > 3:
                    report_error(f"Shaped recipe {path.name} has an invalid pattern")
                used_symbols = {char for row in pattern for char in row if char != " "}
                if not used_symbols.issubset(key_map):
                    report_error(f"Shaped recipe {path.name} has unmapped pattern symbols {sorted(used_symbols-set(key_map))}")

    if not recipe_count:
        report_error("No crafting recipes found")

    texture_count = len(list(RP.rglob("*.png")))
    report_ok(f"Validated {len(bp_entities)} entities, {len(block_ids)} blocks, {len(item_ids)} items, {len(geometry_by_id)} geometries, {len(animations)} animations, and {recipe_count} recipes")
    return len(bp_entities), len(block_ids), len(item_ids), texture_count


def validate_package(path: Path) -> None:
    print("\n=== .mcaddon package validation ===")
    if not path.is_file():
        report_error(f"Package does not exist: {path}")
        return

    try:
        with zipfile.ZipFile(path) as addon:
            files = {name for name in addon.namelist() if not name.endswith("/")}
            if files != set(EXPECTED_PACKAGES):
                report_error(f".mcaddon must contain exactly {sorted(EXPECTED_PACKAGES)}, found {sorted(files)}")
                return

            manifests: dict[str, dict] = {}
            for package_name, manifest_path in EXPECTED_PACKAGES.items():
                contents = addon.read(package_name)
                with zipfile.ZipFile(io.BytesIO(contents)) as pack:
                    names = [name for name in pack.namelist() if not name.endswith("/")]
                    if "manifest.json" not in names:
                        report_error(f"{package_name} has no root manifest.json")
                        continue
                    if any(name.startswith(("behavior_pack/", "resource_pack/")) for name in names):
                        report_error(f"{package_name} has an invalid nested folder layout")
                    try:
                        manifest = json.loads(pack.read("manifest.json"))
                    except (json.JSONDecodeError, KeyError) as error:
                        report_error(f"Invalid manifest inside {package_name}: {error}")
                        continue
                    if manifest.get("header", {}).get("uuid") != json.loads(manifest_path.read_text()).get("header", {}).get("uuid"):
                        report_error(f"{package_name} contains the wrong pack manifest")
                    if len(names) != len(set(names)):
                        report_error(f"{package_name} contains duplicate archive paths")
                    manifests[package_name] = manifest

            if len(manifests) == len(EXPECTED_PACKAGES):
                report_ok(".mcaddon contains valid, root-level BP/RP .mcpack archives")
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        report_error(f"Unreadable .mcaddon archive {path}: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Also validate the resulting .mcaddon archive")
    args = parser.parse_args()

    validate_json_and_pngs()
    bp_manifest, _ = validate_manifests()
    validate_scripts(bp_manifest)
    counts = validate_pack_references()
    validate_placement_chain()
    if args.package:
        validate_package(args.package.resolve())

    print(f"\n{'=' * 58}")
    print(f"Summary: {len(errors)} error(s)")
    print(f"Entities: {counts[0]}, blocks: {counts[1]}, items: {counts[2]}, textures: {counts[3]}")
    if errors:
        print("BUILD FAILED")
        return 1
    print("BUILD PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
