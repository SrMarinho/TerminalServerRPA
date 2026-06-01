"""Generate assets/icon.ico + icon.png from the project's 'flow' mark.

The mark: a terminal screen framing a 3-node step flow (the task state
machine that drives each RPA execution). Accent green on a dark rounded
square. Run: python scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (8, 9, 10, 255)  # --bg-1
LINE = (42, 46, 54, 255)  # --line
ACCENT = (74, 222, 128, 255)  # --accent #4ade80
DIM = (34, 197, 94, 255)  # --accent-dim

S = 1024
ICO_SIZES = [256, 128, 64, 48, 32, 16]


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _flow(d: ImageDraw.ImageDraw) -> None:
    """Terminal screen + 3 connected nodes (the execution step flow)."""
    w = int(S * 0.045)
    x0, y0, x1, y1 = S * 0.18, S * 0.24, S * 0.82, S * 0.76
    d.rounded_rectangle((x0, y0, x1, y1), radius=int(S * 0.06), outline=ACCENT, width=int(w * 1.15))
    cy = (y0 + y1) / 2
    xs = [x0 + (x1 - x0) * f for f in (0.24, 0.5, 0.76)]
    rad = S * 0.052
    # Connectors first (sit behind nodes).
    for a, b in ((xs[0], xs[1]), (xs[1], xs[2])):
        d.line((a + rad, cy, b - rad, cy), fill=DIM, width=int(w * 0.95))
    # Nodes: first two done (filled), last pending (outline).
    for i, x in enumerate(xs):
        box = (x - rad, cy - rad, x + rad, cy + rad)
        if i < 2:
            d.ellipse(box, fill=ACCENT)
        else:
            d.ellipse(box, outline=ACCENT, width=int(rad * 0.34))


def build() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(S * 0.22)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=radius, fill=BG)
    d.rounded_rectangle((3, 3, S - 4, S - 4), radius=radius - 3, outline=LINE, width=max(2, S // 256))
    _flow(d)
    img.putalpha(_rounded_mask(S, radius))
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
