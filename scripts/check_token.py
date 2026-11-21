"""Instagram access token'in ne zaman dolacagini soyler.

  python scripts/check_token.py

Uzun omurlu token ~60 gun gecerlidir; suresi dolmadan yenilenmeli.
Cikis kodu 1 ise token 14 gunden az kalmistir (CI'da uyari icin kullanilabilir).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from main import force_utf8_stdout, load_dotenv  # noqa: E402

WARN_DAYS = 14


def main() -> int:
    force_utf8_stdout()
    load_dotenv(ROOT / ".env")

    from instagram import (  # noqa: E402
        InstagramError,
        InstagramPublisher,
        TokenInspectionUnsupported,
    )

    try:
        publisher = InstagramPublisher()
        data = publisher.debug_token().get("data", {})
    except TokenInspectionUnsupported:
        print("Bu bağlantı yolunda (Instagram Login) token inceleme uç noktası yok.")
        try:
            account = publisher.get_account()
            print(f"Hesap     : @{account.get('username')}")
            print("Durum     : token çalışıyor")
        except InstagramError as exc:
            print(f"HATA: {exc}", file=sys.stderr)
            return 2
        print()
        print("Instagram token'ları ~60 gün geçerlidir; süresi dolmadan yenile.")
        return 0
    except InstagramError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2

    print(f"Uygulama    : {data.get('application')}")
    print(f"Tür         : {data.get('type')}")
    print(f"Geçerli mi  : {data.get('is_valid')}")
    print(f"İzinler     : {', '.join(data.get('scopes', [])) or '-'}")

    expires = data.get("expires_at") or 0
    if expires == 0:
        print("Son kullanma: süresiz")
        return 0

    when = dt.datetime.fromtimestamp(expires, dt.timezone.utc)
    remaining = (when - dt.datetime.now(dt.timezone.utc)).days
    print(f"Son kullanma: {when:%Y-%m-%d %H:%M UTC} ({remaining} gün kaldı)")

    if remaining < WARN_DAYS:
        print(f"\nUYARI: Token {remaining} gün içinde dolacak, yenile.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
