"""Gonderi aciklamasini (caption) uretir.

Metnin kendisi config["post"]["caption_template"] icindeki sablondan gelir;
boylece arayuzden duzenlenebilir. Sablonda {degisken} yer tutuculari kullanilir.
"""

from __future__ import annotations

import datetime as dt
import re

from render import TR_DAYS, TR_MONTHS
from weather import CampusWeather

DEFAULT_HASHTAGS = (
    "#kocaeliüniversitesi #koü #umuttepe #kocaeli #izmit "
    "#havadurumu #kampüs #öğrenci"
)

DEFAULT_TEMPLATE = """🗓 {tarih} — {marka}

🔆 En ılık: {en_ilik}
❄️ En serin: {en_serin}
{yagis_uyarisi}
{ruzgar_uyarisi}

Yerleşke yerleşke detaylar için kaydır 👉

{detaylar}

Veri: Open-Meteo · otomatik paylaşım

{hashtagler}"""

# Sablonda kullanilabilecek yer tutucular (arayuzde listelenir)
PLACEHOLDERS = [
    ("tarih", "21 Kasım 2026, Cumartesi"),
    ("saat", "06:30"),
    ("marka", "KOÜ'de Hava"),
    ("hesap", "@koudehava"),
    ("yerleske_sayisi", "15"),
    ("en_ilik", "Anıtpark 18°C"),
    ("en_serin", "Umuttepe 16°C"),
    ("en_ilik_ad", "Anıtpark"),
    ("en_serin_ad", "Umuttepe"),
    ("yagis_uyarisi", "Şemsiye uyarısı satırı"),
    ("ruzgar_uyarisi", "Rüzgâr uyarısı satırı"),
    ("detaylar", "Yerleşke listesi"),
    ("hashtagler", "Hashtag satırı"),
]

WET_ICONS = {"rain", "showers", "drizzle", "thunder", "snow", "sleet"}


class _SafeDict(dict):
    """Bilinmeyen yer tutucu sablonu patlatmasin, oldugu gibi kalsin."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _tr_date(day: dt.date) -> str:
    return f"{day.day} {TR_MONTHS[day.month - 1]} {day.year}, {TR_DAYS[day.weekday()]}"


def _num(value: float | None) -> str:
    return "--" if value is None else str(int(round(value)))


def build_context(campuses: list[CampusWeather], day: dt.date,
                  config: dict | None = None,
                  moment: dt.datetime | None = None) -> dict[str, str]:
    """Sablonda kullanilabilecek tum degerleri hazirlar."""
    config = config or {}
    post = config.get("post", {})
    account = config.get("account", {})
    rain_pct = post.get("rain_warning_percent", 50)
    wind_kmh = post.get("wind_warning_kmh", 40)
    max_lines = post.get("caption_detail_lines", 10)

    with_max = [c for c in campuses if c.temp_max is not None]
    warmest = max(with_max, key=lambda c: c.temp_max) if with_max else None
    coldest = min(with_max, key=lambda c: c.temp_max) if with_max else None

    rainy = [c for c in campuses
             if (c.precip_prob or 0) >= rain_pct or c.icon in WET_ICONS]
    if rainy:
        names = ", ".join(c.name for c in rainy[:6])
        extra = f" (+{len(rainy) - 6})" if len(rainy) > 6 else ""
        rain_line = f"☔ Şemsiye gerekebilir: {names}{extra}"
    else:
        rain_line = "☔ Bugün yağış beklenmiyor."

    windy = [c for c in campuses if (c.wind_max or 0) >= wind_kmh]
    wind_line = (
        "💨 Rüzgârlı: "
        + ", ".join(f"{c.name} {_num(c.wind_max)} km/s" for c in windy[:4])
    ) if windy else ""

    details = "\n".join(
        f"• {c.name}: {_num(c.temp_min)}° / {_num(c.temp_max)}° · {c.description}"
        for c in campuses[:max_lines]
    )

    return {
        "tarih": _tr_date(day),
        "saat": moment.strftime("%H:%M") if moment else "",
        "marka": account.get("brand", "KOÜ'de Hava"),
        "hesap": account.get("handle", ""),
        "yerleske_sayisi": str(len(campuses)),
        "en_ilik": f"{warmest.name} {_num(warmest.temp_max)}°C" if warmest else "—",
        "en_serin": f"{coldest.name} {_num(coldest.temp_max)}°C" if coldest else "—",
        "en_ilik_ad": warmest.name if warmest else "—",
        "en_serin_ad": coldest.name if coldest else "—",
        "yagis_uyarisi": rain_line,
        "ruzgar_uyarisi": wind_line,
        "detaylar": details,
        "hashtagler": post.get("hashtags", DEFAULT_HASHTAGS),
    }


def render_template(template: str, context: dict[str, str]) -> str:
    """Sablonu doldurur, bos satirlari toparlar, 2200 karaktere sigdirir."""
    text = template.format_map(_SafeDict(context))
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > 2200:
        tags = context.get("hashtagler", "")
        head = text[:2180].rsplit("\n", 1)[0]
        text = head + "\n\n" + tags if tags else head
    return text


def build(campuses: list[CampusWeather], day: dt.date,
          config: dict | None = None, moment: dt.datetime | None = None) -> str:
    """Yapilandirmadaki sablona gore gonderi aciklamasini uretir."""
    if not campuses:
        return f"{_tr_date(day)} · veri alınamadı."

    config = config or {}
    template = config.get("post", {}).get("caption_template") or DEFAULT_TEMPLATE
    return render_template(template, build_context(campuses, day, config, moment))
