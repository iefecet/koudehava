"""Hava durumuna gore renk paletleri — acik ve koyu tema.

Tema `config/campuses.json` icindeki "theme" alani ile secilir: "light" | "dark".
Her palet sablonlara CSS degiskeni olarak gecer; sablonlarda sabit renk yoktur.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    mode: str          # "light" | "dark"
    background: str    # tam CSS background degeri
    ink: str           # birincil metin
    ink2: str          # ikincil metin
    ink3: str          # etiket / soluk metin
    hair: str          # belirgin ayrac cizgisi
    hair_soft: str     # yumusak ayrac cizgisi
    surface: str       # kart / serit zemini
    accent: str        # vurgu rengi
    glow_a: str        # sag ustteki isik lekesi
    glow_b: str        # sol alttaki isik lekesi

    @property
    def is_light(self) -> bool:
        return self.mode == "light"


# ---------------------------------------------------------------- koyu tema

def _dark(top: str, mid: str, bottom: str, accent: str,
          glow_a: str, glow_b: str) -> Palette:
    return Palette(
        mode="dark",
        background=f"linear-gradient(168deg, {top} 0%, {mid} 46%, {bottom} 100%)",
        ink="#FFFFFF",
        ink2="rgba(255, 255, 255, 0.70)",
        ink3="rgba(255, 255, 255, 0.46)",
        hair="rgba(255, 255, 255, 0.16)",
        hair_soft="rgba(255, 255, 255, 0.09)",
        surface="rgba(255, 255, 255, 0.07)",
        accent=accent,
        glow_a=glow_a,
        glow_b=glow_b,
    )


DARK: dict[str, Palette] = {
    "clear": _dark("#2F86FF", "#0F47A6", "#061A3F", "#FFC247", "#FFB03A", "#36C5FF"),
    "mostly-clear": _dark("#2B7CF0", "#0E3F94", "#061838", "#FFCD5E", "#FFA94D", "#4CC7FF"),
    "partly-cloudy": _dark("#4A8BC9", "#1D4A80", "#0A1F38", "#9BD2FF", "#BFE3FF", "#3F8FD6"),
    "overcast": _dark("#6A7686", "#333D4A", "#12171D", "#D5DFEA", "#AEBCCB", "#5A6775"),
    "fog": _dark("#7C8792", "#3C454E", "#161B20", "#E3E9EF", "#C9D2DA", "#6C7782"),
    "drizzle": _dark("#2191A8", "#0D4B5E", "#05212C", "#8BEAF5", "#5FD8E8", "#1A6F86"),
    "rain": _dark("#1D6E99", "#0B3754", "#04151F", "#6FD0FA", "#4BB8F0", "#0F4E70"),
    "showers": _dark("#2080A5", "#0C415C", "#051A26", "#7ADAF7", "#59C9EE", "#15607F"),
    "sleet": _dark("#4A7793", "#1E3F56", "#0A1A26", "#B6E2F2", "#8FCFE6", "#2E5A76"),
    "snow": _dark("#7797BE", "#35507A", "#141F33", "#E6F3FF", "#C9E4FF", "#5A7AA8"),
    "thunder": _dark("#6A3FB5", "#331C6B", "#120B26", "#FFD24D", "#B57BFF", "#3F63FF"),
}

DARK_SUMMARY = _dark("#1C5FB8", "#0B2F66", "#050F24", "#FFC247", "#4FA8FF", "#FFB03A")


# --------------------------------------------------------------- acik tema

# Google Hava Durumu kartindaki gibi: beyaza yakin zemin, koyu gri metin,
# veriler icin mavi vurgu, renkli ikonlar.
_L_INK = "#1A1C1E"
_L_INK2 = "#4E5560"
_L_INK3 = "#858C96"
_L_HAIR = "rgba(16, 24, 40, 0.13)"
_L_HAIR_SOFT = "rgba(16, 24, 40, 0.07)"
_L_SURFACE = "rgba(16, 24, 40, 0.045)"


def _light(tint_top: str, tint_bottom: str, accent: str,
           glow_a: str, glow_b: str) -> Palette:
    return Palette(
        mode="light",
        background=(
            f"linear-gradient(168deg, {tint_top} 0%, #FFFFFF 46%, "
            f"{tint_bottom} 100%)"
        ),
        ink=_L_INK,
        ink2=_L_INK2,
        ink3=_L_INK3,
        hair=_L_HAIR,
        hair_soft=_L_HAIR_SOFT,
        surface=_L_SURFACE,
        accent=accent,
        glow_a=glow_a,
        glow_b=glow_b,
    )


LIGHT: dict[str, Palette] = {
    "clear": _light("#FFF6DF", "#EFF5FF", "#E8820C", "#FFD98A", "#B5D5FF"),
    "mostly-clear": _light("#FFF7E4", "#EDF3FF", "#E8820C", "#FFDC97", "#BBD7FF"),
    "partly-cloudy": _light("#F1F7FF", "#EDF1F7", "#1A73E8", "#CFE5FF", "#BDCCDD"),
    "overcast": _light("#F3F5F8", "#EBEEF2", "#5B6470", "#C7D0DA", "#A9B4C0"),
    "fog": _light("#F4F6F7", "#ECEFF1", "#687682", "#CDD5DB", "#AEB8C0"),
    "drizzle": _light("#EAF7FA", "#EDF3F8", "#0E7C94", "#8BE3F0", "#9CC6DB"),
    "rain": _light("#E9F3FB", "#E8EFF7", "#1A73E8", "#7FC8F5", "#8FB4D8"),
    "showers": _light("#EAF5FA", "#ECF2F8", "#1577A8", "#86D2EF", "#93BBD8"),
    "sleet": _light("#EEF5F9", "#EAF0F6", "#2A7093", "#A9D8EA", "#9BB8CE"),
    "snow": _light("#F2F8FF", "#E9F0F9", "#2B7FC4", "#D2E8FF", "#C0D3E6"),
    "thunder": _light("#F6F4FC", "#EFF2FA", "#1A73E8", "#D3C7F5", "#C2D3F7"),
}

LIGHT_SUMMARY = _light("#EDF4FF", "#EEF1F8", "#1A73E8", "#C3DCFF", "#D5E0EE")


def get(icon: str, mode: str = "dark") -> Palette:
    table = LIGHT if mode == "light" else DARK
    fallback = table["overcast"]
    return table.get(icon, fallback)


def summary(mode: str = "dark") -> Palette:
    return LIGHT_SUMMARY if mode == "light" else DARK_SUMMARY
