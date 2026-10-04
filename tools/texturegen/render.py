"""Software preview renderer for the hand-authored device models.

Bedrock cannot be run headless in CI, so this renders the *same* geometry, UVs
and animation data that ship in the packs. It is a review aid: a z-sorted quad
rasterizer with backface culling, alpha test and directional shading.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from canvas import Rect
from model import FACE_NORMALS, FACE_ORDER, Model, face_corners
from png_io import Image

Vec3 = tuple[float, float, float]


# --------------------------------------------------------------------------- #
# transforms
# --------------------------------------------------------------------------- #
def _rotate(point: Vec3, rotation: Vec3) -> Vec3:
    x, y, z = point
    rx, ry, rz = (math.radians(value) for value in rotation)
    # Bedrock applies Z, then Y, then X.
    cos_z, sin_z = math.cos(rz), math.sin(rz)
    x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z
    cos_y, sin_y = math.cos(ry), math.sin(ry)
    x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x
    return (x, y, z)


def bone_transform(bones: dict, name: str, pose: dict):
    """Return a point transform for a bone, composed with its ancestors."""
    bone = bones[name]
    key = pose.get(name, {})
    pivot = bone.pivot
    rotation = key.get("rotation", bone.rotation or (0, 0, 0))
    position = key.get("position", (0, 0, 0))
    scale = key.get("scale", (1, 1, 1))

    def apply(point: Vec3) -> Vec3:
        local = (
            (point[0] - pivot[0]) * scale[0],
            (point[1] - pivot[1]) * scale[1],
            (point[2] - pivot[2]) * scale[2],
        )
        rotated = _rotate(local, rotation)
        return (rotated[0] + pivot[0] + position[0],
                rotated[1] + pivot[1] + position[1],
                rotated[2] + pivot[2] + position[2])

    if bone.parent:
        parent_apply = bone_transform(bones, bone.parent, pose)
        return lambda point: parent_apply(apply(point))
    return apply


def cube_transform(bone_apply, cube):
    if not cube.rotation:
        return bone_apply
    pivot = cube.pivot or (0, 0, 0)

    def apply(point: Vec3) -> Vec3:
        local = (point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2])
        rotated = _rotate(local, tuple(cube.rotation))
        return bone_apply((rotated[0] + pivot[0], rotated[1] + pivot[1], rotated[2] + pivot[2]))

    return apply


@dataclass
class Quad:
    corners: list[Vec3]
    uv: Rect
    atlas: Image
    shade: float
    depth: float


def collect_quads(model: Model, atlas: Image, rects: dict, pose: dict | None = None,
                  light: Vec3 = (0.42, 0.82, -0.38)) -> list[Quad]:
    pose = pose or {}
    bones = {bone.name: bone for bone in model.bones}
    quads: list[Quad] = []

    for bone in model.bones:
        if not rects.get(bone.name):
            continue
        apply = bone_transform(bones, bone.name, pose)
        for cube_index, cube in enumerate(bone.cubes):
            transform = cube_transform(apply, cube)
            corners = face_corners(cube)
            for face in FACE_ORDER:
                rect = rects[bone.name].get(f"{cube_index}:{face}")
                if rect is None:
                    continue
                points = [transform(tuple(point)) for point in corners[face]]
                normal = FACE_NORMALS[face]
                # Rotate the normal by the same chain (sampled from a delta point).
                origin = transform((0.0, 0.0, 0.0))
                normal_world = tuple(
                    transform(tuple(normal))[axis] - origin[axis] for axis in range(3)
                )
                length = math.sqrt(sum(component * component for component in normal_world)) or 1.0
                normal_world = tuple(component / length for component in normal_world)
                lambert = max(0.0, sum(normal_world[axis] * light[axis] for axis in range(3)))
                shade = 0.70 + 0.34 * lambert
                center = tuple(sum(point[axis] for point in points) / 4 for axis in range(3))
                quads.append(Quad(points, rect, atlas, shade, 0.0))
                quads[-1].depth = center
    return quads


def render(model: Model, atlas: Image, rects: dict, size=(220, 260), pose: dict | None = None,
           camera: Vec3 = (1.35, 0.78, -1.75), zoom: float = 1.0, supersample: int = 1) -> Image:
    """Render one frame of the model from a front-right-above hero angle."""
    quads = collect_quads(model, atlas, rects, pose)
    if not quads:
        raise ValueError("no quads to render")

    points = [point for quad in quads for point in quad.corners]
    min_corner = [min(point[axis] for point in points) for axis in range(3)]
    max_corner = [max(point[axis] for point in points) for axis in range(3)]
    center = [(min_corner[axis] + max_corner[axis]) / 2 for axis in range(3)]
    extent = max(max_corner[axis] - min_corner[axis] for axis in range(3)) or 1.0

    camera_length = math.sqrt(sum(component * component for component in camera)) or 1.0
    forward = tuple(-component / camera_length for component in camera)
    world_up = (0.0, 1.0, 0.0)
    right = (
        forward[1] * world_up[2] - forward[2] * world_up[1],
        forward[2] * world_up[0] - forward[0] * world_up[2],
        forward[0] * world_up[1] - forward[1] * world_up[0],
    )
    right_length = math.sqrt(sum(component * component for component in right)) or 1.0
    right = tuple(component / right_length for component in right)
    up = (
        right[1] * forward[2] - right[2] * forward[1],
        right[2] * forward[0] - right[0] * forward[2],
        right[0] * forward[1] - right[1] * forward[0],
    )

    width, height = size[0] * supersample, size[1] * supersample
    scale = (min(width, height) / (extent * 1.62)) * zoom

    def project(point: Vec3):
        relative = (point[0] - center[0], point[1] - center[1], point[2] - center[2])
        screen_x = sum(relative[axis] * right[axis] for axis in range(3))
        screen_y = sum(relative[axis] * up[axis] for axis in range(3))
        depth = sum(relative[axis] * forward[axis] for axis in range(3))
        return (width / 2 + screen_x * scale, height / 2 - screen_y * scale, depth)

    shaded = Image(width, height)

    # Painter's algorithm: farthest first. "depth" grows away from the camera,
    # so the largest values must be drawn before the near ones.
    for quad in sorted(quads, key=lambda item: -sum(
        sum(point[axis] * forward[axis] for axis in range(3)) for point in item.corners
    )):
        projected = [project(point) for point in quad.corners]
        # Backface cull using the screen-space winding.
        area = 0.0
        for index in range(4):
            x0, y0, _ = projected[index]
            x1, y1, _ = projected[(index + 1) % 4]
            area += x0 * y1 - x1 * y0
        if area >= 0:
            continue
        for triangle in ((0, 1, 2), (0, 2, 3)):
            _rasterize_triangle(
                shaded, quad, [projected[index] for index in triangle],
                [((0 if index in (0, 3) else quad.uv.width), (0 if index in (0, 1) else quad.uv.height))
                 for index in triangle],
            )

    if supersample > 1:
        downscaled = Image(width // supersample, height // supersample)
        for y in range(downscaled.height):
            for x in range(downscaled.width):
                samples = []
                for offset_y in range(supersample):
                    for offset_x in range(supersample):
                        pixel = shaded.get(x * supersample + offset_x, y * supersample + offset_y)
                        if pixel[3] > 0:
                            samples.append(pixel)
                if samples:
                    average = tuple(round(sum(sample[channel] for sample in samples) / len(samples))
                                    for channel in range(4))
                    downscaled.set(x, y, average)
        return downscaled
    return shaded


def _rasterize_triangle(target: Image, quad: Quad, vertices, uvs) -> None:
    (x0, y0, _), (x1, y1, _), (x2, y2, _) = vertices
    min_x = max(0, int(math.floor(min(x0, x1, x2))))
    max_x = min(target.width - 1, int(math.ceil(max(x0, x1, x2))))
    min_y = max(0, int(math.floor(min(y0, y1, y2))))
    max_y = min(target.height - 1, int(math.ceil(max(y0, y1, y2))))
    if min_x > max_x or min_y > max_y:
        return

    denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(denominator) < 1e-9:
        return

    rect = quad.uv
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            sample_x = x + 0.5
            sample_y = y + 0.5
            weight0 = ((y1 - y2) * (sample_x - x2) + (x2 - x1) * (sample_y - y2)) / denominator
            weight1 = ((y2 - y0) * (sample_x - x2) + (x0 - x2) * (sample_y - y2)) / denominator
            weight2 = 1 - weight0 - weight1
            if weight0 < -1e-6 or weight1 < -1e-6 or weight2 < -1e-6:
                continue
            u = uvs[0][0] * weight0 + uvs[1][0] * weight1 + uvs[2][0] * weight2
            v = uvs[0][1] * weight0 + uvs[1][1] * weight1 + uvs[2][1] * weight2
            texel_x = rect.x + min(rect.width - 1, max(0, int(u)))
            texel_y = rect.y + min(rect.height - 1, max(0, int(v)))
            color = quad.atlas.get(texel_x, texel_y)
            if color[3] < 128:
                continue
            shaded_color = (
                min(255, round(color[0] * quad.shade)),
                min(255, round(color[1] * quad.shade)),
                min(255, round(color[2] * quad.shade)),
                255,
            )
            target.set(x, y, shaded_color)


def render_to_file(model: Model, atlas: Image, rects: dict, path: Path, **kwargs) -> None:
    image = render(model, atlas, rects, **kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
