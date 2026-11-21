"""KOU yerleske hava durumu -> Instagram carousel otomasyonu.

Kullanim:
  python src/main.py --dry-run        # sadece gorselleri uret
  python src/main.py                  # uret + Instagram'a paylas
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

import caption as caption_mod  # noqa: E402
import render as render_mod  # noqa: E402
import weather as weather_mod  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "campuses.json"
OUTPUT_ROOT = ROOT / "output"


def force_utf8_stdout() -> None:
    """Windows konsolu cp1254 oldugu icin emoji/Turkce karakter patlamasin."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace",
                               line_buffering=True)
        except (AttributeError, ValueError):
            pass


def load_dotenv(path: Path) -> None:
    """Basit .env yukleyici (ek bagimlilik yok)."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KOÜ yerleşke hava durumu otomasyonu")
    parser.add_argument("--dry-run", action="store_true",
                        help="Sadece görselleri üret, paylaşma")
    parser.add_argument("--publish-only", action="store_true",
                        help="Üretimi atla, diskteki görselleri paylaş")
    parser.add_argument("--date", help="YYYY-MM-DD (varsayılan: bugün)")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--outdir", default=str(OUTPUT_ROOT))
    parser.add_argument("--base-url", default=os.environ.get("IMAGE_BASE_URL", ""),
                        help="Görsellerin servis edildiği public kök URL")
    return parser.parse_args()


def main() -> int:
    force_utf8_stdout()
    load_dotenv(ROOT / ".env")
    args = parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    timezone = config.get("timezone", "Europe/Istanbul")

    if args.date:
        day = dt.date.fromisoformat(args.date)
    else:
        day = dt.datetime.now(ZoneInfo(timezone)).date()

    outdir = Path(args.outdir) / day.isoformat()

    if args.publish_only:
        paths = sorted(outdir.glob("*.png"))
        caption_file = outdir / "caption.txt"
        if not paths or not caption_file.exists():
            print(f"HATA: {outdir} içinde hazır görsel/caption yok.", file=sys.stderr)
            return 2
        text = caption_file.read_text(encoding="utf-8")
        print(f"[1/2] Diskteki {len(paths)} görsel kullanılacak ({outdir})")
    else:
        campus_defs = config["campuses"]
        print(f"[1/4] Hava durumu çekiliyor ({len(campus_defs)} yerleşke)...")
        campuses = weather_mod.fetch(campus_defs, timezone=timezone)
        for c in campuses:
            print(f"      {c.name:<14} {c.description:<24} "
                  f"{c.temp_min and round(c.temp_min)}° / "
                  f"{c.temp_max and round(c.temp_max)}°")

        print(f"[2/4] Görseller üretiliyor -> {outdir}")
        paths = render_mod.render(campuses, day, config, outdir)
        for p in paths:
            print(f"      {p.name}")

        print("[3/4] Açıklama hazırlanıyor")
        text = caption_mod.build(campuses, day)
        (outdir / "caption.txt").write_text(text, encoding="utf-8")
        print("      " + text.splitlines()[0])

    if args.dry_run:
        print("[4/4] --dry-run: paylaşım atlandı.")
        print(f"\nGörseller hazır: {outdir}")
        return 0

    base_url = args.base_url.rstrip("/")
    if not base_url:
        print("[4/4] HATA: IMAGE_BASE_URL tanımlı değil, paylaşım yapılamaz.",
              file=sys.stderr)
        return 2

    import instagram as ig_mod

    image_urls = [f"{base_url}/{day.isoformat()}/{p.name}" for p in paths]
    print("[4/4] Görsellerin erişilebilirliği doğrulanıyor")
    for url in image_urls:
        ig_mod.wait_for_public_url(url)
        print(f"      OK {url}")

    publisher = ig_mod.InstagramPublisher()
    media_id = publisher.publish_carousel(image_urls, text)
    print(f"\nYayınlandı. media_id={media_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
