"""HTML sablonlarini Playwright ile 1080x1350 PNG'ye cevirir."""

from __future__ import annotations

import base64
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

import theme
from icons import svg as icon_svg
from weather import CampusWeather

WIDTH = 1080
HEIGHT = 1350

TEMPLATE_DIR = Path(__file__).parent / "templates"
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

# Resmi KOU logosu bu adlardan biriyle assets/ icine konur.
KOU_LOGO_NAMES = ("logo-kou.svg", "logo-kou.png", "logo-kou.jpg",
                  "logo-kou.jpeg", "logo-kou.webp")
BRAND_LOGO = "logo-koudehava.svg"
# Ust barda yaninda zaten yazi var; rozetin icindeki yazi 72 px'te
# okunmadigi icin orada yazisiz varyant kullaniliyor.
BRAND_LOGO_MARK = "logo-koudehava-mark.svg"

_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp"}

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
TR_DAYS = [
    "Pazartesi", "Salı", "Çarşamba", "Perşembe",
    "Cuma", "Cumartesi", "Pazar",
]



def data_uri(path: Path) -> str | None:
    """Dosyayi data URI'ye cevirir. Playwright set_content ile calistigi icin
    gorseller sayfaya gomulu olmak zorunda; disaridan dosya yolu okunamaz."""
    if not path.exists():
        return None
    mime = _MIME.get(path.suffix.lower(), "application/octet-stream")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def find_kou_logo() -> str | None:
    """assets/ icindeki resmi KOU logosunu bulur; yoksa None."""
    for name in KOU_LOGO_NAMES:
        uri = data_uri(ASSET_DIR / name)
        if uri:
            return uri
    return None


def brand_logo_markup(mark_only: bool = True) -> str:
    """KOU'de Hava logosunu satir ici SVG olarak dondurur."""
    name = BRAND_LOGO_MARK if mark_only else BRAND_LOGO
    path = ASSET_DIR / name
    if not path.exists():
        path = ASSET_DIR / BRAND_LOGO
    if not path.exists():
        return ""
    markup = path.read_text(encoding="utf-8")
    return markup[markup.index("<svg"):]


def fmt_temp(value: float | None) -> str:
    if value is None:
        return "--"
    return str(int(round(value)))


def fmt_int(value: float | None) -> str:
    if value is None:
        return "--"
    return str(int(round(value)))


def _env(mode: str = "dark") -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals.update(
        fmt_temp=fmt_temp,
        fmt_int=fmt_int,
        icon_svg=lambda icon, size=120: icon_svg(icon, size, mode),
    )
    return env


def _date_context(day: dt.date, moment: dt.datetime | None = None) -> dict:
    return {
        "date_long": f"{day.day} {TR_MONTHS[day.month - 1]}",
        "weekday": TR_DAYS[day.weekday()],
        # Gorselin uretildigi, yani paylasimin yapildigi saat
        "time_hm": moment.strftime("%H:%M") if moment else "",
    }


def build_html(campuses: list[CampusWeather], day: dt.date, config: dict) -> list[tuple[str, str]]:
    """(dosya_adi, html) listesi dondurur. Ilk eleman ozet slayti olabilir."""
    mode = config.get("theme", "light")
    env = _env(mode)
    account = config.get("account", {})
    moment = dt.datetime.now(ZoneInfo(config.get("timezone", "Europe/Istanbul")))
    carousel_cfg = config.get("carousel", {})
    max_slides = int(carousel_cfg.get("max_slides", 10))
    include_summary = bool(carousel_cfg.get("include_summary_slide", True))

    base_ctx = {
        "width": WIDTH,
        "height": HEIGHT,
        "brand": account.get("brand", "KOÜ'de Hava"),
        "tagline": account.get("tagline", "Yerleşke Hava Durumu"),
        "university": account.get("university", "Kocaeli Üniversitesi"),
        "handle": account.get("handle", ""),
        "kou_logo": find_kou_logo(),
        "brand_logo": brand_logo_markup(),
        **_date_context(day, moment),
    }

    pages: list[tuple[str, str]] = []

    if include_summary:
        with_max = [c for c in campuses if c.temp_max is not None]
        tpl = env.get_template("summary.html")
        pages.append((
            "00-ozet.png",
            tpl.render(
                **base_ctx,
                p=theme.summary(mode),
                footer_note="Veri: Open-Meteo",
                campuses=campuses,
                warmest=max(with_max, key=lambda c: c.temp_max) if with_max else None,
                coldest=min(with_max, key=lambda c: c.temp_max) if with_max else None,
            ),
        ))

    slots = max_slides - len(pages)
    selected = [c for c in campuses if c.carousel][:slots]

    tpl = env.get_template("campus.html")
    for index, campus in enumerate(selected, start=1):
        pages.append((
            f"{index:02d}-{campus.id}.png",
            tpl.render(
                **base_ctx,
                p=theme.get(campus.icon, mode),
                footer_note=f"{index} / {len(selected)} · Veri: Open-Meteo",
                c=campus,
                icon_svg=icon_svg(campus.icon, 168, mode),
            ),
        ))

    return pages


def render(campuses: list[CampusWeather], day: dt.date, config: dict,
           outdir: Path) -> list[Path]:
    """Slaytlari PNG olarak diske yazar, sirali dosya yollarini dondurur."""
    outdir.mkdir(parents=True, exist_ok=True)
    pages = build_html(campuses, day, config)
    written: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--font-render-hinting=none"])
        page = browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
        )
        for filename, html in pages:
            page.set_content(html, wait_until="load")
            try:
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(350)
            except Exception:
                page.wait_for_timeout(600)
            target = outdir / filename
            page.screenshot(path=str(target))
            written.append(target)
        browser.close()

    return written
