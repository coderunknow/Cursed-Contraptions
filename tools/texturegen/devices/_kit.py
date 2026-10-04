"""Shared helpers for the device definitions.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from artkit import IRON_BLACK, STEEL_DARK
from model import Face
from pipeline import DeviceArt

STANDARD_STATES = {
    "idle": ["idle"],
    "detecting": ["detect"],
    "capturing": ["close"],
    "closed": ["closed"],
    "torturing": ["torture"],
    "opening": ["open"],
    "released": ["released"],
    "broken": ["broken"],
}

STRAIN_STATES = {
    "closed": ("closed_strain", 0.6),
    "torturing": ("torture_strain", 0.6),
}


def flat_face(color, key: str, size: tuple[int, int] = (1, 1)) -> Face:
    """A shared flat patch: one texel costs no atlas space no matter the use count."""
    from artkit import flat

    return Face(paint=flat(color), size=size, share=f"flat:{key}")


def hidden_faces(dark=IRON_BLACK) -> dict[str, Face]:
    """Faces that are never visible but must still be textured."""
    return {
        "north": flat_face(dark, "hidden_dark"),
        "south": flat_face(dark, "hidden_dark"),
        "east": flat_face(dark, "hidden_dark"),
        "west": flat_face(dark, "hidden_dark"),
        "up": flat_face(dark, "hidden_dark"),
        "down": flat_face(dark, "hidden_dark"),
    }


def shared_face(paint, key: str, size: tuple[int, int] | None = None,
                flip_u: bool = False, flip_v: bool = False) -> Face:
    return Face(paint=paint, size=size, share=key, flip_u=flip_u, flip_v=flip_v)


def finalize(art: DeviceArt) -> DeviceArt:
    """Apply the standard state->animation mapping and strain overlays."""
    art.state_animations = dict(STANDARD_STATES)
    for state, (overlay, _) in STRAIN_STATES.items():
        art.state_animations[overlay] = ["strain"]
    art.strain = dict(STRAIN_STATES)
    return art


STEEL_FLAT = lambda: flat_face(STEEL_DARK, "steel_dark")  # noqa: E731
