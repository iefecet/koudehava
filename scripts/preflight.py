"""Ilk gonderiden once her seyin dogru kuruldugunu kontrol eder.

  python scripts/preflight.py

Hicbir sey paylasmaz; sadece okur ve rapor eder.
Cikis kodu 0 ise sistem paylasima hazir demektir.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from main import force_utf8_stdout, load_dotenv  # noqa: E402

OK, FAIL, WARN = "✓", "✗", "!"

results: list[tuple[str, str, str]] = []


def record(status: str, title: str, detail: str = "") -> None:
    results.append((status, title, detail))
    line = f"  {status} {title}"
    print(line if not detail else f"{line}\n      {detail}")


def check_config() -> dict | None:
    path = ROOT / "config" / "campuses.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        record(FAIL, "Yapılandırma okunamadı", str(exc))
        return None

    campuses = config.get("campuses", [])
    carousel = [c for c in campuses if c.get("carousel")]
    slides = len(carousel) + (1 if config.get("carousel", {})
                              .get("include_summary_slide", True) else 0)
    detail = f"{len(campuses)} yerleşke, {slides} slayt, tema: {config.get('theme')}"

    if slides > 10:
        record(FAIL, "Slayt sayısı", f"{slides} slayt — Instagram en fazla 10 kabul eder")
    elif slides < 2:
        record(FAIL, "Slayt sayısı", f"{slides} slayt — carousel en az 2 ister")
    else:
        record(OK, "Yapılandırma", detail)
    return config


def check_weather(config: dict) -> None:
    import weather

    campuses = config.get("campuses", [])[:2]
    try:
        data = weather.fetch(campuses, timezone=config.get("timezone", "Europe/Istanbul"))
    except Exception as exc:
        record(FAIL, "Open-Meteo erişimi", str(exc))
        return
    sample = data[0]
    record(OK, "Open-Meteo erişimi",
           f"{sample.name}: {sample.description}, "
           f"{sample.temp_min:.0f}° / {sample.temp_max:.0f}°")


def check_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        record(FAIL, "Playwright", "pip install -r requirements.txt")
        return
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception as exc:
        record(FAIL, "Playwright tarayıcısı",
               f"python -m playwright install chromium  ({exc})")
        return
    record(OK, "Playwright tarayıcısı", "chromium hazır")


def check_logos() -> None:
    assets = ROOT / "assets"
    kou = [n for n in ("logo-kou.svg", "logo-kou.png", "logo-kou.jpg")
           if (assets / n).exists()]
    if kou:
        record(OK, "Resmî KOÜ logosu", kou[0])
    else:
        record(WARN, "Resmî KOÜ logosu",
               "assets/logo-kou.* yok — yerine 'KOÜ' rozeti basılacak")

    if (assets / "logo-koudehava-mark.svg").exists():
        record(OK, "KOÜ'de Hava amblemi", "logo-koudehava-mark.svg")
    else:
        record(WARN, "KOÜ'de Hava amblemi", "yazısız varyant bulunamadı")


def check_instagram() -> str | None:
    import os

    token = os.environ.get("IG_ACCESS_TOKEN", "")
    user_id = os.environ.get("IG_USER_ID", "")

    if not token:
        record(FAIL, "IG_ACCESS_TOKEN", ".env dosyasında tanımlı değil")
        return None
    if not user_id:
        record(FAIL, "IG_USER_ID",
               "tanımlı değil — python scripts/setup_instagram.py")
        return None

    import instagram as ig_mod

    try:
        publisher = ig_mod.InstagramPublisher()
    except ig_mod.InstagramError as exc:
        record(FAIL, "Instagram ayarları", str(exc))
        return None

    yol = "Instagram Login" if publisher.is_instagram_login else "Facebook Login"
    record(OK, "Bağlantı yolu", f"{yol} ({publisher.base})")

    # token gecerliligi ve izinler — yalnizca Facebook yolunda sorgulanabilir
    try:
        data = publisher.debug_token().get("data", {})
    except ig_mod.TokenInspectionUnsupported:
        record(WARN, "Token süresi",
               "sorgulanamıyor (system-user token kendini inceleyemez). "
               "Bu tür token'ların süresi dolmaz; "
               "sorgulamak istersen .env'e IG_APP_ID + IG_APP_SECRET ekle")
        data = None
    except ig_mod.InstagramError as exc:
        record(FAIL, "Token doğrulama", str(exc))
        return None

    if data is None:
        pass
    elif not data.get("is_valid"):
        record(FAIL, "Token geçerliliği", "token geçersiz — yenile")
        return None

    expires = (data or {}).get("expires_at") or 0
    if expires:
        when = dt.datetime.fromtimestamp(expires, dt.timezone.utc)
        days = (when - dt.datetime.now(dt.timezone.utc)).days
        status = OK if days >= 14 else WARN
        record(status, "Token süresi", f"{days} gün kaldı ({when:%Y-%m-%d})")
    elif data is not None:
        record(OK, "Token süresi", "süresiz")

    if data is not None:
        scopes = set(data.get("scopes", []))
        # Izin adlari kuruluma gore degisiyor:
        #   Unified / Facebook Login -> instagram_basic, instagram_content_publish
        #   Instagram Login          -> instagram_business_basic, ..._content_publish
        pairs = [
            ("temel erişim", {"instagram_basic", "instagram_business_basic"}),
            ("paylaşım", {"instagram_content_publish",
                          "instagram_business_content_publish"}),
        ]
        missing = [label for label, names in pairs if not (names & scopes)]
        if missing:
            record(FAIL, "İzinler", "eksik: " + ", ".join(missing))
        else:
            granted = sorted(
                s for s in scopes
                if s.startswith("instagram_") and
                ("basic" in s or "content_publish" in s)
            )
            record(OK, "İzinler", ", ".join(granted))

    # hesap erisilebilir mi
    try:
        me = publisher.get_account()
        record(OK, "Instagram hesabı", f"@{me.get('username')}")
    except ig_mod.InstagramError as exc:
        record(FAIL, "Instagram hesabı", str(exc))
        return None

    return user_id


def check_image_host() -> None:
    import os

    base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
    if not base:
        record(FAIL, "IMAGE_BASE_URL",
               "tanımlı değil — görseller public bir URL'den servis edilmeli")
        return

    if "raw.githubusercontent.com" in base and "/output" not in base:
        record(WARN, "IMAGE_BASE_URL",
               f"{base} — sonu /output ile bitmeli gibi görünüyor")
        return

    try:
        response = requests.head(base, timeout=20, allow_redirects=True)
        code = response.status_code
    except requests.RequestException as exc:
        record(FAIL, "IMAGE_BASE_URL erişimi", str(exc))
        return

    # 404 normal: kok dizin diye bir dosya yok, onemli olan sunucunun cevap vermesi
    if code < 500:
        record(OK, "IMAGE_BASE_URL", f"{base} (HTTP {code})")
    else:
        record(FAIL, "IMAGE_BASE_URL", f"{base} sunucu hatası verdi (HTTP {code})")


def main() -> int:
    force_utf8_stdout()
    load_dotenv(ROOT / ".env")

    print("KOÜ'de Hava — kurulum kontrolü\n")

    print("Üretim tarafı")
    config = check_config()
    if config:
        check_weather(config)
    check_playwright()
    check_logos()

    print("\nPaylaşım tarafı")
    check_instagram()
    check_image_host()

    failures = [r for r in results if r[0] == FAIL]
    warnings = [r for r in results if r[0] == WARN]

    print("\n" + "─" * 52)
    if failures:
        print(f"{len(failures)} sorun var, paylaşım yapılamaz:")
        for _, title, _detail in failures:
            print(f"  ✗ {title}")
        return 1

    if warnings:
        print(f"Hazır ({len(warnings)} uyarı ile).")
    else:
        print("Her şey hazır.")
    print("\nDeneme:  python src/main.py --dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
