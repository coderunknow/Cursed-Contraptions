"""Shared pixel-art painters for the Cursed Contraptions device textures.

Each helper returns a callable ``(Painter) -> None`` so device definitions stay
declarative. Art is authored at 1 texel = 1 model pixel, which keeps every
device on the standard Minecraft density and avoids mixels.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

import math

from canvas import Color, Painter, mix, rgba, shade, with_alpha

# --------------------------------------------------------------------------- #
# palettes
# --------------------------------------------------------------------------- #
STEEL_DARK = rgba("#3a424e")
STEEL_MID = rgba("#5f6874")
STEEL = rgba("#7b8794")
STEEL_LIGHT = rgba("#9aa5b4")
STEEL_HIGHLIGHT = rgba("#ccd4de")
RUST = rgba("#7b4327")
GRIME = rgba("#2f2a24")
BLOOD = rgba("#5c1a19")
IRON_BLACK = rgba("#262b33")

WOOD_DARK = rgba("#573b26")
WOOD_MID = rgba("#6c4a2b")
WOOD = rgba("#946e42")
WOOD_LIGHT = rgba("#a07d4e")
ROPE = rgba("#b4945a")
ROPE_DARK = rgba("#7d6337")
LEATHER = rgba("#59391f")

OBSIDIAN_DARK = rgba("#0d0a16")
OBSIDIAN = rgba("#241c3a")
OBSIDIAN_LIGHT = rgba("#332547")
OBSIDIAN_FACET = rgba("#453161")
NETHERITE = rgba("#2b2725")
NETHERITE_LIGHT = rgba("#4d4642")
GOLD = rgba("#c9a227")
GOLD_LIGHT = rgba("#f0d369")
SOUL = rgba("#6f3fc4")
SOUL_LIGHT = rgba("#b98bff")
SOUL_PALE = rgba("#e0ccff")
CRYSTAL = rgba("#c15cf0")
CRYSTAL_LIGHT = rgba("#f0b6ff")
CRYSTAL_DARK = rgba("#6a1ea8")
BONE = rgba("#d6cfb6")
BONE_DARK = rgba("#9d9377")


# --------------------------------------------------------------------------- #
# generic surfaces
# --------------------------------------------------------------------------- #
def steel_plate(
    base: Color = STEEL,
    *,
    light: Color = STEEL_LIGHT,
    dark: Color = STEEL_DARK,
    rivets: bool = True,
    rivet_color: Color = STEEL_HIGHLIGHT,
    bands: int = 0,
    band_color: Color | None = None,
    grime: float = 0.1,
    scratches: int = 3,
    rust: float = 0.0,
):
    """A riveted iron plate: gradient, bevel, rivet rows, optional cross bands."""

    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.10), shade(base, -0.22))
        painter.noise(base, [shade(base, 0.10), shade(base, -0.12)], density=0.14)
        if bands:
            band = band_color or shade(dark, -0.1)
            for index in range(bands):
                row = int((index + 1) * painter.rect.height / (bands + 1))
                painter.box(0, row, painter.rect.width, 1, band)
                painter.box(0, row + 1, painter.rect.width, 1, shade(band, 0.25))
        if rivets and painter.rect.width >= 3 and painter.rect.height >= 5:
            painter.rivets(rivet_color, spacing=max(3, painter.rect.width // 3), inset=1)
        if scratches:
            painter.wear(light, chips=scratches, length=2, amount=0.4)
        if rust:
            painter.streaks(RUST, count=max(1, int(painter.rect.width * rust)), alpha_range=(30, 70))
        if grime:
            painter.streaks(GRIME, count=max(1, int(painter.rect.width * grime)), alpha_range=(20, 46))
        painter.bevel(light, dark, alpha=120)

    return paint


def steel_face(
    base: Color = STEEL,
    *,
    light: Color = STEEL_LIGHT,
    dark: Color = STEEL_DARK,
    eye_glow: Color | None = None,
):
    """The Iron Maiden's carved, screaming inner plate."""

    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.06), shade(base, -0.26))
        painter.noise(base, [shade(base, 0.09), shade(base, -0.12)], density=0.14)
        width, height = painter.rect.width, painter.rect.height
        if width < 4 or height < 6:
            painter.bevel(light, dark, alpha=110)
            return
        # Brow ridge and nose.
        painter.box(0, max(1, height // 4), width, 1, shade(dark, -0.15))
        painter.box(width // 2 - 1, height // 3, 2, max(2, height // 3), shade(base, 0.18))
        # Eye sockets: hollow, with an optional ember glow.
        eye_row = max(2, height // 4 + 1)
        socket_width = max(1, width // 5)
        for offset in (max(1, width // 8), width - max(1, width // 8) - socket_width):
            painter.box(offset, eye_row, socket_width, max(2, height // 8), shade(dark, -0.35))
            painter.box(offset, eye_row + max(2, height // 8) - 1, socket_width, 1, shade(base, 0.3))
            if eye_glow:
                painter.box(offset + 1, eye_row + 1, max(1, socket_width - 2), 1, eye_glow)
        # Mouth grille.
        mouth_row = height - max(2, height // 4)
        painter.box(max(1, width // 5), mouth_row, max(2, width - 2 * max(1, width // 5)), 1, shade(dark, -0.3))
        for column in range(max(1, width // 5), width - max(1, width // 5), 2):
            painter.box(column, mouth_row, 1, max(2, height // 5), shade(dark, -0.2))
        # Cheek rivets.
        painter.rivets(shade(light, 0.2), spacing=3, inset=2)
        painter.wear(shade(light, 0.35), chips=3, length=2)
        painter.streaks(BLOOD, count=2, alpha_range=(40, 90))
        painter.bevel(light, dark, alpha=130)

    return paint


def planks(
    base: Color = WOOD,
    *,
    light: Color = WOOD_LIGHT,
    dark: Color = WOOD_DARK,
    count: int = 3,
    vertical: bool = False,
    knots: int = 2,
):
    """Wooden boards with seams, grain and knots."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        painter.noise(base, [shade(base, 0.09), shade(base, -0.11)], density=0.15)
        span = width if vertical else height
        seam_count = max(1, min(count, span - 1))
        for index in range(1, seam_count + 1):
            offset = int(index * span / (seam_count + 1))
            if vertical:
                painter.vline(offset, 0, height, shade(dark, -0.25))
                painter.vline(min(width - 1, offset + 1), 0, height, shade(base, 0.14))
            else:
                painter.hline(0, offset, width, shade(dark, -0.25))
                painter.hline(0, min(height - 1, offset + 1), width, shade(base, 0.14))
        for _ in range(knots):
            column = painter.rng.between(1, max(1, width - 2))
            row = painter.rng.between(1, max(1, height - 2))
            painter.px(column, row, shade(dark, -0.2))
            painter.px(min(width - 1, column + 1), row, shade(light, 0.1))
        for _ in range(max(1, (width * height) // 14)):
            if vertical:
                column = painter.rng.between(0, max(0, width - 1))
                top = painter.rng.between(0, max(0, height - 3))
                painter.vline(column, top, painter.rng.between(2, 4), shade(base, -0.12))
            else:
                row = painter.rng.between(0, max(0, height - 1))
                left = painter.rng.between(0, max(0, width - 4))
                painter.hline(left, row, painter.rng.between(2, 5), shade(base, -0.12))
        painter.bevel(light, dark, alpha=90)

    return paint


def iron_bar(base: Color = STEEL, *, light: Color = STEEL_HIGHLIGHT, dark: Color = IRON_BLACK):
    """Vertical wrought-iron bar with a cylindrical highlight."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.gradient_h(shade(base, -0.18), shade(base, -0.3))
        highlight_column = width // 2
        painter.vline(highlight_column, 0, height, mix(base, light, 0.45))
        if width > 2:
            painter.vline(highlight_column - 1, 0, height, mix(base, light, 0.16))
        painter.box(0, 0, 1, height, shade(dark, -0.1))
        painter.box(width - 1, 0, 1, height, shade(dark, -0.1))
        for _ in range(max(1, height // 6)):
            row = painter.rng.between(0, max(0, height - 1))
            for column in range(width):
                painter.blend_px(column, row, RUST, painter.rng.between(60, 150) / 255.0)
        painter.bevel(light, dark, alpha=70)

    return paint


def chain(base: Color = STEEL, *, dark: Color = IRON_BLACK, light: Color = STEEL_LIGHT):
    """Interlocking chain links, drawn column-wise."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(shade(base, -0.25))
        link_height = max(2, height // 4)
        for index in range(0, height, link_height):
            wide = (index // link_height) % 2 == 0
            left = 0 if wide or width < 3 else 1
            right = width if wide or width < 3 else width - 1
            for row in range(index, min(height, index + link_height)):
                painter.box(left, row, max(1, right - left), 1, mix(base, dark, 0.35 if row in (index, index + link_height - 1) else 0.1))
            painter.box(left, index, max(1, right - left), 1, mix(light, base, 0.55))
            painter.box(left, min(height - 1, index + link_height - 1), max(1, right - left), 1, shade(dark, 0.05))
        painter.noise(base, [shade(base, 0.10), shade(base, -0.12)], density=0.12)

    return paint


def rope(base: Color = ROPE, *, dark: Color = ROPE_DARK):
    """Twisted rope, hatched diagonally."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        for row in range(height):
            for column in range(width):
                if (column + row) % 3 == 0:
                    painter.px(column, row, shade(dark, -0.05))
                elif (column + row) % 3 == 1:
                    painter.px(column, row, shade(base, 0.14))
        for row in (0, height - 1):
            painter.hline(0, row, width, shade(dark, -0.25))
        painter.noise(base, [shade(base, 0.09)], density=0.1)

    return paint


def leather(base: Color = LEATHER):
    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.12), shade(base, -0.2))
        painter.noise(base, [shade(base, 0.11), shade(base, -0.11)], density=0.16)
        painter.bevel(shade(base, 0.3), shade(base, -0.4), alpha=130)

    return paint


def obsidian(base: Color = OBSIDIAN, *, facet: Color = OBSIDIAN_FACET, dark: Color = OBSIDIAN_DARK):
    """Volcanic glass: near-black with sharp purple facets."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        painter.noise(base, [shade(base, 0.22), dark], density=0.16)
        for _ in range(max(1, (width * height) // 10)):
            column = painter.rng.between(0, max(0, width - 3))
            row = painter.rng.between(0, max(0, height - 3))
            length = painter.rng.between(2, 5)
            painter.line(column, row, column + length, row + painter.rng.between(-1, 2), facet)
            painter.line(column + 1, row + 1, column + length, row + 1 + painter.rng.between(-1, 2),
                         mix(facet, dark, 0.45))
        painter.bevel(facet, dark, alpha=150)

    return paint


def netherite_plate(base: Color = NETHERITE, *, light: Color = NETHERITE_LIGHT):
    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.16), shade(base, -0.24))
        painter.noise(base, [shade(base, 0.18), shade(base, -0.18)], density=0.15)
        painter.rivets(light, spacing=4, inset=1)
        painter.wear(light, chips=4, length=2, amount=0.42)
        painter.bevel(light, shade(base, -0.5), alpha=140)

    return paint


def gold_trim(base: Color = GOLD, *, light: Color = GOLD_LIGHT):
    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.2), shade(base, -0.25))
        painter.hline(0, 0, painter.rect.width, light)
        painter.bevel(light, shade(base, -0.45), alpha=160)
        painter.noise(base, [light, shade(base, -0.25)], density=0.1)

    return paint


def crystal(base: Color = CRYSTAL, *, light: Color = CRYSTAL_LIGHT, dark: Color = CRYSTAL_DARK):
    """Faceted soul crystal with a bright core."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(dark)
        painter.gradient_v(mix(base, light, 0.35), dark)
        edge = max(1, width // 4)
        painter.box(edge, 0, max(1, width - 2 * edge), height, mix(base, light, 0.2))
        painter.box(width // 2, 0, 1, height, light)
        for row in range(height):
            if (row + width) % 3 == 0:
                painter.hline(0, row, width, mix(base, dark, 0.35))
        painter.bevel(light, dark, alpha=180)

    return paint


def soul_glow(base: Color = SOUL, *, light: Color = SOUL_LIGHT, pale: Color = SOUL_PALE):
    """Emissive-looking soul fire; bright core with a violet halo."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        for row in range(height):
            ratio = row / max(1, height - 1)
            painter.hline(0, row, width, mix(pale, base, ratio * 0.8))
        painter.box(width // 2, 0, 1, height, pale)
        painter.noise(base, [light, pale], density=0.22)
        painter.bevel(pale, shade(base, -0.4), alpha=150)

    return paint


def bone(base: Color = BONE, *, dark: Color = BONE_DARK):
    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.1), shade(base, -0.12))
        painter.noise(base, [shade(base, 0.12), dark], density=0.14)
        painter.wear(dark, chips=3, length=2)
        painter.bevel(shade(base, 0.3), dark, alpha=120)

    return paint


def runes(pattern: list[str], color: Color, *, background: Color | None = None, glow: Color | None = None):
    """Paint an explicit ASCII glyph (``#`` opaque, ``L`` light, ``D`` dark)."""

    def paint(painter: Painter) -> None:
        painter.fill(background if background is not None else shade(color, -0.78))
        if glow is not None:
            for row in range(painter.rect.height):
                for column in range(painter.rect.width):
                    if painter.rng.below(0.2):
                        painter.blend_px(column, row, glow, 0.25)
        offset_x = max(0, (painter.rect.width - len(pattern[0])) // 2)
        offset_y = max(0, (painter.rect.height - len(pattern)) // 2)
        painter.stencil(pattern, color, offset_x, offset_y)

    return paint


def straps(base: Color = LEATHER, *, buckle: Color = GOLD, vertical: bool = False):
    def paint(painter: Painter) -> None:
        painter.fill(base)
        painter.noise(base, [shade(base, 0.12), shade(base, -0.12)], density=0.15)
        if vertical:
            painter.vline(painter.rect.width // 2, 0, painter.rect.height, buckle)
            painter.vline(painter.rect.width // 2 + 1, 0, painter.rect.height, shade(buckle, -0.35))
        else:
            painter.hline(0, painter.rect.height // 2, painter.rect.width, buckle)
            painter.hline(0, painter.rect.height // 2 + 1, painter.rect.width, shade(buckle, -0.35))
        painter.bevel(shade(base, 0.3), shade(base, -0.4), alpha=120)

    return paint


def spike(base: Color = STEEL, *, light: Color = STEEL_HIGHLIGHT, dark: Color = IRON_BLACK):
    """Tapered spike: bright tip, dark base."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(shade(base, -0.1))
        for row in range(height):
            ratio = row / max(1, height - 1)
            inset = int(ratio * max(0, width // 2))
            painter.hline(inset, row, max(1, width - inset * 2), mix(dark, light, 1 - ratio * 0.85))
        painter.bevel(light, dark, alpha=90)

    return paint


def cloth(base: Color, *, trim: Color = GOLD, vertical: bool = True, emblem: list[str] | None = None):
    """Tattered banner cloth with a trim and optional emblem."""

    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.14), shade(base, -0.24))
        painter.noise(base, [shade(base, 0.12), shade(base, -0.13)], density=0.15)
        if vertical:
            painter.vline(0, 0, painter.rect.height, trim)
            painter.vline(painter.rect.width - 1, 0, painter.rect.height, shade(trim, -0.3))
        else:
            painter.hline(0, 0, painter.rect.width, trim)
            painter.hline(0, painter.rect.height - 1, painter.rect.width, shade(trim, -0.3))
        if emblem:
            offset_x = max(0, (painter.rect.width - len(emblem[0])) // 2)
            offset_y = max(0, (painter.rect.height - len(emblem)) // 2)
            painter.stencil(emblem, shade(base, -0.45), offset_x, offset_y)
        painter.bevel(shade(base, 0.3), shade(base, -0.4), alpha=100)

    return paint


def flat(color: Color, *, bevel: bool = False, noise: bool = False):
    """A plain color patch, used for hidden faces to save atlas space."""

    def paint(painter: Painter) -> None:
        painter.fill(color)
        if noise:
            painter.noise(color, [shade(color, 0.1), shade(color, -0.1)], density=0.14)
        if bevel:
            painter.bevel(shade(color, 0.25), shade(color, -0.3), alpha=110)

    return paint


def rusted_socket(base: Color = STEEL_DARK, *, glow: Color | None = None):
    def paint(painter: Painter) -> None:
        painter.gradient_v(shade(base, 0.14), shade(base, -0.28))
        painter.noise(base, [RUST, shade(base, 0.15)], density=0.2)
        if glow:
            painter.box(
                painter.rect.width // 3, painter.rect.height // 3,
                max(1, painter.rect.width // 3), max(1, painter.rect.height // 3),
                glow,
            )
        painter.bevel(shade(base, 0.3), shade(base, -0.4), alpha=130)

    return paint


# --------------------------------------------------------------------------- #
# v0.1.4 structure painters (barred walls, cracks, reliefs, mechanisms)
# --------------------------------------------------------------------------- #
def bar_grid(
    base: Color = STEEL,
    *,
    light: Color = STEEL_HIGHLIGHT,
    dark: Color = IRON_BLACK,
    rails: int = 3,
    spacing: int = 4,
    rust: float = 0.3,
):
    """A transparent wall crossed by vertical bars and horizontal rails.

    The gaps keep alpha 0 on purpose: ``entity_alphatest`` discards them, which
    is what lets a captive be seen through the cage instead of behind a painted
    picture of bars.
    """

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.clear()
        for column in range(1, width, spacing):
            painter.box(column, 0, 1, height, shade(base, -0.18))
            painter.vline(min(width - 1, column), 0, height, shade(base, 0.05))
            painter.vline(min(width - 1, column), 0, height, mix(base, light, 0.35))
        for index in range(1, rails + 1):
            row = int(index * height / (rails + 1))
            painter.box(0, row, width, 1, shade(dark, -0.1))
            painter.box(0, row + 1, width, 1, mix(base, light, 0.2))
        for _ in range(max(1, int(width * rust))):
            column = painter.rng.between(0, max(0, width - 1))
            row = painter.rng.between(0, max(0, height - 3))
            for offset in range(painter.rng.between(2, 5)):
                painter.blend_px(column, min(height - 1, row + offset), RUST, painter.rng.between(60, 140) / 255.0)

    return paint


def cracks(seed: int = 0, *, count: int = 5, color: Color = IRON_BLACK, glow: Color | None = None):
    """Transparent crack overlay: hairline fractures and chipped edges."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.clear()
        for index in range(count):
            column = painter.rng.between(0, max(0, width - 1))
            row = painter.rng.between(0, max(0, height - 1))
            length = painter.rng.between(max(2, height // 6), max(3, height // 2))
            for step in range(length):
                painter.px(column, min(height - 1, row + step), color)
                if painter.rng.below(0.45):
                    column += painter.rng.between(-1, 1)
                if glow and painter.rng.below(0.2):
                    painter.px(min(width - 1, max(0, column + 1)), min(height - 1, row + step), glow)
            if index % 2 == 0:
                painter.px(min(width - 1, column), min(height - 1, row + length), color)
        for _ in range(max(1, (width * height) // 24)):
            column = painter.rng.between(0, max(0, width - 1))
            row = painter.rng.between(0, max(0, height - 1))
            painter.px(column, row, color)

    return paint


def skull(base: Color = BONE, *, dark: Color = BONE_DARK, socket: Color = IRON_BLACK):
    """A small carved skull relief, size-relative so it survives rescaling."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.gradient_v(shade(base, 0.14), shade(base, -0.18))
        painter.noise(base, [shade(base, 0.16), dark], density=0.12)
        if width < 5 or height < 6:
            painter.bevel(shade(base, 0.3), dark, alpha=120)
            return
        eye_height = max(2, height // 5)
        eye_width = max(1, width // 4)
        eye_row = max(1, height // 3)
        painter.box(max(0, width // 6), eye_row, eye_width, eye_height, socket)
        painter.box(min(width - eye_width, width - width // 6 - eye_width), eye_row, eye_width, eye_height, socket)
        painter.box(max(1, width // 3), eye_row + eye_height, max(1, width // 3), max(1, height // 6), shade(dark, -0.25))
        mouth_row = eye_row + eye_height + max(2, height // 5)
        for column in range(max(1, width // 4), width - max(1, width // 4), 2):
            painter.box(column, mouth_row, 1, max(1, height // 8), shade(socket, 0.25))
        painter.bevel(shade(base, 0.35), dark, alpha=140)

    return paint


def rune_band(base: Color = OBSIDIAN_LIGHT, *, glow: Color = SOUL_LIGHT, dark: Color = OBSIDIAN_DARK):
    """A band of carved glyphs that catch the light."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        painter.noise(base, [shade(base, 0.18), dark], density=0.16)
        for column in range(2, width - 2, 3):
            glyph = painter.rng.between(0, 3)
            row = max(1, height // 2 - 2)
            if glyph == 0:
                painter.vline(column, row, 3, glow)
                painter.px(column + 1, row + 1, glow)
            elif glyph == 1:
                painter.box(column, row, 2, 1, glow)
                painter.px(column, row + 2, glow)
            elif glyph == 2:
                painter.px(column, row, glow)
                painter.px(column, row + 2, glow)
                painter.px(column + 1, row + 1, glow)
            else:
                painter.vline(column, row, 2, glow)
            if painter.rng.below(0.4):
                painter.px(min(width - 1, column + 1), row + 3, shade(glow, -0.35))
        painter.bevel(shade(base, 0.3), dark, alpha=140)

    return paint


def spoked_wheel(base: Color = STEEL, *, light: Color = STEEL_HIGHLIGHT, dark: Color = IRON_BLACK, spokes: int = 6):
    """A wheel face for cranks and winches: rim, hub and open spokes."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.clear()
        size = min(width, height)
        radius = max(1.5, (size - 1) / 2)
        rim = max(1.0, size / 7)
        hub = max(1.0, size / 5)
        center_x, center_y = (width - 1) / 2, (height - 1) / 2
        painter.clear()
        spoke_count = max(3, spokes)
        for row in range(height):
            for column in range(width):
                # A true circle; sub-texel bias keeps the 1-texel-odd wheel round.
                distance = math.hypot(column - center_x, row - center_y) + 0.15
                if distance > radius:
                    continue
                if distance >= radius - rim or distance <= hub:
                    painter.px(column, row, mix(base, light, 0.2) if distance > hub else mix(dark, base, 0.5))
        for index in range(spoke_count):
            radians = math.radians(index * (360.0 / spoke_count))
            for step in range(max(1, int(radius))):
                column = int(round(center_x + math.cos(radians) * step))
                row = int(round(center_y + math.sin(radians) * step))
                if 0 <= column < width and 0 <= row < height:
                    painter.px(column, row, mix(base, dark, 0.25))
        painter.bevel(light, dark, alpha=90)

    return paint


def soul_lantern(base: Color = IRON_BLACK, *, glass: Color = SOUL, light: Color = SOUL_PALE, frame: Color = STEEL_DARK):
    """A squat iron lantern with a soul flame inside."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(frame)
        inner_width = max(1, width - 2)
        inner_height = max(1, height - 3)
        painter.box(1, 1, inner_width, inner_height, shade(base, -0.1))
        painter.box(1, 1, inner_width, inner_height, glass)
        painter.box(1, 2, inner_width, max(1, inner_height - 2), mix(glass, light, 0.35))
        painter.vline(max(1, width // 2), 1, inner_height, light)
        painter.box(0, 0, width, 1, frame)
        painter.box(0, height - 1, width, 1, frame)
        painter.bevel(shade(frame, 0.35), IRON_BLACK, alpha=130)

    return paint


def wood_frame(base: Color = WOOD_MID, *, light: Color = WOOD_LIGHT, dark: Color = WOOD_DARK, braces: int = 2):
    """Timber frame with corner braces, for the rack and the stocks."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        painter.noise(base, [shade(base, 0.12), shade(base, -0.14)], density=0.15)
        thickness = max(2, min(width, height) // 5)
        painter.box(0, 0, width, thickness, shade(light, -0.05))
        painter.box(0, height - thickness, width, thickness, dark)
        painter.box(0, 0, thickness, height, light)
        painter.box(width - thickness, 0, thickness, height, dark)
        for index in range(braces):
            row = int((index + 1) * height / (braces + 1))
            painter.box(thickness, row, max(1, width - thickness * 2), thickness, mix(base, dark, 0.45))
            painter.box(thickness, row + thickness, max(1, width - thickness * 2), 1, shade(light, 0.05))
        painter.rivets(shade(light, 0.25), spacing=max(3, width // 4), inset=max(1, thickness - 1))
        painter.bevel(light, dark, alpha=110)

    return paint


def steel_panel(
    base: Color = STEEL,
    *,
    light: Color = STEEL_HIGHLIGHT,
    dark: Color = STEEL_DARK,
    recess: Color = IRON_BLACK,
    seams: int = 3,
    bands: int = 2,
    rivets: bool = True,
    grime: float = 0.25,
    rust: float = 0.35,
    scratches: int = 4,
):
    """A single bolt-on armour panel with real value structure.

    v0.1.3 painted every metal face with the same two-stop gradient, which
    flattened the whole device into one grey mass in game. This painter builds
    a readable hierarchy instead: dark outer seam, bright top bevel, recessed
    waist band, riveted frame and rust running out of the joints.
    """

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.gradient_v(shade(base, 0.18), shade(base, -0.34))
        painter.noise(base, [shade(base, 0.12), shade(base, -0.16)], density=0.13)
        # Outer seam and top highlight give the panel thickness.
        painter.outline(shade(dark, -0.25), 0)
        painter.box(1, 1, max(1, width - 2), 1, shade(light, -0.05))
        painter.box(1, 0, max(1, width - 2), 1, shade(base, 0.25))
        # Horizontal armour bands with a shadowed groove beneath each.
        for index in range(1, bands + 1):
            row = int(index * height / (bands + 1))
            painter.box(0, row, width, 1, shade(dark, 0.18))
            painter.box(0, min(height - 1, row + 1), width, 1, shade(recess, 0.15))
        # Vertical plate seams.
        for index in range(1, seams):
            column = int(index * width / seams)
            painter.vline(column, 1, max(1, height - 2), shade(recess, 0.2))
            painter.vline(min(width - 1, column + 1), 1, max(1, height - 2), shade(light, 0.05))
        if rivets and width >= 4 and height >= 4:
            painter.rivets(mix(light, base, 0.25), spacing=max(4, width // 4), inset=2,
                           highlight=shade(light, 0.3))
        for _ in range(max(1, int(width * rust))):
            column = painter.rng.between(0, max(0, width - 1))
            row = painter.rng.between(0, max(1, height - 2))
            for step in range(painter.rng.between(2, 6)):
                painter.blend_px(column, min(height - 1, row + step), RUST, painter.rng.between(50, 130) / 255.0)
        painter.streaks(GRIME, count=max(1, int(width * grime)), alpha_range=(30, 80))
        if scratches:
            painter.wear(shade(light, 0.15), chips=scratches, length=2, amount=0.32)
        painter.bevel(light, shade(dark, -0.2), alpha=150)

    return paint


def stone_brick(base: Color = rgba("#4a4741"), *, light: Color = rgba("#5d5a53"), dark: Color = rgba("#26241f")):
    """Grimy plinth masonry for the base of the heavier contraptions."""

    def paint(painter: Painter) -> None:
        width, height = painter.rect.width, painter.rect.height
        painter.fill(base)
        painter.noise(base, [shade(base, 0.16), shade(base, -0.2)], density=0.18)
        row_height = max(3, height // 3)
        for index, row in enumerate(range(0, height, row_height)):
            offset = 0 if index % 2 == 0 else max(2, width // 4)
            painter.box(0, row, width, 1, shade(dark, 0.1))
            for column in range(offset, width, max(3, width // 3)):
                painter.vline(column, row, row_height, shade(dark, 0.05))
                painter.vline(min(width - 1, column + 1), row + 1, max(1, row_height - 1), shade(light, 0.05))
        painter.streaks(dark, count=max(2, width // 4), alpha_range=(40, 90))
        painter.bevel(light, dark, alpha=130)

    return paint
