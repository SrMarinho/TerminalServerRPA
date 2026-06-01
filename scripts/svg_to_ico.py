"""Rasterize assets/favicon.svg via Playwright and export icon.ico + icon.png.

Usage: python scripts/svg_to_ico.py [--size 1024]
"""

import argparse
import asyncio
import base64
from pathlib import Path

from PIL import Image

ICO_SIZES = [256, 128, 64, 48, 32, 16]
ASSETS = Path(__file__).resolve().parent.parent / "assets"


async def rasterize(svg_path: Path, size: int) -> Image.Image:
    from playwright.async_api import async_playwright

    svg_b64 = base64.b64encode(svg_path.read_bytes()).decode()
    html = f"""<!DOCTYPE html><html><head><style>
    * {{ margin:0;padding:0;box-sizing:border-box }}
    body {{ width:{size}px;height:{size}px;overflow:hidden;background:transparent }}
    img {{ width:{size}px;height:{size}px;display:block }}
    </style></head><body>
    <img src="data:image/svg+xml;base64,{svg_b64}"/>
    </body></html>"""

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": size, "height": size})
        await page.set_content(html)
        await page.wait_for_timeout(200)
        buf = await page.screenshot(type="png", omit_background=True)
        await browser.close()

    import io

    return Image.open(io.BytesIO(buf)).convert("RGBA")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--svg", type=Path, default=ASSETS / "favicon.svg")
    args = ap.parse_args()

    print(f"rasterizing {args.svg} at {args.size}px …")
    img = asyncio.run(rasterize(args.svg, args.size))

    img.save(ASSETS / "icon.ico", sizes=[(s, s) for s in ICO_SIZES])
    img.resize((512, 512), Image.LANCZOS).save(ASSETS / "icon.png")
    print(f"wrote {ASSETS / 'icon.ico'} and icon.png")


if __name__ == "__main__":
    main()
