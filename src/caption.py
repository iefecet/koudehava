"""Gonderi aciklamasini (caption) uretir."""

from __future__ import annotations

import datetime as dt

from render import TR_DAYS, TR_MONTHS
from weather import CampusWeather

DEFAULT_HASHTAGS = (
    "#kocaeliüniversitesi #koü #umuttepe #kocaeli #izmit "
    "#havadurumu #kampüs #öğrenci"
)

WET_ICONS = {"rain", "showers", "drizzle", "thunder", "snow", "sleet"}


def _tr_date(day: dt.date) -> str:
    return f"{day.day} {TR_MONTHS[day.month - 1]} {day.year}, {TR_DAYS[day.weekday()]}"


def _num(value: float | None) -> str:
    return "--" if value is None else str(int(round(value)))


def build(campuses: list[CampusWeather], day: dt.date,
          config: dict | None = None, max_lines: int | None = None) -> str:
    """Ozet + uyari + hashtag iceren caption.

    Metinle ilgili ayarlar config["post"] altindan okunur; arayuzden
    degistirilebilsin diye koda gomulu degil.
    """
    post = (config or {}).get("post", {})
    hashtags = post.get("hashtags", DEFAULT_HASHTAGS)
    rain_pct = post.get("rain_warning_percent", 50)
    wind_kmh = post.get("wind_warning_kmh", 40)
    if max_lines is None:
        max_lines = post.get("caption_detail_lines", 10)
    if not campuses:
        return f"{_tr_date(day)} · veri alinamadi."

    with_max = [c for c in campuses if c.temp_max is not None]
    lines = [f"🗓 {_tr_date(day)} — KOÜ yerleşkelerinde hava", ""]

    if with_max:
        warmest = max(with_max, key=lambda c: c.temp_max)
        coldest = min(with_max, key=lambda c: c.temp_max)
        lines.append(
            f"🔆 En ılık: {warmest.name} {_num(warmest.temp_max)}°C"
        )
        lines.append(
            f"❄️ En serin: {coldest.name} {_num(coldest.temp_max)}°C"
        )

    rainy = [c for c in campuses
             if (c.precip_prob or 0) >= rain_pct or c.icon in WET_ICONS]
    if rainy:
        names = ", ".join(c.name for c in rainy[:6])
        extra = f" (+{len(rainy) - 6})" if len(rainy) > 6 else ""
        lines.append(f"☔ Şemsiye gerekebilir: {names}{extra}")
    else:
        lines.append("☔ Bugün yağış beklenmiyor.")

    windy = [c for c in campuses if (c.wind_max or 0) >= wind_kmh]
    if windy:
        lines.append(
            "💨 Rüzgârlı: "
            + ", ".join(f"{c.name} {_num(c.wind_max)} km/s" for c in windy[:4])
        )

    lines.append("")
    lines.append("Yerleşke yerleşke detaylar için kaydır 👉")
    lines.append("")

    detail = [
        f"• {c.name}: {_num(c.temp_min)}° / {_num(c.temp_max)}° · {c.description}"
        for c in campuses[:max_lines]
    ]
    lines.extend(detail)

    lines.append("")
    lines.append("Veri: Open-Meteo · otomatik paylaşım")
    lines.append("")
    lines.append(hashtags)

    caption = "\n".join(lines)
    # Instagram caption siniri 2200 karakter
    if len(caption) > 2200:
        caption = caption[:2180].rsplit("\n", 1)[0] + "\n\n" + HASHTAGS
    return caption
