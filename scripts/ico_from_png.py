"""Build assets/icon.ico + icon.png from a downloaded PNG (e.g. from Recraft).

Squares the source on a transparent canvas (no distortion), then exports a
multi-size Windows .ico and a 512px PNG.

Usage:
    python scripts/ico_from_png.py path/to/recraft.png
    python scripts/ico_from_png.py path/to/recraft.png --pad 0.06
"""

import argparse
from pathlib import Path

from PIL import Image

ICO_SIZES = [256, 128, 64, 48, 32, 16]


def square(img: Image.Image, pad: float) -> Image.Image:
    """Center the image on a transparent square canvas with optional padding."""
    img = img.convert("RGBA")
    side = max(img.size)
    canvas_side = int(side * (1 + pad * 2))
    canvas = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    offset = ((canvas_side - img.width) // 2, (canvas_side - img.height) // 2)
    canvas.paste(img, offset, img)
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path, help="source PNG downloaded from Recraft")
    ap.add_argument("--pad", type=float, default=0.0, help="extra transparent padding ratio (e.g. 0.06)")
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"source not found: {args.source}")

    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    base = square(Image.open(args.source), args.pad)
    base.save(out_dir / "icon.ico", sizes=[(s, s) for s in ICO_SIZES])
    base.resize((512, 512), Image.LANCZOS).save(out_dir / "icon.png")
    print(f"wrote {out_dir / 'icon.ico'} and icon.png from {args.source.name}")
    print("Tip: also drop the SVG (if you vectorized it) into assets/favicon.svg")


if __name__ == "__main__":
    main()
