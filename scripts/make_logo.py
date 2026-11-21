"""KOU'de Hava logosunu PNG olarak uretir.

  python scripts/make_logo.py

Uretilenler (assets/ icine):
  profil-1080.png       Instagram profil fotografi (yazili rozet)
  logo-yazili-1080.png  rozet + "Yerleske hava durumu" alt basligi
  logo-mark-1080.png    yazisiz varyant (kucuk kullanim)
  logo-256.png          yazisiz varyant, kucuk
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LOGO = ASSETS / "logo-koudehava.svg"

SKY = "linear-gradient(150deg, #5FB8FF 0%, #2585E0 52%, #0F5BB5 100%)"
INK = "#0F4733"
INK_SOFT = "#4C7A68"

FONT = ('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Plus+Jakarta+Sans:wght@600;800&display=swap" rel="stylesheet">')

MARK = ASSETS / "logo-koudehava-mark.svg"


def svg_body(path: Path) -> str:
    """SVG govdesini kapsayiciyi dolduracak sekilde dondurur."""
    markup = path.read_text(encoding="utf-8")
    markup = markup[markup.index("<svg"):]
    # Dikkat: bu olcu hem <svg> etiketinde hem ic sekillerde gecebilir;
    # sadece kok etiketi degistir.
    return markup.replace('width="120" height="120"',
                          'width="100%" height="100%"', 1)


def page(body: str, size: int, background: str = "#FFFFFF") -> str:
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">{FONT}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {size}px; height: {size}px; overflow: hidden; }}
  body {{
    background: {background};
    font-family: "Plus Jakarta Sans", system-ui, sans-serif;
    display: grid;
    place-items: center;
  }}
  svg {{ display: block; }}
</style></head><body>{body}</body></html>"""


def profile_html(size: int = 1080) -> str:
    """Instagram profil fotografi: rozet, daire kirpmaya pay birakacak kadar."""
    d = int(size * 0.88)
    return page(f'<div style="width:{d}px;height:{d}px">{svg_body(LOGO)}</div>',
                size)


def wordmark_html(size: int = 1080) -> str:
    """Rozet + alt baslik. Ad zaten rozetin icinde."""
    d = int(size * 0.56)
    body = f"""
    <div style="display:flex;flex-direction:column;align-items:center;gap:44px">
      <div style="width:{d}px;height:{d}px">{svg_body(LOGO)}</div>
      <div style="font-size:34px;font-weight:600;letter-spacing:6px;
                  text-transform:uppercase;color:{INK_SOFT}">Yerleşke hava durumu</div>
    </div>"""
    return page(body, size)


def mark_html(size: int = 1080) -> str:
    """Yazisiz varyant: kucuk kullanim ve favicon icin."""
    d = int(size * 0.9)
    return page(f'<div style="width:{d}px;height:{d}px">{svg_body(MARK)}</div>',
                size)


def small_html(size: int = 256) -> str:
    d = int(size * 0.94)
    return page(f'<div style="width:{d}px;height:{d}px">{svg_body(MARK)}</div>',
                size)


def main() -> int:
    if not LOGO.exists():
        print(f"HATA: {LOGO} bulunamadı.", file=sys.stderr)
        return 2

    jobs = [
        ("profil-1080.png", profile_html(1080), 1080),
        ("logo-yazili-1080.png", wordmark_html(1080), 1080),
        ("logo-mark-1080.png", mark_html(1080), 1080),
        ("logo-256.png", small_html(256), 256),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for filename, html, size in jobs:
            page_obj = browser.new_page(
                viewport={"width": size, "height": size}, device_scale_factor=1
            )
            page_obj.set_content(html, wait_until="load")
            try:
                page_obj.evaluate("document.fonts.ready")
                page_obj.wait_for_timeout(350)
            except Exception:
                page_obj.wait_for_timeout(600)
            page_obj.screenshot(path=str(ASSETS / filename))
            page_obj.close()
            print(f"  {ASSETS / filename}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
