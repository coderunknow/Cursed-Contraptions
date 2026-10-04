"""Box-model definition, face-atlas packing, geometry JSON writer, and baking.

A device definition lives in Python as bones + cubes. Every cube face carries
its own painter, and the packer allocates a texel region for it inside the
device atlas. The same definition therefore drives:

* ``resource_pack/models/entity/<device>.geo.json`` (per-face UV geometry)
* ``resource_pack/textures/entity/<device>.png`` (atlas art)
* the software preview renderer used for human review

Face orientation follows the standard "viewed from outside" convention used by
Bedrock per-face UVs: U runs to the viewer's right and V runs downward.
Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from canvas import Painter, Rect
from png_io import Image

# Face -> (right axis, down axis) in model space (X east, Y up, Z south),
# expressed as the direction the texture's +U / +V axes travel.
FACE_AXES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "north": ((-1, 0, 0), (0, -1, 0)),
    "south": ((1, 0, 0), (0, -1, 0)),
    "east": ((0, 0, 1), (0, -1, 0)),
    "west": ((0, 0, -1), (0, -1, 0)),
    "up": ((1, 0, 0), (0, 0, 1)),
    "down": ((1, 0, 0), (0, 0, -1)),
}

FACE_NORMALS: dict[str, tuple[int, int, int]] = {
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "east": (1, 0, 0),
    "west": (-1, 0, 0),
    "up": (0, 1, 0),
    "down": (0, -1, 0),
}

FACE_ORDER = ("north", "south", "east", "west", "up", "down")


def face_pixel_size(face: str, size: list[float], inflate: float = 0.0) -> tuple[int, int]:
    """Texel size of one cube face, mirroring Bedrock's integer UV rounding."""
    width = max(1, round(size[0] + 2 * inflate))
    height = max(1, round(size[1] + 2 * inflate))
    depth = max(1, round(size[2] + 2 * inflate))
    if face in ("north", "south"):
        return width, height
    if face in ("east", "west"):
        return depth, height
    return width, depth


@dataclass
class Face:
    """One cube face: a painter plus an optional resolution/flip/share override.

    ``share`` lets several faces reuse a single atlas patch (mirrors, hidden
    faces, repeated bars/plates) which keeps the atlas small and tidy.
    """

    paint: object | None = None
    size: tuple[int, int] | None = None
    flip_u: bool = False
    flip_v: bool = False
    share: str | None = None

    def dimensions(self, face: str, cube_size: list[float], inflate: float) -> tuple[int, int]:
        return self.size or face_pixel_size(face, cube_size, inflate)


@dataclass
class Cube:
    origin: list[float]
    size: list[float]
    faces: dict[str, Face] = field(default_factory=dict)
    inflate: float = 0.0
    rotation: list[float] | None = None
    pivot: list[float] | None = None


@dataclass
class Bone:
    name: str
    pivot: list[float]
    parent: str | None = None
    rotation: list[float] | None = None
    binding: str | None = None
    cubes: list[Cube] = field(default_factory=list)

    def cube(self, origin, size, faces=None, **kwargs) -> Cube:
        cube = Cube(origin=list(origin), size=list(size), faces=faces or {}, **kwargs)
        self.cubes.append(cube)
        return cube


@dataclass
class Model:
    identifier: str
    texture_width: int = 64
    texture_height: int = 64
    visible_bounds: tuple[float, float] = (2.0, 2.5)
    visible_offset: tuple[float, float, float] = (0.0, 1.25, 0.0)
    atlas_gutter: int = 1
    bones: list[Bone] = field(default_factory=list)

    def bone(self, name: str, pivot, parent: str | None = None, rotation=None, binding=None) -> Bone:
        if any(existing.name == name for existing in self.bones):
            raise ValueError(f"duplicate bone {name}")
        created = Bone(name=name, pivot=list(pivot), parent=parent, rotation=rotation, binding=binding)
        self.bones.append(created)
        return created

    def all_cubes(self):
        for bone in self.bones:
            for cube in bone.cubes:
                yield bone, cube


def face_groups(model: Model) -> dict[str, list[tuple[int, int, str, Face]]]:
    """Group faces by atlas patch key so shared art is painted only once."""
    groups: dict[str, list[tuple[int, int, str, Face]]] = {}
    for bone_index, bone in enumerate(model.bones):
        for cube_index, cube in enumerate(bone.cubes):
            for face in FACE_ORDER:
                spec = cube.faces.get(face)
                if spec is None:
                    continue
                key = spec.share or f"{bone.name}#{cube_index}:{face}"
                groups.setdefault(key, []).append((bone_index, cube_index, face, spec))
    return groups


def pack_faces(model: Model) -> tuple[dict[str, dict[str, Rect]], dict[str, list]]:
    """Shelf-pack each atlas patch: ``({bone: {"cube:face": Rect}}, groups)``."""
    groups = face_groups(model)
    entries = []
    for key, members in groups.items():
        bone_index, cube_index, face, spec = members[0]
        cube = model.bones[bone_index].cubes[cube_index]
        width, height = spec.dimensions(face, cube.size, cube.inflate)
        entries.append((width * height, key, width, height))

    entries.sort(key=lambda entry: (-entry[0], entry[1]))

    placements: dict[str, Rect] = {}
    cursor_x = 0
    cursor_y = 0
    row_height = 0
    for _, key, width, height in entries:
        if cursor_x + width > model.texture_width:
            cursor_x = 0
            cursor_y += row_height + model.atlas_gutter
            row_height = 0
        if cursor_y + height > model.texture_height:
            raise ValueError(
                f"{model.identifier}: atlas overflow while packing {key} "
                f"({width}x{height}) into {model.texture_width}x{model.texture_height}"
            )
        placements[key] = Rect(cursor_x, cursor_y, width, height)
        cursor_x += width + model.atlas_gutter
        row_height = max(row_height, height)

    rects: dict[str, dict[str, Rect]] = {}
    for key, members in groups.items():
        rect = placements[key]
        for bone_index, cube_index, face, _ in members:
            rects.setdefault(model.bones[bone_index].name, {})[f"{cube_index}:{face}"] = rect
    return rects, groups


def bake_atlas(model: Model, seed: int = 1) -> tuple[Image, dict[str, dict[str, dict]]]:
    """Paint the atlas and return ``(image, uv_map)`` ready for geometry export."""
    rects, groups = pack_faces(model)
    image = Image(model.texture_width, model.texture_height)

    for group_index, (key, members) in enumerate(sorted(groups.items())):
        bone_index, cube_index, face, spec = members[0]
        rect = rects[model.bones[bone_index].name][f"{cube_index}:{face}"]
        painter = Painter(image, rect, seed * 7919 + group_index * 131)
        if spec.paint is not None:
            spec.paint(painter)
        # entity_alphatest drops anything under 50% alpha, so no shipped texel
        # may be left semi-transparent.
        painter.opaque()

    uv_map: dict[str, dict[str, dict]] = {}
    for bone in model.bones:
        cube_uv: dict[str, dict] = {}
        for cube_index, cube in enumerate(bone.cubes):
            face_uv: dict[str, dict] = {}
            for face in FACE_ORDER:
                spec = cube.faces.get(face)
                if spec is None:
                    continue
                rect = rects[bone.name].get(f"{cube_index}:{face}")
                if rect is None:
                    continue
                uv_size = [rect.width, rect.height]
                if spec.flip_u:
                    uv_size[0] = -uv_size[0]
                if spec.flip_v:
                    uv_size[1] = -uv_size[1]
                face_uv[face] = {"uv": [rect.x, rect.y], "uv_size": uv_size}
            if face_uv:
                cube_uv[str(cube_index)] = face_uv
        uv_map[bone.name] = cube_uv

    return image, uv_map


def geometry_json(model: Model, uv_map: dict[str, dict[str, dict]]) -> dict:
    bones = []
    for bone in model.bones:
        entry: dict = {"name": bone.name, "pivot": bone.pivot}
        if bone.parent:
            entry["parent"] = bone.parent
        if bone.rotation:
            entry["rotation"] = bone.rotation
        if bone.binding:
            entry["binding"] = bone.binding
        cubes = []
        for cube_index, cube in enumerate(bone.cubes):
            faces = uv_map.get(bone.name, {}).get(str(cube_index))
            if not faces:
                continue
            cube_entry: dict = {
                "origin": cube.origin,
                "size": cube.size,
                "uv": {face: faces[face] for face in FACE_ORDER if face in faces},
            }
            if cube.inflate:
                cube_entry["inflate"] = cube.inflate
            if cube.rotation:
                cube_entry["rotation"] = cube.rotation
                cube_entry["pivot"] = cube.pivot or bone.pivot
            cubes.append(cube_entry)
        if cubes:
            entry["cubes"] = cubes
        bones.append(entry)

    return {
        "format_version": "1.16.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": model.identifier,
                    "texture_width": model.texture_width,
                    "texture_height": model.texture_height,
                    "visible_bounds_width": model.visible_bounds[0],
                    "visible_bounds_height": model.visible_bounds[1],
                    "visible_bounds_offset": list(model.visible_offset),
                },
                "bones": bones,
            }
        ],
    }


def write_geometry(model: Model, path: Path, uv_map: dict[str, dict[str, dict]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(geometry_json(model, uv_map), handle, indent=2)
        handle.write("\n")


def face_corners(cube: Cube) -> dict[str, list[list[float]]]:
    """Four corners per face, ordered (0,0) (1,0) (1,1) (0,1) for the face's UV axes."""
    inflate = cube.inflate
    x0 = cube.origin[0] - inflate
    y0 = cube.origin[1] - inflate
    z0 = cube.origin[2] - inflate
    x1 = cube.origin[0] + cube.size[0] + inflate
    y1 = cube.origin[1] + cube.size[1] + inflate
    z1 = cube.origin[2] + cube.size[2] + inflate

    return {
        "north": [[x1, y1, z0], [x0, y1, z0], [x0, y0, z0], [x1, y0, z0]],
        "south": [[x0, y1, z1], [x1, y1, z1], [x1, y0, z1], [x0, y0, z1]],
        "east": [[x1, y1, z0], [x1, y1, z1], [x1, y0, z1], [x1, y0, z0]],
        "west": [[x0, y1, z1], [x0, y1, z0], [x0, y0, z0], [x0, y0, z1]],
        "up": [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]],
        "down": [[x0, y0, z1], [x1, y0, z1], [x1, y0, z0], [x0, y0, z0]],
    }
