"""Minimal dependency-free PNG reader/writer.

Bedrock Edition expects 8-bit RGBA PNGs (color type 6) for custom block and
entity textures. The writer here only ever emits that format so the shipped
packs cannot regress into indexed/grayscale PNGs again.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class Image:
    """An RGBA8 raster image."""

    __slots__ = ("width", "height", "pixels")

    def __init__(self, width: int, height: int, fill=(0, 0, 0, 0)):
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(fill) * (width * height))

    def get(self, x: int, y: int) -> tuple[int, int, int, int]:
        offset = (y * self.width + x) * 4
        return tuple(self.pixels[offset:offset + 4])  # type: ignore[return-value]

    def set(self, x: int, y: int, color) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        offset = (y * self.width + x) * 4
        self.pixels[offset:offset + 4] = bytes(color)

    def to_png(self) -> bytes:
        raw = bytearray()
        stride = self.width * 4
        for y in range(self.height):
            raw.append(0)  # filter type: None (keeps the encoder tiny and lossless)
            raw += self.pixels[y * stride:(y + 1) * stride]

        def chunk(tag: bytes, payload: bytes) -> bytes:
            body = tag + payload
            return (
                struct.pack(">I", len(payload))
                + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
            )

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 6, 0, 0, 0)
        return (
            PNG_SIGNATURE
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )

    def save(self, path) -> None:
        with open(path, "wb") as handle:
            handle.write(self.to_png())


def png_color_type(path) -> tuple[int, int, int]:
    """Return (bit_depth, color_type, channels) straight from the IHDR chunk."""
    with open(path, "rb") as handle:
        header = handle.read(26)
    if header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file")
    bit_depth = header[24]
    color_type = header[25]
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 0)
    return bit_depth, color_type, channels
