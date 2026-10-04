"""Animation authoring + sampling.

Animations are written once in Python, exported to Bedrock JSON for the shipped
resource pack, and sampled by the preview renderer so animation frames can be
reviewed without launching the game.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CHANNELS = ("rotation", "position", "scale")


@dataclass
class Animation:
    identifier: str
    length: float
    loop: bool | str = False
    bones: dict[str, dict[str, list[tuple[float, tuple[float, float, float]]]]] = field(default_factory=dict)

    def key(self, bone: str, channel: str, time: float, value) -> "Animation":
        if channel not in CHANNELS:
            raise ValueError(f"unknown channel {channel}")
        self.bones.setdefault(bone, {}).setdefault(channel, []).append((round(float(time), 4), tuple(value)))
        return self

    def offset(self, bone: str, channel: str, value) -> "Animation":
        """Add a constant offset to every key of an existing channel."""
        track = self.bones.get(bone, {}).get(channel)
        if not track:
            return self.key(bone, channel, 0.0, value)
        return self.key(bone, channel, track[-1][0], tuple(track[-1][1][axis] + value[axis] for axis in range(3)))

    def to_json(self) -> dict:
        bones: dict[str, dict] = {}
        for bone, channels in self.bones.items():
            entry: dict[str, dict] = {}
            for channel, keys in channels.items():
                entry[channel] = {f"{time:.4f}".rstrip("0").rstrip("."): list(value) for time, value in sorted(keys)}
            bones[bone] = entry
        payload: dict = {"bones": bones}
        if self.loop:
            payload["loop"] = self.loop if isinstance(self.loop, str) else True
        payload["animation_length"] = self.length
        return payload


def pose_at(animation: Animation, time: float) -> dict:
    """Sample a pose at ``time`` seconds, mirroring Bedrock's linear interpolation."""
    if animation.loop:
        length = animation.length or 1.0
        if length > 0:
            time = time % length

    pose: dict = {}
    for bone, channels in animation.bones.items():
        bone_pose: dict = {}
        for channel, keys in channels.items():
            ordered = sorted(keys)
            if time <= ordered[0][0]:
                bone_pose[channel] = ordered[0][1]
                continue
            if time >= ordered[-1][0]:
                if animation.loop and len(ordered) > 1:
                    # Wrap to the first key for a seamless loop.
                    span = (animation.length - ordered[-1][0]) + ordered[0][0]
                    ratio = (time - ordered[-1][0]) / span if span > 0 else 0.0
                    bone_pose[channel] = _lerp(ordered[-1][1], ordered[0][1], ratio)
                else:
                    bone_pose[channel] = ordered[-1][1]
                continue
            for start, end in zip(ordered, ordered[1:]):
                if start[0] <= time <= end[0]:
                    span = end[0] - start[0]
                    ratio = (time - start[0]) / span if span > 0 else 0.0
                    bone_pose[channel] = _lerp(start[1], end[1], ratio)
                    break
        pose[bone] = bone_pose
    return pose


def _lerp(first, second, ratio: float):
    return tuple(first[axis] + (second[axis] - first[axis]) * ratio for axis in range(3))


def merge(*poses: dict) -> dict:
    """Overlay poses; later poses win per channel (used for strain layers)."""
    merged: dict = {}
    for pose in poses:
        for bone, channels in pose.items():
            merged.setdefault(bone, {}).update(channels)
    return merged


def write_animations(path, animations: list[Animation]) -> None:
    import json
    from pathlib import Path

    payload = {
        "format_version": "1.8.0",
        "animations": {animation.identifier: animation.to_json() for animation in animations},
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
