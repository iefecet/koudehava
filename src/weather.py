"""Open-Meteo'dan tum yerleskelerin hava durumunu tek istekte ceker."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import requests

API_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    "wind_speed_10m_max",
    "sunrise",
    "sunset",
]

CURRENT_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "weather_code",
    "wind_speed_10m",
]

# WMO weather code -> (Turkce aciklama, ikon anahtari)
WMO: dict[int, tuple[str, str]] = {
    0: ("Açık", "clear"),
    1: ("Az bulutlu", "mostly-clear"),
    2: ("Parçalı bulutlu", "partly-cloudy"),
    3: ("Kapalı", "overcast"),
    45: ("Puslu", "fog"),
    48: ("Kırağılı pus", "fog"),
    51: ("Hafif çisenti", "drizzle"),
    53: ("Çisenti", "drizzle"),
    55: ("Yoğun çisenti", "drizzle"),
    56: ("Dondurucu çisenti", "sleet"),
    57: ("Yoğun dondurucu çisenti", "sleet"),
    61: ("Hafif yağmurlu", "rain"),
    63: ("Yağmurlu", "rain"),
    65: ("Şiddetli yağmurlu", "rain"),
    66: ("Dondurucu yağmur", "sleet"),
    67: ("Şiddetli dondurucu yağmur", "sleet"),
    71: ("Hafif kar", "snow"),
    73: ("Kar yağışlı", "snow"),
    75: ("Yoğun kar", "snow"),
    77: ("Kar taneleri", "snow"),
    80: ("Hafif sağanak", "showers"),
    81: ("Sağanak yağışlı", "showers"),
    82: ("Kuvvetli sağanak", "showers"),
    85: ("Hafif kar sağanağı", "snow"),
    86: ("Yoğun kar sağanağı", "snow"),
    95: ("Gök gürültülü fırtına", "thunder"),
    96: ("Dolulu fırtına", "thunder"),
    99: ("Şiddetli dolulu fırtına", "thunder"),
}


def describe(code: int | None) -> tuple[str, str]:
    if code is None:
        return ("Bilinmiyor", "overcast")
    return WMO.get(int(code), ("Bilinmiyor", "overcast"))


@dataclass
class CampusWeather:
    id: str
    name: str
    subtitle: str
    carousel: bool
    temp_max: float | None = None
    temp_min: float | None = None
    temp_now: float | None = None
    feels_like: float | None = None
    humidity: float | None = None
    wind_max: float | None = None
    wind_now: float | None = None
    precip_prob: float | None = None
    precip_sum: float | None = None
    sunrise: str | None = None
    sunset: str | None = None
    code: int | None = None
    description: str = ""
    icon: str = "overcast"
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def sunrise_hm(self) -> str:
        return _hm(self.sunrise)

    @property
    def sunset_hm(self) -> str:
        return _hm(self.sunset)


def _hm(iso: str | None) -> str:
    if not iso:
        return "--:--"
    try:
        return dt.datetime.fromisoformat(iso).strftime("%H:%M")
    except ValueError:
        return "--:--"


def _first(value: Any) -> Any:
    """Open-Meteo gunluk alanlari liste dondurur; ilk gunu al."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def fetch(campuses: list[dict], timezone: str = "Europe/Istanbul",
          timeout: int = 30) -> list[CampusWeather]:
    """Butun yerleskeler icin tek HTTP istegi atar."""
    if not campuses:
        return []

    params = {
        "latitude": ",".join(str(c["lat"]) for c in campuses),
        "longitude": ",".join(str(c["lon"]) for c in campuses),
        "daily": ",".join(DAILY_FIELDS),
        "current": ",".join(CURRENT_FIELDS),
        "timezone": timezone,
        "forecast_days": 1,
        "wind_speed_unit": "kmh",
    }

    response = requests.get(API_URL, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    # Tek konumda dict, cok konumda liste doner.
    blocks = payload if isinstance(payload, list) else [payload]
    if len(blocks) != len(campuses):
        raise RuntimeError(
            f"Open-Meteo {len(blocks)} konum dondurdu, {len(campuses)} bekleniyordu."
        )

    results: list[CampusWeather] = []
    for campus, block in zip(campuses, blocks):
        daily = block.get("daily", {}) or {}
        current = block.get("current", {}) or {}
        code = _first(daily.get("weather_code"))
        description, icon = describe(code)

        results.append(
            CampusWeather(
                id=campus["id"],
                name=campus["name"],
                subtitle=campus.get("subtitle", ""),
                carousel=bool(campus.get("carousel")),
                temp_max=_first(daily.get("temperature_2m_max")),
                temp_min=_first(daily.get("temperature_2m_min")),
                temp_now=current.get("temperature_2m"),
                feels_like=current.get("apparent_temperature"),
                humidity=current.get("relative_humidity_2m"),
                wind_max=_first(daily.get("wind_speed_10m_max")),
                wind_now=current.get("wind_speed_10m"),
                precip_prob=_first(daily.get("precipitation_probability_max")),
                precip_sum=_first(daily.get("precipitation_sum")),
                sunrise=_first(daily.get("sunrise")),
                sunset=_first(daily.get("sunset")),
                code=int(code) if code is not None else None,
                description=description,
                icon=icon,
            )
        )
    return results
