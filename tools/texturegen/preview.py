"""Render QA previews of the device models, including animation frames.

Dev-only tool: nothing in this file ships inside the .mcaddon.

Usage::

    python3 tools/texturegen/preview.py iron_maiden [frame_time ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "devices"))

from anim import pose_at  # noqa: E402
from png_io import Image  # noqa: E402
from model import bake_atlas, pack_faces  # noqa: E402
from render import render  # noqa: E402

PREVIEW_DIR = ROOT / "previews"

DEVICES = {
    "iron_maiden": ("iron_maiden", "animations"), 
}


def atlas_zoom(atlas: Image, factor: int) -> Image:
    """Nearest-neighbour upscale so 1-texel detail is reviewable by eye."""
    zoomed = Image(atlas.width * factor, atlas.height * factor)
    for y in range(zoomed.height):
        for x in range(zoomed.width):
            zoomed.set(x, y, atlas.get(x // factor, y // factor))
    return zoomed


def load(slug: str):
    module = __import__(slug)
    return module.build()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: preview.py <device> [state[:time] ...]")
        return 2
    slug = argv[1]
    art = load(slug)
    atlas, uv_map = bake_atlas(art.model, seed=7)
    rects, _ = pack_faces(art.model)

    jobs = argv[2:]
    if not jobs:
        jobs = ["idle:0", "detect:0.5", "close:0.6", "torture:1.0", "strain:0.12", "open:0.6", "broken:1.4"]
    if "atlas" in jobs:
        atlas.save(PREVIEW_DIR / f"{slug}_atlas.png")
        atlas_zoom(atlas, 5).save(PREVIEW_DIR / f"{slug}_atlas_x5.png")

    for job in jobs:
        if job == "atlas":
            continue
        name, _, time_text = job.partition(":")
        time = float(time_text) if time_text else 0.0
        animation = next((a for a in art.animations if a.identifier.endswith(f".{name}")), None)
        pose = pose_at(animation, time) if animation else {}
        target = PREVIEW_DIR / f"{slug}_{name}_{time:g}.png"
        image = render(art.model, atlas, rects, size=(240, 280), pose=pose, supersample=2)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target)
        print(f"wrote {target.relative_to(ROOT.parent.parent)} ({image.width}x{image.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
