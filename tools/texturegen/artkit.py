"""Shared pixel-art painters for the Cursed Contraptions device textures.

Each helper returns a callable ``(Painter) -> None`` so device definitions stay
declarative. Art is authored at 1 texel = 1 model pixel, which keeps every
device on the standard Minecraft density and avoids mixels.

Dev-only tool: nothing in this file ships inside the .mcaddon.
"""

from __future__ import annotations

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
