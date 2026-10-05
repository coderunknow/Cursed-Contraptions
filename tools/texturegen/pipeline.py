"""Packaging pipeline: animation controllers, wear stages, and client entities.

The server drives the client purely through ``cc:anim_*`` tags plus the
client-synced ``cc:charge`` property, because a behavior pack cannot call the
beta animation APIs. Everything below turns that small signal set into real
animation state.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from anim import Animation
from model import Model, model_bounds

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

# Extra states layered on top of the base states:
# * ``torturing_high`` is a hotter loop the controller switches to from the
#   client-synced soul-charge property, so an escalating device visibly works
#   itself up without needing a second tag.
# * ``*_strain`` / ``*_burst`` are short one-shots that interrupt an occupied
#   state (the captive rattling the frame, and the discharge on a damage tick).
TIER_STATES = {"torturing": (("torturing_high", "q.property('cc:charge') >= 3"),)}
TIER_FALLBACK = "q.property('cc:charge') < 3"
OVERLAYS = {
    "closed": ("strain",),
    "torturing": ("strain", "burst"),
}
OVERLAY_DURATION = {"strain": 0.7, "burst": 0.45}

# Animations every device must ship for the controller above to resolve.
REQUIRED_ANIMATIONS = (
    "idle", "detect", "close", "closed", "torture", "torture_high",
    "strain", "burst", "open", "released", "broken",
)

# Damage stages: ``cc:anim_wear_<stage>`` tags, driven by remaining durability.
WEAR_STAGES = 4
WEAR_THRESHOLD_COMMENT = (
    "wear_0 = pristine, wear_1..3 = progressively cracked (see CONFIG.wear)"
)


def overlay_state_name(base: str, overlay: str) -> str:
    return f"{base}_{overlay}"


@dataclass
class DeviceArt:
    """Everything the resource pack needs for one device."""

    slug: str
    display_name: str
    model: Model
    animations: list[Animation]
    particle: str = "minecraft:basic_smoke_particle"
    accent_particle: str = "minecraft:basic_flame_particle"
    material: str = "entity_alphatest"
    # Extra device-specific flourish, e.g. the Iron Maiden's nail bed.
    seat_height: float = 0.0

    @property
    def controller_id(self) -> str:
        return f"controller.animation.cc_{self.slug}.state"

    @property
    def wear_controller_id(self) -> str:
        return f"controller.animation.cc_{self.slug}.wear"

    def animation_id(self, name: str) -> str:
        return f"animation.cc_{self.slug}.{name}"

    def animation_names(self) -> set[str]:
        prefix = f"animation.cc_{self.slug}."
        return {
            animation.identifier[len(prefix):]
            for animation in self.animations
            if animation.identifier.startswith(prefix)
        }


def _state_tag(state: str) -> str:
    """Tag that selects a controller state (tier states share the base tag)."""
    for base, tiers in TIER_STATES.items():
        if state == base or state in [tier for tier, _ in tiers]:
            return base
    for base, overlays in OVERLAYS.items():
        for overlay in overlays:
            if state == overlay_state_name(base, overlay):
                return overlay
    return state


def _state_animation(device: DeviceArt, state: str) -> str:
    """Animation alias a controller state plays, derived from its name."""
    if state.endswith("_strain"):
        return "strain"
    if state.endswith("_burst"):
        return "burst"
    if state == "torturing_high":
        return "torture_high"
    return {
        "detecting": "detect",
        "capturing": "close",
        "torturing": "torture",
        "opening": "open",
    }.get(state, state)


def controller_json(device: DeviceArt) -> dict:
    """Emit the state controller for one device.

    Every gameplay state is reachable from every other state: state changes
    (redstone resets, reconnect recovery, forced releases) are not always
    adjacent, and the unit test that walks the graph requires it.
    """
    base_states = list(DEVICE_STATES)
    tier_states = [tier for base in DEVICE_STATES for tier, _ in TIER_STATES.get(base, ())]
    all_states = base_states + tier_states
    overlay_states = [
        overlay_state_name(base, overlay)
        for base in DEVICE_STATES
        for overlay in OVERLAYS.get(base, ())
    ]

    states: dict[str, dict] = {}

    for state in all_states:
        entry: dict = {"animations": [_state_animation(device, state)]}
        transitions: list[dict] = []

        for base in DEVICE_STATES:
            for overlay in OVERLAYS.get(base, ()):
                overlay_name = overlay_state_name(base, overlay)
                if base == state or (state in tier_states and TIER_STATES.get(base) and
                                     state == TIER_STATES[base][0][0]):
                    transitions.append({overlay_name: f"q.has_tag('cc:anim_{overlay}')"})

        if state not in tier_states:
            for tier, condition in TIER_STATES.get(state, ()):
                transitions.append({tier: condition})

        if state == "broken":
            entry["transitions"] = transitions
            states[state] = entry
            continue

        for candidate in all_states:
            if candidate == state:
                continue
            if candidate in tier_states:
                continue
            transitions.append({candidate: f"q.has_tag('cc:anim_{_state_tag(candidate)}')"})

        if state in tier_states:
            base = next(base for base in TIER_STATES if TIER_STATES[base][0][0] == state)
            transitions.append({base: TIER_FALLBACK})

        entry["transitions"] = transitions
        states[state] = entry

    for overlay_state in overlay_states:
        base, _, overlay = overlay_state.rpartition("_")
        duration = OVERLAY_DURATION[overlay]
        transitions: list[dict] = [{
            base: f"!q.has_tag('cc:anim_{overlay}') || q.anim_time > {duration}",
        }]
        for candidate in all_states:
            if candidate == base or candidate in tier_states:
                continue
            transitions.append({candidate: f"q.has_tag('cc:anim_{_state_tag(candidate)}')"})
        states[overlay_state] = {
            "animations": [_state_animation(device, overlay_state)],
            "blend_transition": 0.1,
            "transitions": transitions,
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


def wear_animations(device: DeviceArt) -> list[Animation]:
    """Build the four durability animations from ``wear_<stage>_*`` bones.

    A wear bone is authored on (or just outside) a surface; every animation
    except its own stage buries it under the device, so a freshly placed
    contraption shows no damage and each later stage adds one more set of
    cracks. Stage 0 buries every plate, which also covers the single frame
    before the client has evaluated the wear controller.
    """
    model = device.model
    _, min_y, _, _, max_y, _ = model_bounds(model)
    burial = -(max_y - min_y) - 8.0
    stages: dict[int, list[str]] = {}
    for bone in model.bones:
        if not bone.name.startswith("wear_"):
            continue
        _, _, rest = bone.name.partition("_")
        stage_text, _, _ = rest.partition("_")
        if not stage_text.isdigit():
            raise ValueError(f"wear bone {bone.name} must be named wear_<stage>_<name>")
        stages.setdefault(int(stage_text), []).append(bone.name)

    animations: list[Animation] = []
    for stage in range(WEAR_STAGES):
        animation = Animation(device.animation_id(f"wear_{stage}"), 0.1, loop="hold_on_last_frame")
        for bone_stage, names in sorted(stages.items()):
            offset = (0.0, 0.0, 0.0) if bone_stage <= stage else (0.0, burial, 0.0)
            for name in names:
                animation.key(name, "position", 0.0, offset)
                animation.key(name, "position", 0.1, offset)
        animations.append(animation)
    return animations


def wear_controller_json(device: DeviceArt) -> dict:
    states: dict[str, dict] = {}
    for stage in range(WEAR_STAGES):
        states[f"wear_{stage}"] = {
            "animations": [f"wear_{stage}"],
            "transitions": [
                {f"wear_{other}": f"q.has_tag('cc:anim_wear_{other}')"}
                for other in range(WEAR_STAGES)
                if other != stage
            ],
        }
    return {
        "format_version": "1.10.0",
        "animation_controllers": {
            device.wear_controller_id: {
                "initial_state": "wear_0",
                "states": states,
            }
        },
    }


def client_entity_json(device: DeviceArt) -> dict:
    animations = {
        animation.identifier.replace(f"animation.cc_{device.slug}.", ""): animation.identifier
        for animation in device.animations
    }
    animations["state"] = device.controller_id
    animations["wear"] = device.wear_controller_id
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"cc:{device.slug}",
                "materials": {"default": device.material},
                "textures": {"default": f"textures/entity/{device.slug}"},
                "geometry": {"default": device.model.identifier},
                "animations": animations,
                "scripts": {"animate": ["state", "wear"]},
                "render_controllers": ["controller.render.default"],
            }
        },
    }


def scale_device(art: DeviceArt, factor: float) -> DeviceArt:
    """Resize a finished device definition by an integer-friendly factor.

    Devices are authored in model units (1 unit = 1 texel = 1/16 block, which
    keeps the art crisp); the world size is a separate decision, applied here in
    one place so geometry, wear burial and animation offsets can never disagree.
    Rotation keys are in degrees and scale keys are ratios, so only pivots,
    cube boxes and position offsets are touched.
    """
    if factor == 1.0:
        return art
    for bone in art.model.bones:
        bone.pivot = [value * factor for value in bone.pivot]
        for cube in bone.cubes:
            cube.origin = [value * factor for value in cube.origin]
            cube.size = [value * factor for value in cube.size]
            cube.inflate = cube.inflate * factor
            if cube.pivot:
                cube.pivot = [value * factor for value in cube.pivot]
    art.model.visible_bounds = tuple(value * factor for value in art.model.visible_bounds)
    art.model.visible_offset = tuple(value * factor for value in art.model.visible_offset)
    for animation in art.animations:
        for channels in animation.bones.values():
            if "position" in channels:
                channels["position"] = [
                    (time, tuple(value * factor for value in offset))
                    for time, offset in channels["position"]
                ]
    return art


def collision_from_model(art: DeviceArt, margin: float = 0.0, ignore: tuple = ()) -> dict:
    """Derive the entity hitbox from the model, in blocks.

    Keeping the hitbox tied to the geometry means a resized device can never
    leave a mismatched box behind (the v0.1.3 models were 40% shorter than the
    boxes they used). ``ignore`` skips protrusions like a crank wheel or a
    hanging chain, which should not inflate the box you have to click.
    """
    min_x, min_y, min_z, max_x, max_y, max_z = model_bounds(art.model, ignore=ignore)
    return {
        "width": round(max(max_x - min_x, max_z - min_z) / 16 + margin, 2),
        "height": round((max_y - min_y) / 16, 2),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
