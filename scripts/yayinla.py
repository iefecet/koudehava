"""Suanki ayarlarla hemen bir gonderi yayinlar.

  python scripts/yayinla.py              # uret, gorselleri push et, paylas
  python scripts/yayinla.py --kontrol    # sadece on kontrol, paylasma

Adimlar:
  1. Gorselleri ve aciklama metnini uretir
  2. Gorselleri repoya gonderir (Instagram public URL'den cektigi icin sart)
  3. URL'lerin gercekten erisilebilir oldugunu dogrular
  4. Carousel olarak paylasir

DIKKAT: 4. adim geri alinamaz; gonderi Instagram'dan elle silinebilir.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from main import force_utf8_stdout, load_dotenv  # noqa: E402
import settings_io as io  # noqa: E402


def run(args: list[str], must_succeed: bool = True) -> int:
    print("$ " + " ".join(args), flush=True)
    code = subprocess.call(args, cwd=str(ROOT))
    if code != 0 and must_succeed:
        raise SystemExit(f"Adım başarısız (çıkış {code}): {' '.join(args)}")
    return code


def preflight(image_base: str | None) -> list[str]:
    """Paylasimi engelleyecek sorunlari listeler."""
    problems: list[str] = []
    if not os.environ.get("IG_ACCESS_TOKEN"):
        problems.append("IG_ACCESS_TOKEN tanımlı değil")
    if not os.environ.get("IG_USER_ID"):
        problems.append("IG_USER_ID tanımlı değil")
    if not image_base:
        problems.append(
            "Görsel kök URL'i belirlenemedi (git remote 'origin' yok mu?)"
        )
    if io.git_remote_slug() is None:
        problems.append("GitHub uzak deposu bulunamadı")

    config = io.load_config()
    carousel = [c for c in config.get("campuses", []) if c.get("carousel")]
    slides = len(carousel) + (
        1 if config.get("carousel", {}).get("include_summary_slide", True) else 0
    )
    limit = int(config.get("carousel", {}).get("max_slides", 10))
    if slides < 2:
        problems.append(f"Carousel en az 2 slayt ister, {slides} var")
    if slides > limit:
        problems.append(f"{slides} slayt gerekiyor, sınır {limit}")
    return problems


def main() -> int:
    force_utf8_stdout()
    load_dotenv(ROOT / ".env")

    ap = argparse.ArgumentParser(description="Hemen gönderi yayınla")
    ap.add_argument("--kontrol", action="store_true",
                    help="Sadece ön kontrol yap, paylaşma")
    args = ap.parse_args()

    image_base = (os.environ.get("IMAGE_BASE_URL", "").strip()
                  or io.derive_image_base_url())

    problems = preflight(image_base)
    if problems:
        print("Paylaşım yapılamaz:", file=sys.stderr)
        for p in problems:
            print(f"  • {p}", file=sys.stderr)
        return 1

    config = io.load_config()
    tz = config.get("timezone", "Europe/Istanbul")
    day = dt.datetime.now(ZoneInfo(tz)).date()
    print(f"Görsel kök URL'i: {image_base}")

    if args.kontrol:
        print("Ön kontrol temiz — paylaşıma hazır.")
        return 0

    # 1) uret
    print("\n=== 1/4 · Görseller ve metin üretiliyor ===", flush=True)
    run([sys.executable, "src/main.py", "--dry-run"])

    # 2) gorselleri repoya gonder
    print("\n=== 2/4 · Görseller GitHub'a gönderiliyor ===", flush=True)
    folder = f"output/{day.isoformat()}"
    run(["git", "add", "-f", folder])
    committed = run(
        ["git", "-c", "core.safecrlf=false", "commit", "-m",
         f"Hava durumu görselleri: {day.isoformat()}"],
        must_succeed=False,
    ) == 0
    if not committed:
        print("  (görsellerde değişiklik yok, mevcut sürüm kullanılacak)")
    run(["git", "push", "origin", io.current_branch()])

    # 3-4) dogrula ve paylas
    print("\n=== 3/4 · URL doğrulama ve paylaşım ===", flush=True)
    env = dict(os.environ, IMAGE_BASE_URL=image_base)
    code = subprocess.call(
        [sys.executable, "src/main.py", "--publish-only"],
        cwd=str(ROOT), env=env,
    )
    if code != 0:
        print("\nPaylaşım başarısız.", file=sys.stderr)
        return code

    print("\n=== 4/4 · Tamam ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
