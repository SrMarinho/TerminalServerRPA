"""Generate assets/icon.ico + icon.png — brutalist terminal mark.

Composition (top to bottom): a boxy terminal window with a title bar (3 dots),
faint CRT scanlines, a command prompt row ('>' + blinking cursor block), and a
3-node execution flow (two done, one pending). Brutalist crop-marks frame the
corners. Mint green on near-black. Run: python scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (8, 9, 10, 255)  # --bg-1
LINE = (42, 46, 54, 255)  # --line
ACCENT = (74, 222, 128, 255)  # --accent #4ade80
DIM = (34, 197, 94, 255)  # --accent-dim
SCAN = (74, 222, 128, 28)  # faint scanline

S = 1024
ICO_SIZES = [256, 128, 64, 48, 32, 16]


def _mask(radius: int) -> Image.Image:
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, S - 1, S - 1), radius=radius, fill=255)
    return m


def _crop_marks(d: ImageDraw.ImageDraw) -> None:
    """Brutalist L-shaped registration marks just inside the badge corners."""
    w = int(S * 0.022)
    arm = S * 0.07
    off = S * 0.1
    for cx, cy, sx, sy in (
        (off, off, 1, 1),
        (S - off, off, -1, 1),
        (off, S - off, 1, -1),
        (S - off, S - off, -1, -1),
    ):
        d.line((cx, cy, cx + sx * arm, cy), fill=DIM, width=w)
        d.line((cx, cy, cx, cy + sy * arm), fill=DIM, width=w)


def _window(d: ImageDraw.ImageDraw) -> tuple[float, float, float, float]:
    w = int(S * 0.04)
    x0, y0, x1, y1 = S * 0.2, S * 0.2, S * 0.8, S * 0.8
    d.rounded_rectangle((x0, y0, x1, y1), radius=int(S * 0.035), outline=ACCENT, width=int(w * 1.2))
    # Title bar separator + 3 dots.
    by = y0 + (y1 - y0) * 0.18
    d.line((x0, by, x1, by), fill=ACCENT, width=w)
    dot = int(S * 0.015)
    for i in range(3):
        cx = x0 + S * 0.045 + i * S * 0.045
        cyd = (y0 + by) / 2
        d.ellipse((cx - dot, cyd - dot, cx + dot, cyd + dot), fill=ACCENT)
    return x0, by, x1, y1


def _scanlines(x0: float, y0: float, x1: float, y1: float) -> Image.Image:
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    step = S * 0.028
    y = y0 + step
    while y < y1 - step * 0.5:
        ld.line((x0 + S * 0.02, y, x1 - S * 0.02, y), fill=SCAN, width=max(1, int(S * 0.004)))
        y += step
    return layer


def _prompt(d: ImageDraw.ImageDraw, x0: float, y: float) -> None:
    """A '>' chevron followed by a filled cursor block (command line)."""
    w = int(S * 0.032)
    cx = x0 + S * 0.085
    h = S * 0.05
    d.line((cx, y - h, cx + S * 0.05, y, cx, y + h), fill=ACCENT, width=w, joint="curve")
    bx = cx + S * 0.1
    bw, bh = S * 0.07, S * 0.05
    d.rectangle((bx, y - bh, bx + bw, y + bh), fill=ACCENT)


def _flow(d: ImageDraw.ImageDraw, x0: float, x1: float, y: float) -> None:
    rad = S * 0.04
    xs = [x0 + S * 0.13, (x0 + x1) / 2, x1 - S * 0.13]
    w = int(S * 0.032)
    for a, b in ((xs[0], xs[1]), (xs[1], xs[2])):
        d.line((a + rad, y, b - rad, y), fill=DIM, width=w)
    for i, x in enumerate(xs):
        box = (x - rad, y - rad, x + rad, y + rad)
        if i < 2:
            d.ellipse(box, fill=ACCENT)
        else:
            d.ellipse(box, outline=ACCENT, width=int(rad * 0.34))


def build() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(S * 0.2)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=radius, fill=BG)
    d.rounded_rectangle((3, 3, S - 4, S - 4), radius=radius - 3, outline=LINE, width=max(2, S // 256))

    _crop_marks(d)
    x0, by, x1, y1 = _window(d)
    img.alpha_composite(_scanlines(x0, by, x1, y1))
    d = ImageDraw.Draw(img)  # redraw handle after composite
    content_top, content_bot = by, y1
    _prompt(d, x0, content_top + (content_bot - content_top) * 0.34)
    _flow(d, x0, x1, content_top + (content_bot - content_top) * 0.72)

    img.putalpha(_mask(radius))
    return img


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = build()
    base.save(out_dir / "icon.ico", sizes=[(s, s) for s in ICO_SIZES])
    base.resize((512, 512), Image.LANCZOS).save(out_dir / "icon.png")
    print(f"wrote {out_dir / 'icon.ico'} and icon.png")


if __name__ == "__main__":
    main()
