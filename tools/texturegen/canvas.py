"""Pixel-art drawing helpers used to hand-author the device textures.

Everything works on an :class:`png_io.Image` plus an explicit ``Rect`` region so
each cube face can be painted independently inside the packed atlas.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

from dataclasses import dataclass

from png_io import Image

Color = tuple[int, int, int, int]


def rgba(value: str | tuple, alpha: int = 255) -> Color:
    """Accept ``"#rrggbb"``/``"#rrggbbaa"`` strings or RGB(A) tuples."""
    if isinstance(value, tuple):
        if len(value) == 3:
            return (value[0], value[1], value[2], alpha)
        return (value[0], value[1], value[2], value[3])
    text = value.lstrip("#")
    red = int(text[0:2], 16)
    green = int(text[2:4], 16)
    blue = int(text[4:6], 16)
    if len(text) >= 8:
        alpha = int(text[6:8], 16)
    return (red, green, blue, alpha)


def mix(first: Color, second: Color, amount: float) -> Color:
    """Linear blend; ``amount`` 0 keeps ``first``, 1 returns ``second``."""
    ratio = max(0.0, min(1.0, amount))
    return (
        round(first[0] + (second[0] - first[0]) * ratio),
        round(first[1] + (second[1] - first[1]) * ratio),
        round(first[2] + (second[2] - first[2]) * ratio),
        round(first[3] + (second[3] - first[3]) * ratio),
    )


def shade(color: Color, amount: float) -> Color:
    """Darken (negative) or lighten (positive) a color."""
    if amount >= 0:
        return mix(color, (255, 255, 255, color[3]), amount)
    return mix(color, (0, 0, 0, color[3]), -amount)


def with_alpha(color: Color, alpha: int) -> Color:
    return (color[0], color[1], color[2], max(0, min(255, alpha)))


@dataclass(frozen=True)
class Rect:
    """A texel region inside an atlas. ``x``/``y`` are the top-left corner."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    def at(self, column: int, row: int) -> tuple[int, int]:
        """Absolute texel coordinate for a cell inside this rect (top-left origin)."""
        return self.x + column, self.y + row


class Rng:
    """Tiny deterministic PRNG so texture grime is stable across runs."""

    def __init__(self, seed: int):
        self.state = (seed or 1) & 0xFFFFFFFF

    def next(self) -> int:
        self.state ^= (self.state << 13) & 0xFFFFFFFF
        self.state ^= self.state >> 17
        self.state ^= (self.state << 5) & 0xFFFFFFFF
        return self.state & 0xFFFFFFFF

    def unit(self) -> float:
        return self.next() / 0xFFFFFFFF

    def below(self, chance: float) -> bool:
        return self.unit() < chance

    def between(self, low: int, high: int) -> int:
        if high <= low:
            return low
        return low + self.next() % (high - low + 1)


class Painter:
    """Convenience wrapper binding an image, a rect, and a deterministic RNG."""

    def __init__(self, image: Image, rect: Rect, seed: int):
        self.image = image
        self.rect = rect
        self.rng = Rng(seed)

    # -- primitives ---------------------------------------------------------
    def px(self, column: int, row: int, color: Color) -> None:
        x, y = self.rect.at(column, row)
        self.image.set(x, y, color)

    def fill(self, color: Color) -> None:
        self.box(0, 0, self.rect.width, self.rect.height, color)

    def box(self, column: int, row: int, width: int, height: int, color: Color) -> None:
        for row_index in range(row, row + height):
            if row_index < 0 or row_index >= self.rect.height:
                continue
            for column_index in range(column, column + width):
                if 0 <= column_index < self.rect.width:
                    self.px(column_index, row_index, color)

    def outline(self, color: Color, inset: int = 0) -> None:
        column, row = inset, inset
        width = self.rect.width - inset * 2
        height = self.rect.height - inset * 2
        if width <= 0 or height <= 0:
            return
        self.box(column, row, width, 1, color)
        self.box(column, row + height - 1, width, 1, color)
        self.box(column, row, 1, height, color)
        self.box(column + width - 1, row, 1, height, color)

    def hline(self, column: int, row: int, width: int, color: Color) -> None:
        self.box(column, row, width, 1, color)

    def vline(self, column: int, row: int, height: int, color: Color) -> None:
        self.box(column, row, 1, height, color)

    def gradient_v(self, top: Color, bottom: Color) -> None:
        height = max(1, self.rect.height - 1)
        for row in range(self.rect.height):
            self.box(0, row, self.rect.width, 1, mix(top, bottom, row / height))

    def gradient_h(self, left: Color, right: Color) -> None:
        width = max(1, self.rect.width - 1)
        for column in range(self.rect.width):
            self.box(column, 0, 1, self.rect.height, mix(left, right, column / width))

    def noise(self, base: Color, colors: list[Color], density: float = 0.14,
              strength: tuple[float, float] = (0.12, 0.34)) -> None:
        """Sprinkle deterministic speckles for a worn, non-flat surface.

        Density and strength are deliberately low: heavy per-pixel randomness
        reads as television static once the texture is repeated over a body.
        """
        for row in range(self.rect.height):
            for column in range(self.rect.width):
                if self.rng.below(density):
                    self.px(column, row, mix(base, colors[self.rng.next() % len(colors)],
                                            strength[0] + (strength[1] - strength[0]) * self.rng.unit()))

    def blend_px(self, column: int, row: int, color: Color, amount: float) -> None:
        """Opaque blend: keeps alpha at 255 so ``entity_alphatest`` never clips it.

        Bedrock's alpha-test materials discard any texel below 50% alpha, so
        grime, blood and bevels must darken the base color instead of fading to
        transparency.
        """
        current = self.px_get(column, row)
        if current[3] == 0:
            return
        blended = mix(current[:3] + (255,), color[:3] + (255,), amount)
        self.px(column, row, (blended[0], blended[1], blended[2], 255))

    def streaks(self, color: Color, count: int, alpha_range=(60, 150)) -> None:
        """Vertical grime streaks that fade out through the base color."""
        for _ in range(count):
            column = self.rng.between(0, self.rect.width - 1)
            top = self.rng.between(0, max(0, self.rect.height - 2))
            length = self.rng.between(2, max(3, self.rect.height - top))
            strength = self.rng.between(alpha_range[0], alpha_range[1]) / 255.0
            for row in range(top, min(self.rect.height, top + length)):
                fade = 1.0 - (row - top) / max(1, length)
                self.blend_px(column, row, color, max(0.08, strength * fade))

    def speckle_shade(self, light: Color, dark: Color, density: float = 0.1) -> None:
        """Add per-pixel light/dark variation on top of existing art."""
        for row in range(self.rect.height):
            for column in range(self.rect.width):
                if not self.rng.below(density):
                    continue
                current = self.px_get(column, row)
                if current[3] == 0:
                    continue
                self.px(column, row, mix(current, light if self.rng.below(0.5) else dark, 0.16))

    def clear(self) -> None:
        """Make the whole patch fully transparent (see-through walls, overlays)."""
        transparent = (0, 0, 0, 0)
        for row in range(self.rect.height):
            for column in range(self.rect.width):
                self.px(column, row, transparent)

    def clear_px(self, column: int, row: int) -> None:
        self.px(column, row, (0, 0, 0, 0))

    def px_get(self, column: int, row: int) -> Color:
        x, y = self.rect.at(column, row)
        return self.image.get(x, y)

    def line(self, column: int, row: int, end_column: int, end_row: int, color: Color) -> None:
        """Bresenham line, kept for diagonal detail like cracks and straps."""
        delta_column = abs(end_column - column)
        delta_row = abs(end_row - row)
        step_column = 1 if column < end_column else -1
        step_row = 1 if row < end_row else -1
        error = delta_column - delta_row
        while True:
            self.px(column, row, color)
            if column == end_column and row == end_row:
                return
            doubled = error * 2
            if doubled > -delta_row:
                error -= delta_row
                column += step_column
            if doubled < delta_column:
                error += delta_column
                row += step_row

    def stencil_map(self, pattern: list[str], mapping: dict[str, Color | None],
                    column: int = 0, row: int = 0) -> None:
        """Paint an ASCII pattern through an explicit character -> color map.

        Characters mapped to ``None`` (typically ``.``) are left untouched so
        they stay transparent, which is how the spoked wheels get their gaps.
        """
        for row_index, line in enumerate(pattern):
            for column_index, char in enumerate(line):
                color = mapping.get(char)
                if color is not None:
                    self.px(column + column_index, row + row_index, color)

    def border_rows(self, top: Color, bottom: Color, thickness: int = 1) -> None:
        self.box(0, 0, self.rect.width, thickness, top)
        self.box(0, self.rect.height - thickness, self.rect.width, thickness, bottom)

    def bevel(self, light: Color, dark: Color, alpha: int = 150, inset: int = 0) -> None:
        """One-texel top/left highlight and bottom/right shadow for depth."""
        width, height = self.rect.width - inset * 2, self.rect.height - inset * 2
        if width <= 1 or height <= 1:
            return
        amount = max(0.05, min(1.0, alpha / 255.0))
        for column in range(inset, inset + width):
            self.blend_px(column, inset, light, amount)
            self.blend_px(column, inset + height - 1, dark, amount)
        for row in range(inset, inset + height):
            self.blend_px(inset, row, light, amount)
            self.blend_px(inset + width - 1, row, dark, amount)

    def opaque(self) -> None:
        """Force every texel to full alpha (safety net before export)."""
        for row in range(self.rect.height):
            for column in range(self.rect.width):
                current = self.px_get(column, row)
                if current[3] != 0 and current[3] != 255:
                    self.px(column, row, (current[0], current[1], current[2], 255))

    def rivets(self, color: Color, spacing: int = 3, inset: int = 2, highlight: Color | None = None) -> None:
        """Row of rivets along the top and bottom insets."""
        highlight = highlight or shade(color, 0.45)
        for column in range(inset, self.rect.width - inset, spacing):
            for row in (inset, self.rect.height - 1 - inset):
                if 0 <= row < self.rect.height:
                    self.px(column, row, color)
                    self.px(min(self.rect.width - 1, column + 1), row, highlight)

    def wear(self, color: Color, chips: int = 6, length: int = 2, amount: float = 0.45) -> None:
        """Scratch marks / chipped paint drawn as opaque blends."""
        for _ in range(chips):
            column = self.rng.between(0, max(0, self.rect.width - 2))
            row = self.rng.between(0, max(0, self.rect.height - 1))
            end_column = column + self.rng.between(1, length)
            end_row = row + self.rng.between(0, 1)
            delta_column = abs(end_column - column)
            delta_row = abs(end_row - row)
            step_column = 1 if column < end_column else -1
            step_row = 1 if row < end_row else -1
            error = delta_column - delta_row
            current_column, current_row = column, row
            while True:
                self.blend_px(current_column, current_row, color, amount)
                if current_column == end_column and current_row == end_row:
                    break
                doubled = error * 2
                if doubled > -delta_row:
                    error -= delta_row
                    current_column += step_column
                if doubled < delta_column:
                    error += delta_column
                    current_row += step_row

    def stencil(self, pattern: list[str], color: Color, column: int = 0, row: int = 0) -> None:
        """Paint an explicit ASCII pixel pattern (``#`` = opaque, ``.``/space = skip)."""
        for row_index, line in enumerate(pattern):
            for column_index, char in enumerate(line):
                if char in ".#xX*":
                    self.px(column + column_index, row + row_index, color)
                elif char.isalpha() and char.isupper():
                    # Named shades: L = light, D = dark, keep the same hue.
                    self.px(
                        column + column_index,
                        row + row_index,
                        shade(color, 0.35) if char == "L" else shade(color, -0.35),
                    )


def palette_from_rows(rows: list[tuple[str, float]]) -> list[Color]:
    """Helper for declarative palettes: [(hex, weight)] -> ordered color list."""
    return [rgba(value) for value, _ in rows]
