"""Hava durumu ikonlari: inline SVG, emoji/font bagimliligi yok."""

_RAYS = "".join(
    f'<line x1="50" y1="18" x2="50" y2="6" stroke="#FFC93C" stroke-width="7" '
    f'stroke-linecap="round" transform="rotate({a} 50 50)"/>'
    for a in range(0, 360, 45)
)

_CLOUD = (
    '<path d="M28 72h46a16 16 0 0 0 1.5-31.9A23 23 0 0 0 32 36.5A15 15 0 0 0 28 72z" '
    'fill="url(#cloudGrad)"/>'
)

_CLOUD_SMALL = (
    '<path d="M38 76h40a14 14 0 0 0 1.3-27.9A20 20 0 0 0 41.5 44A13 13 0 0 0 38 76z" '
    'fill="url(#cloudGrad)"/>'
)


def _drops(xs, color="#4FA3F7"):
    return "".join(
        f'<path d="M{x} 78 q4 7 0 11 q-4-4 0-11z" fill="{color}"/>' for x in xs
    )


def _snow(xs):
    out = []
    for x in xs:
        out.append(
            f'<g stroke="#BFE3FF" stroke-width="4" stroke-linecap="round">'
            f'<line x1="{x - 5}" y1="84" x2="{x + 5}" y2="84"/>'
            f'<line x1="{x}" y1="79" x2="{x}" y2="89"/>'
            f'<line x1="{x - 3.5}" y1="80.5" x2="{x + 3.5}" y2="87.5"/>'
            f'<line x1="{x - 3.5}" y1="87.5" x2="{x + 3.5}" y2="80.5"/>'
            f"</g>"
        )
    return "".join(out)


_BOLT = '<path d="M52 72l-14 22h11l-4 18 19-26H52l6-14z" fill="#FFC93C"/>'

_FOG_LINES = "".join(
    f'<line x1="{22 + (i % 2) * 6}" y1="{74 + i * 9}" x2="{78 - (i % 2) * 6}" '
    f'y2="{74 + i * 9}" stroke="#CBD5E1" stroke-width="6" stroke-linecap="round"/>'
    for i in range(3)
)

_SHAPES = {
    "clear": _RAYS + '<circle cx="50" cy="50" r="22" fill="url(#sunGrad)"/>',
    "mostly-clear": (
        '<g transform="translate(14 -8) scale(0.78)">'
        + _RAYS
        + '<circle cx="50" cy="50" r="22" fill="url(#sunGrad)"/></g>'
        + _CLOUD_SMALL
    ),
    "partly-cloudy": (
        '<g transform="translate(20 -10) scale(0.7)">'
        + _RAYS
        + '<circle cx="50" cy="50" r="22" fill="url(#sunGrad)"/></g>'
        + _CLOUD
    ),
    "overcast": (
        '<g transform="translate(-8 -6) scale(0.72)" opacity="0.6">' + _CLOUD + "</g>"
        + _CLOUD
    ),
    "fog": _CLOUD_SMALL + _FOG_LINES,
    "drizzle": _CLOUD + _drops([38, 52, 66], "#7FC2FF"),
    "rain": _CLOUD + _drops([36, 50, 64]) + _drops([43, 57]),
    "showers": (
        '<g transform="translate(18 -12) scale(0.62)">'
        + _RAYS
        + '<circle cx="50" cy="50" r="22" fill="url(#sunGrad)"/></g>'
        + _CLOUD
        + _drops([38, 52, 66])
    ),
    "sleet": _CLOUD + _drops([38, 62]) + _snow([50]),
    "snow": _CLOUD + _snow([36, 52, 68]),
    "thunder": _CLOUD + _BOLT + _drops([34, 70]),
}

_DEFS_TEMPLATE = """
<defs>
  <linearGradient id="sun{u}" x1="0" y1="0" x2="0.9" y2="1">
    <stop offset="0%" stop-color="#FFE9A3"/>
    <stop offset="45%" stop-color="#FFC43D"/>
    <stop offset="100%" stop-color="#F58A00"/>
  </linearGradient>
  <linearGradient id="cloud{u}" x1="0.1" y1="0" x2="0.6" y2="1">
    <stop offset="0%" stop-color="#FFFFFF"/>
    <stop offset="52%" stop-color="{c_mid}"/>
    <stop offset="100%" stop-color="{c_end}"/>
  </linearGradient>
  <filter id="soft{u}" x="-35%" y="-35%" width="180%" height="180%">
    <feDropShadow dx="0" dy="{sh_dy}" stdDeviation="{sh_blur}"
                  flood-color="{sh_color}" flood-opacity="{sh_op}"/>
  </filter>
  <filter id="halo{u}" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="7"/>
  </filter>
</defs>
"""

# Acik zeminde beyaz bulut kaybolur: kenar tonunu koyulastirip golgeyi
# yumusatiyoruz. Koyu zeminde tam tersi gerekiyor.
_MODE_STYLE = {
    "dark": {
        "c_mid": "#EDF4FB", "c_end": "#C6D7E8",
        "sh_dy": "4", "sh_blur": "4.5",
        "sh_color": "#04101F", "sh_op": "0.34",
    },
    "light": {
        "c_mid": "#E4EDF6", "c_end": "#AFC3D7",
        "sh_dy": "3", "sh_blur": "3.2",
        "sh_color": "#334155", "sh_op": "0.20",
    },
}

# Gradyan/filtre id'leri birden fazla ikon ayni sayfada oldugunda cakismasin diye
# her cagrida benzersiz bir sonek alir.
_counter = {"n": 0}


def svg(icon: str, size: int = 120, mode: str = "dark") -> str:
    """Verilen ikon anahtari icin hazir SVG dondurur."""
    _counter["n"] += 1
    uid = _counter["n"]
    style = _MODE_STYLE.get(mode, _MODE_STYLE["dark"])

    shapes = _SHAPES.get(icon, _SHAPES["overcast"])
    shapes = shapes.replace("url(#sunGrad)", f"url(#sun{uid})")
    shapes = shapes.replace("url(#cloudGrad)", f"url(#cloud{uid})")

    halo = ""
    if icon in ("clear", "mostly-clear"):
        opacity = "0.26" if mode == "light" else "0.38"
        halo = (
            f'<circle cx="50" cy="50" r="26" fill="#FFCB5C" opacity="{opacity}" '
            f'filter="url(#halo{uid})"/>'
        )

    return (
        f'<svg class="wicon" width="{size}" height="{size}" viewBox="0 0 100 115" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f"{_DEFS_TEMPLATE.format(u=uid, **style)}{halo}"
        f'<g filter="url(#soft{uid})">{shapes}</g></svg>'
    )
