"""Packaging pipeline: animation controllers and client entity files.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from anim import Animation
from model import Model

# The device state names shared with the behavior pack. Each has a matching
# ``cc:anim_<state>`` tag on the entity, which is what the animation controller
# reads (tags are the only client-visible signal available on the stable API).
DEVICE_STATES = (
    "idle",
    "detecting",
    "capturing",
    "closed",
    "torturing",
    "opening",
    "released",
    "broken",
)

# States the strain overlay may interrupt, and how long the rattle holds.
STRAIN_DURATION = 0.6


@dataclass
class DeviceArt:
    """Everything the resource pack needs for one device."""

    slug: str
    display_name: str
    model: Model
    animations: list[Animation]
    state_animations: dict[str, list[str]]
    particle: str = "minecraft:basic_smoke_particle"
    accent_particle: str = "minecraft:basic_flame_particle"
    material: str = "entity_alphatest"
    # state -> (overlay state name, overlay duration in seconds)
    strain: dict[str, tuple[str, float]] = field(default_factory=dict)

    @property
    def controller_id(self) -> str:
        return f"controller.animation.cc_{self.slug}.state"


def controller_json(device: DeviceArt) -> dict:
    """Emit the animation controller for one device.

    Every gameplay state must be reachable from every other state: the server
    drives the controller purely through ``cc:anim_<state>`` tags, and state
    changes (redstone, resets, reconnect recovery) are not always adjacent.
    Strain overlays are short-lived states that play a one-shot rattle before
    falling back to the state underneath.
    """
    states: dict[str, dict] = {}

    for state in DEVICE_STATES:
        entry: dict = {"animations": list(device.state_animations.get(state, []))}
        transitions: list[dict] = []

        if state in device.strain:
            overlay = device.strain[state][0]
            transitions.append({overlay: "q.has_tag('cc:anim_strain')"})

        if state != "broken":
            # The behavior pack is authoritative: it sets exactly one
            # ``cc:anim_<state>`` tag at a time, and every state must be
            # reachable from every other (redstone resets, reconnect recovery
            # and forced releases are not limited to adjacent transitions).
            for candidate in DEVICE_STATES:
                if candidate == state:
                    continue
                transitions.append({candidate: f"q.has_tag('cc:anim_{candidate}')"})

        entry["transitions"] = transitions
        states[state] = entry

    for state, (overlay, duration) in device.strain.items():
        # The overlay runs for a fixed time, then hands back to the state it
        # interrupted (or follows the server if that state already moved on).
        overlay_transitions: list[dict] = [
            {state: f"!q.has_tag('cc:anim_strain') || q.anim_time > {duration}"}
        ]
        for candidate in DEVICE_STATES:
            if candidate == state:
                continue
            if candidate == "idle":
                continue
            overlay_transitions.append({candidate: f"q.has_tag('cc:anim_{candidate}')"})
        overlay_transitions.append({"idle": "q.has_tag('cc:anim_idle')"})
        states[overlay] = {
            "animations": ["strain"],
            "blend_transition": 0.1,
            "transitions": overlay_transitions,
        }

    return {
        "format_version": "1.10.0",
        "animation_controllers": {
            device.controller_id: {
                "initial_state": "idle",
                "states": states,
            }
        },
    }


def client_entity_json(device: DeviceArt) -> dict:
    animations = {
        animation.identifier.replace(f"animation.cc_{device.slug}.", ""): animation.identifier
        for animation in device.animations
    }
    animations["controller"] = device.controller_id
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"cc:{device.slug}",
                "materials": {"default": device.material},
                "textures": {"default": f"textures/entity/{device.slug}"},
                "geometry": {"default": device.model.identifier},
                "animations": animations,
                "scripts": {"animate": ["controller"]},
                "render_controllers": ["controller.render.default"],
            }
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
