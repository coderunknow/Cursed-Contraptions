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
RELEASE_VERSION = [0, 1, 0]
MIN_ENGINE_VERSION = [1, 21, 60]
SERVER_API_VERSION = "1.17.0"
EXPECTED_PACKAGES = {
    "Cursed-Contraptions_BP.mcpack": BP / "manifest.json",
    "Cursed-Contraptions_RP.mcpack": RP / "manifest.json",
}
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

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
    return RP / f"{texture.removesuffix('.png')}.png"


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
    release_version = ".".join(map(str, RELEASE_VERSION))
    if package and package.get("version") != release_version:
        report_error(f"package.json must be version {release_version}")
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
            report_error(f"{name} manifest must be version 0.1.0")
        if header.get("min_engine_version") != MIN_ENGINE_VERSION:
            report_error(f"{name} minimum engine version must be 1.21.60")

        modules = pack.get("modules", [])
        module_types = {module.get("type") for module in modules}
        if module_types != expected_module_type:
            report_error(f"{name} manifest modules are {module_types}, expected {expected_module_type}")
        for index, module in enumerate(modules):
            validate_uuid(module.get("uuid"), f"{name} module[{index}]", seen_uuids)
            if module.get("version") != RELEASE_VERSION:
                report_error(f"{name} module[{index}] must be version 0.1.0")
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
            report_error("behavior pack resource dependency UUID/version does not match resource pack v0.1.0")

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
            header = path.read_bytes()[:24]
            if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("invalid PNG signature/header")
            width, height = struct.unpack(">II", header[16:24])
            if width < 1 or height < 1:
                raise ValueError(f"invalid dimensions {width}x{height}")
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

    for path in sorted((BP / "blocks").glob("*.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        block = data.get("minecraft:block", {})
        identifier = block.get("description", {}).get("identifier")
        if not identifier:
            report_error(f"Block has no identifier: {path.relative_to(ROOT)}")
            continue
        if identifier in block_ids:
            report_error(f"Duplicate block identifier: {identifier}")
        block_ids[identifier] = path

    for path in sorted((BP / "items").glob("*.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        item = data.get("minecraft:item", {})
        identifier = item.get("description", {}).get("identifier")
        if not identifier:
            report_error(f"Item has no identifier: {path.relative_to(ROOT)}")
            continue
        if identifier in item_ids:
            report_error(f"Duplicate item identifier: {identifier}")
        item_ids[identifier] = path

    terrain = json_data.get(RP / "textures" / "terrain_texture.json") or load_json(RP / "textures" / "terrain_texture.json") or {}
    item_atlas = json_data.get(RP / "textures" / "item_texture.json") or load_json(RP / "textures" / "item_texture.json") or {}
    terrain_aliases = set(terrain.get("texture_data", {}))
    item_aliases = set(item_atlas.get("texture_data", {}))

    for path in block_ids.values():
        block = (json_data.get(path) or {}).get("minecraft:block", {})
        components = block.get("components", {})
        geometry = components.get("minecraft:geometry")
        material_instances = components.get("minecraft:material_instances", {})
        if geometry and geometry not in geometry_by_id:
            # Populated below; defer this reference check.
            pass
        for instance in material_instances.values():
            alias = instance.get("texture") if isinstance(instance, dict) else None
            if alias and alias not in terrain_aliases:
                report_error(f"Block {path.name} references missing terrain texture alias {alias}")

    for path in sorted((RP / "models" / "entity").glob("*.geo.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        for geometry in data.get("minecraft:geometry", []):
            identifier = geometry.get("description", {}).get("identifier")
            if not identifier:
                report_error(f"Geometry has no identifier: {path.relative_to(ROOT)}")
            elif identifier in geometry_by_id:
                report_error(f"Duplicate geometry identifier: {identifier}")
            else:
                geometry_by_id[identifier] = geometry

    for path in sorted((RP / "animations").glob("*.animation.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        for identifier, definition in data.get("animations", {}).items():
            if identifier in animations:
                report_error(f"Duplicate animation identifier: {identifier}")
            animations[identifier] = definition

    for path in sorted((RP / "animation_controllers").glob("*.animation_controllers.json")):
        data = json_data.get(path) or load_json(path)
        if not data:
            continue
        for identifier, definition in data.get("animation_controllers", {}).items():
            if identifier in controllers:
                report_error(f"Duplicate animation controller identifier: {identifier}")
            controllers[identifier] = definition

    for path in block_ids.values():
        block = (json_data.get(path) or {}).get("minecraft:block", {})
        geometry = block.get("components", {}).get("minecraft:geometry")
        if geometry and geometry not in geometry_by_id:
            report_error(f"Block {path.name} references undefined geometry {geometry}")

    for identifier, path in item_ids.items():
        item = (json_data.get(path) or {}).get("minecraft:item", {})
        components = item.get("components", {})
        icon = components.get("minecraft:icon", {}).get("textures", {}).get("default")
        if icon and icon not in item_aliases:
            report_error(f"Item {identifier} references missing item texture alias {icon}")
        target_block = components.get("minecraft:block_placer", {}).get("block")
        if target_block and target_block not in block_ids:
            report_error(f"Item {identifier} references missing block {target_block}")

    for path, description in rp_entities.values():
        texture_refs = description.get("textures", {}).values()
        for texture in texture_refs:
            texture_file = asset_path_from_texture(texture)
            if not texture_file.is_file():
                report_error(f"Client entity {path.name} references missing texture {texture}")

        geometry_refs = description.get("geometry", {}).values()
        for geometry_id in geometry_refs:
            geometry = geometry_by_id.get(geometry_id)
            if not geometry:
                report_error(f"Client entity {path.name} references undefined geometry {geometry_id}")
                continue
            bone_names = {bone.get("name") for bone in geometry.get("bones", [])}
            for alias, animation_id in description.get("animations", {}).items():
                if alias == "controller":
                    continue
                animation = animations.get(animation_id)
                if not animation:
                    report_error(f"Client entity {path.name} references undefined animation {animation_id}")
                    continue
                missing_bones = set(animation.get("bones", {})) - bone_names
                if missing_bones:
                    report_error(f"Animation {animation_id} references missing bones {sorted(missing_bones)}")

        animation_aliases = description.get("animations", {})
        controller_id = animation_aliases.get("controller")
        if controller_id and controller_id not in controllers:
            report_error(f"Client entity {path.name} references undefined controller {controller_id}")
        for alias, animation_id in animation_aliases.items():
            if alias != "controller" and animation_id not in animations:
                report_error(f"Client entity {path.name} maps {alias} to missing animation {animation_id}")

        scripts = description.get("scripts", {})
        for animated_alias in scripts.get("animate", []):
            if animated_alias not in animation_aliases:
                report_error(f"Client entity {path.name} animates undefined alias {animated_alias}")

        if controller_id in controllers:
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

    for path, block in block_ids.items():
        pass

    # The block registry also maps each custom block to a terrain-atlas alias.
    block_registry_path = RP / "blocks.json"
    block_registry = json_data.get(block_registry_path) or load_json(block_registry_path) or {}
    for identifier, definition in block_registry.items():
        if identifier not in block_ids:
            report_error(f"Resource block registry has no behavior block {identifier}")
        if definition.get("textures") not in terrain_aliases:
            report_error(f"Resource block registry {identifier} references missing texture alias {definition.get('textures')}")
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
    for identifier in bp_entities:
        if f"entity.{identifier}.name" not in language_entries:
            report_error(f"Missing localized entity name for {identifier}")

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
