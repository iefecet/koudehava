"""IG_USER_ID'yi erisim token'indan otomatik bulup .env'e yazar.

  python scripts/setup_instagram.py                 # .env icindeki token ile
  python scripts/setup_instagram.py EAAG...         # token'i dogrudan vererek
  python scripts/setup_instagram.py --page-id 123   # birden fazla sayfa varsa

Token'in hangi yola ait oldugunu kendisi anlar:
  • Instagram Login  -> graph.instagram.com/me        (Facebook sayfasi gerekmez)
  • Facebook Login   -> graph.facebook.com/me/accounts -> sayfalar -> IG hesabi
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from main import force_utf8_stdout, load_dotenv  # noqa: E402

ENV_PATH = ROOT / ".env"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Instagram kullanıcı ID'sini bulur")
    ap.add_argument("token", nargs="?", help="Uzun ömürlü erişim token'ı")
    ap.add_argument("--page-id", help="Birden fazla Facebook sayfası varsa hangisi")
    ap.add_argument("--write", action="store_true", default=True,
                    help="Bulunan değerleri .env dosyasına yaz (varsayılan)")
    ap.add_argument("--no-write", dest="write", action="store_false")
    return ap.parse_args()


def set_env_value(key: str, value: str) -> None:
    """.env icinde anahtari gunceller, yoksa ekler."""
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    else:
        example = ROOT / ".env.example"
        if example.exists():
            lines = example.read_text(encoding="utf-8").splitlines()

    found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}=") and not stripped.startswith("#"):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    force_utf8_stdout()
    load_dotenv(ENV_PATH)
    args = parse_args()

    import os

    token = args.token or os.environ.get("IG_ACCESS_TOKEN", "")
    if not token:
        print(
            "HATA: Token yok.\n"
            "  python scripts/setup_instagram.py EAAG...\n"
            "ya da .env dosyasına IG_ACCESS_TOKEN=... satırını ekle.",
            file=sys.stderr,
        )
        return 2

    version = os.environ.get("GRAPH_VERSION", "v26.0")
    base = os.environ.get("GRAPH_BASE", "").rstrip("/")

    # Hesap ID'si zaten elimizdeyse (orn. Unified Login kurulumunda panelde
    # yaziyor) en guvenilir yontem: iki sunucuyu da bu ID ile sinamak.
    known_id = os.environ.get("IG_USER_ID", "").strip()
    if known_id and not base:
        print(f"Hesap ID'si biliniyor ({known_id}); sunucular sınanıyor …")
        for host in ("https://graph.facebook.com", "https://graph.instagram.com"):
            probe = requests.get(
                f"{host}/{version}/{known_id}",
                params={"fields": "username", "access_token": token},
                timeout=30,
            ).json()
            if "error" not in probe:
                username = probe.get("username", "?")
                print(f"  ✓ {host} → @{username}")
                if args.write:
                    set_env_value("GRAPH_BASE", host)
                    if args.token:
                        set_env_value("IG_ACCESS_TOKEN", args.token)
                    print(f".env güncellendi: {ENV_PATH}")
                    print()
                    print("Sıradaki adım:  python scripts/preflight.py")
                else:
                    print()
                    print(f"GRAPH_BASE={host}")
                return 0
            message = (probe.get("error") or {}).get("message", "")
            print(f"  ✗ {host} → {message}")
        print()
        print("Hiçbir sunucu bu token'ı kabul etmedi; token'ı kontrol et.",
              file=sys.stderr)
        return 1

    # Once yeni yolu dene: Instagram Login token'i ise Facebook sayfasi hic gerekmez.
    if not base or "graph.instagram.com" in base:
        print(f"Instagram Login yolu deneniyor (graph.instagram.com/{version}) …")
        ig_login = requests.get(
            f"https://graph.instagram.com/{version}/me",
            params={"fields": "user_id,username", "access_token": token},
            timeout=30,
        ).json()

        if "error" not in ig_login:
            ig_id = str(ig_login.get("user_id") or ig_login.get("id") or "")
            username = ig_login.get("username", "?")
            if ig_id:
                print()
                print(f"Instagram Login token'ı. Hesap: @{username} (id {ig_id})")
                if args.write:
                    set_env_value("IG_USER_ID", ig_id)
                    set_env_value("GRAPH_BASE", "https://graph.instagram.com")
                    if args.token:
                        set_env_value("IG_ACCESS_TOKEN", args.token)
                    print(f".env güncellendi: {ENV_PATH}")
                    print()
                    print("Sıradaki adım:  python scripts/preflight.py")
                else:
                    print()
                    print(f"IG_USER_ID={ig_id}")
                    print("GRAPH_BASE=https://graph.instagram.com")
                return 0

        if base:
            message = (ig_login.get("error") or {}).get("message")
            print(f"Graph API hatası: {message}", file=sys.stderr)
            return 1
        print("  (Instagram Login token'ı değil, Facebook yolu deneniyor)")

    base = base or "https://graph.facebook.com"
    print(f"Sayfalar sorgulanıyor ({base}/{version}) …")
    response = requests.get(
        f"{base}/{version}/me/accounts",
        params={
            "fields": "id,name,instagram_business_account{id,username}",
            "access_token": token,
        },
        timeout=30,
    )
    payload = response.json()

    if "error" in payload:
        error = payload["error"]
        print(f"\nGraph API hatası: {error.get('message')}", file=sys.stderr)
        print(
            "\nSık karşılaşılanlar:\n"
            "  • Token süresi dolmuş → Access Token Tool'dan yenile\n"
            "  • pages_show_list izni yok → Graph API Explorer'dan izni ekle\n"
            "  • Token bir Sayfa token'ı → Kullanıcı token'ı kullanman gerekiyor",
            file=sys.stderr,
        )
        return 1

    pages = payload.get("data", [])
    if not pages:
        print(
            "Bu token'a bağlı Facebook sayfası bulunamadı.\n"
            "Instagram hesabının bir Facebook sayfasına bağlı olduğundan ve\n"
            "token'da pages_show_list izni olduğundan emin ol.",
            file=sys.stderr,
        )
        return 1

    print(f"\n{len(pages)} sayfa bulundu:\n")
    linked = []
    for page in pages:
        ig = page.get("instagram_business_account") or {}
        mark = "✓" if ig else "—"
        username = f"@{ig['username']}" if ig.get("username") else "Instagram bağlı değil"
        print(f"  {mark} {page.get('name')}")
        print(f"      sayfa id : {page.get('id')}")
        print(f"      instagram: {username}"
              + (f"  (id {ig['id']})" if ig.get("id") else ""))
        if ig.get("id"):
            linked.append((page, ig))

    if not linked:
        print(
            "\nHiçbir sayfaya Instagram profesyonel hesabı bağlı değil.\n"
            "Instagram → Ayarlar → Sayfa bağlantısı adımını tamamla.",
            file=sys.stderr,
        )
        return 1

    if args.page_id:
        linked = [(p, ig) for p, ig in linked if p.get("id") == args.page_id]
        if not linked:
            print(f"\n--page-id {args.page_id} bulunamadı.", file=sys.stderr)
            return 1

    if len(linked) > 1:
        print(
            "\nBirden fazla bağlı hesap var. Hangisini kullanacağını seç:\n"
            "  python scripts/setup_instagram.py --page-id <sayfa id>",
            file=sys.stderr,
        )
        return 1

    page, ig = linked[0]
    ig_id = ig["id"]
    print(f"\nKullanılacak hesap: @{ig.get('username')} (id {ig_id})")

    if args.write:
        set_env_value("IG_USER_ID", ig_id)
        set_env_value("GRAPH_BASE", "https://graph.facebook.com")
        if args.token:
            set_env_value("IG_ACCESS_TOKEN", args.token)
        print(f".env güncellendi: {ENV_PATH}")
        print("\nSıradaki adım:  python scripts/preflight.py")
    else:
        print(f"\nIG_USER_ID={ig_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
