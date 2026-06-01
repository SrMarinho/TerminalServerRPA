"""Generate assets/icon.ico from the project's layers glyph.

Draws the same 'layers' mark used in the web sidebar (accent green on a dark
rounded square) at high resolution, then exports a multi-size Windows .ico for
PyInstaller. Run: python scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (8, 9, 10, 255)  # --bg-1
LINE = (42, 46, 54, 255)  # --line
ACCENT = (74, 222, 128, 255)  # --accent #4ade80

S = 1024  # supersample canvas
ICO_SIZES = [256, 128, 64, 48, 32, 16]


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _layers(draw: ImageDraw.ImageDraw) -> None:
    """Draw the 3-layer stack centered on the canvas (matches the 24x24 glyph)."""
    # Map the glyph's 24-unit space into a padded square on the SxS canvas.
    pad = S * 0.26
    span = S - 2 * pad

    def pt(x: float, y: float) -> tuple[float, float]:
        return (pad + x / 24 * span, pad + y / 24 * span)

    w = max(2, int(S * 0.052))
    # Top diamond (filled outline).
    diamond = [pt(12, 2), pt(2, 7), pt(12, 12), pt(22, 7)]
    draw.line([*diamond, diamond[0]], fill=ACCENT, width=w, joint="curve")
    # Middle + bottom chevrons.
    draw.line([pt(2, 12), pt(12, 17), pt(22, 12)], fill=ACCENT, width=w, joint="curve")
    draw.line([pt(2, 17), pt(12, 22), pt(22, 17)], fill=ACCENT, width=w, joint="curve")


def build() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = int(S * 0.22)
    draw.rounded_rectangle((0, 0, S - 1, S - 1), radius=radius, fill=BG)
    draw.rounded_rectangle((2, 2, S - 3, S - 3), radius=radius - 2, outline=LINE, width=max(2, S // 256))
    _layers(draw)
    # Clip to the rounded square so corners stay transparent.
    img.putalpha(_rounded_mask(S, radius))
    return img


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = build()
    ico_path = out_dir / "icon.ico"
    base.save(ico_path, sizes=[(s, s) for s in ICO_SIZES])
    png_path = out_dir / "icon.png"
    base.resize((512, 512), Image.LANCZOS).save(png_path)
    print(f"wrote {ico_path}")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
