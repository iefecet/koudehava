"""Gun ici sicaklik ve yagis grafigi (satir ici SVG).

Tasarim notu: sicaklik (°C) ve yagis olasiligi (%) farkli olceklerdir,
bu yuzden tek grafige iki y ekseniyle bindirilmez. Ortak zaman eksenini
paylasan iki ayri serit olarak cizilir.

Renkler dataviz dogrulayicisindan gecirilmistir (light yuzey):
  #C96A00 (sicaklik) ve #1A73E8 (yagis) — CVD ayrimi ΔE 29.7, kontrast >= 3:1.
"""

from __future__ import annotations

import datetime as dt

TEMP = "#C96A00"
TEMP_FILL = "#F0A24A"
RAIN = "#1A73E8"

W = 944          # grafik genisligi
PAD_L = 4
PAD_R = 4

TEMP_TOP = 30    # sicaklik seridi
TEMP_H = 78
RAIN_TOP = 140   # yagis seridi
RAIN_H = 48
AXIS_Y = 212
H = 224


def _hour(iso: str) -> int:
    try:
        return dt.datetime.fromisoformat(iso).hour
    except ValueError:
        return 0


def _x(index: int, count: int) -> float:
    """Saat indeksini yatay konuma cevirir (serit ortasi)."""
    inner = W - PAD_L - PAD_R
    step = inner / count
    return PAD_L + step * (index + 0.5)


def _smooth_path(points: list[tuple[float, float]]) -> str:
    """Koseleri yumusatilmis cizgi (Catmull-Rom benzeri)."""
    if not points:
        return ""
    if len(points) < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)

    d = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        x0, y0 = points[max(i - 1, 0)]
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        x3, y3 = points[min(i + 2, len(points) - 1)]
        c1x = x1 + (x2 - x0) / 6
        c1y = y1 + (y2 - y0) / 6
        c2x = x2 - (x3 - x1) / 6
        c2y = y2 - (y3 - y1) / 6
        d.append(f"C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {x2:.1f},{y2:.1f}")
    return " ".join(d)


def build(campus, now: dt.datetime | None = None) -> str:
    """Yerleske icin gun ici grafigi dondurur; veri yoksa bos dizi."""
    temps = [t for t in campus.hourly_temp if t is not None]
    if len(campus.hourly_time) < 6 or len(temps) < 6:
        return ""

    count = len(campus.hourly_time)
    lo, hi = min(temps), max(temps)
    span = max(hi - lo, 1.0)

    def temp_y(value: float) -> float:
        # Ust ve altta birer miktar bosluk birak
        ratio = (value - lo) / span
        return TEMP_TOP + TEMP_H - 10 - ratio * (TEMP_H - 20)

    points = [
        (_x(i, count), temp_y(v))
        for i, v in enumerate(campus.hourly_temp)
        if v is not None
    ]

    parts: list[str] = [
        f'<svg class="daychart" viewBox="0 0 {W} {H}" width="100%" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    ]

    # --- gece golgesi: gun dogumundan once, gun batimindan sonra ---
    def band(iso: str | None) -> float | None:
        if not iso:
            return None
        try:
            t = dt.datetime.fromisoformat(iso)
        except ValueError:
            return None
        return _x(t.hour + t.minute / 60 - 0.5, count)

    sunrise_x, sunset_x = band(campus.sunrise), band(campus.sunset)
    if sunrise_x is not None and sunset_x is not None:
        for x0, x1 in ((PAD_L, sunrise_x), (sunset_x, W - PAD_R)):
            if x1 > x0:
                parts.append(
                    f'<rect x="{x0:.1f}" y="{TEMP_TOP - 12}" '
                    f'width="{x1 - x0:.1f}" height="{RAIN_TOP + RAIN_H - TEMP_TOP + 12:.0f}" '
                    f'fill="currentColor" opacity="0.045"/>'
                )

    # --- sicaklik seridi ---
    parts.append(
        f'<text x="0" y="{TEMP_TOP - 16}" class="ct-label">SICAKLIK</text>'
    )
    area = (
        _smooth_path(points)
        + f" L{points[-1][0]:.1f},{TEMP_TOP + TEMP_H:.1f}"
        + f" L{points[0][0]:.1f},{TEMP_TOP + TEMP_H:.1f} Z"
    )
    parts.append(f'<path d="{area}" fill="{TEMP_FILL}" opacity="0.17"/>')
    parts.append(
        f'<path d="{_smooth_path(points)}" fill="none" stroke="{TEMP}" '
        f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # en yuksek / en dusuk noktalar dogrudan etiketli (renk tek basina tasimasin)
    for value, label in ((hi, f"{round(hi)}°"), (lo, f"{round(lo)}°")):
        idx = next(i for i, v in enumerate(campus.hourly_temp) if v == value)
        px, py = _x(idx, count), temp_y(value)
        above = value == hi
        # etiket kenarlardan tasmasin
        label_x = min(max(px, 26.0), W - 26.0)
        label_y = py - 13 if above else py + 24
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{TEMP}" '
            f'stroke="#FFFFFF" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" '
            f'class="ct-point" text-anchor="middle">{label}</text>'
        )

    # --- yagis seridi ---
    parts.append(
        f'<text x="0" y="{RAIN_TOP - 14}" class="ct-label">YAĞIŞ OLASILIĞI</text>'
    )
    parts.append(
        f'<line x1="{PAD_L}" y1="{RAIN_TOP + RAIN_H:.0f}" x2="{W - PAD_R}" '
        f'y2="{RAIN_TOP + RAIN_H:.0f}" stroke="currentColor" '
        f'stroke-width="1" opacity="0.18"/>'
    )

    inner = W - PAD_L - PAD_R
    bar_w = max(inner / count - 3.0, 4.0)
    for i, value in enumerate(campus.hourly_precip or []):
        if not value:
            continue
        h = max(RAIN_H * (value / 100.0), 3.0)
        x = _x(i, count) - bar_w / 2
        parts.append(
            f'<rect x="{x:.1f}" y="{RAIN_TOP + RAIN_H - h:.1f}" '
            f'width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{RAIN}"/>'
        )

    # --- zaman ekseni ---
    for i, iso in enumerate(campus.hourly_time):
        h = _hour(iso)
        if h % 3:
            continue
        parts.append(
            f'<text x="{_x(i, count):.1f}" y="{AXIS_Y}" class="ct-axis" '
            f'text-anchor="middle">{h:02d}</text>'
        )

    # --- su an ---
    if now is not None:
        nx = _x(now.hour + now.minute / 60 - 0.5, count)
        if PAD_L < nx < W - PAD_R:
            parts.append(
                f'<line x1="{nx:.1f}" y1="{TEMP_TOP - 12}" x2="{nx:.1f}" '
                f'y2="{RAIN_TOP + RAIN_H:.0f}" stroke="currentColor" '
                f'stroke-width="1.5" opacity="0.32" stroke-dasharray="4 4"/>'
            )

    parts.append("</svg>")
    return "".join(parts)
