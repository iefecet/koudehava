"""Instagram Graph API ile carousel (cok gorselli) gonderi paylasir.

Akis (Meta'nin Content Publishing API'si):
  1) Her gorsel icin  POST /{ig-user-id}/media?is_carousel_item=true  -> container id
  2) POST /{ig-user-id}/media?media_type=CAROUSEL&children=...        -> carousel id
  3) POST /{ig-user-id}/media_publish?creation_id=...                 -> yayinla

Gorseller Instagram sunucularindan cekildigi icin PUBLIC bir URL'de olmalari sart.
"""

from __future__ import annotations

import os
import time

import requests

DEFAULT_BASE = "https://graph.facebook.com"
DEFAULT_VERSION = "v26.0"

# Meta'nin iki ayri yolu var:
#   graph.facebook.com  -> "Instagram API with Facebook Login" (Facebook sayfasi sart)
#   graph.instagram.com -> "Instagram API with Instagram Login" (sayfa gerekmez)
# Yayinlama akisi ikisinde de ayni; fark token turu ve izin adlarinda.
INSTAGRAM_LOGIN_BASE = "https://graph.instagram.com"


class InstagramError(RuntimeError):
    pass


class TokenInspectionUnsupported(InstagramError):
    """Bu yolda token inceleme ucnoktasi yok (Instagram Login)."""


class InstagramPublisher:
    def __init__(self, user_id: str | None = None, access_token: str | None = None,
                 base: str | None = None, version: str | None = None,
                 timeout: int = 60):
        self.user_id = user_id or os.environ.get("IG_USER_ID", "")
        self.access_token = access_token or os.environ.get("IG_ACCESS_TOKEN", "")
        self.base = (base or os.environ.get("GRAPH_BASE") or DEFAULT_BASE).rstrip("/")
        # Token incelemek icin gereken opsiyonel uygulama kimligi
        self.app_id = os.environ.get("IG_APP_ID", "")
        self.app_secret = os.environ.get("IG_APP_SECRET", "")
        self.retries = 3
        self.version = version or os.environ.get("GRAPH_VERSION") or DEFAULT_VERSION
        self.timeout = timeout

        if not self.user_id or not self.access_token:
            raise InstagramError(
                "IG_USER_ID ve IG_ACCESS_TOKEN tanimli degil. "
                ".env dosyasina ekle veya GitHub Secrets'ta tanimla."
            )

    @property
    def is_instagram_login(self) -> bool:
        """Instagram Login yolunda miyiz? (Facebook sayfasi gerektirmeyen yol)"""
        return "graph.instagram.com" in self.base

    # ---------- dahili yardimcilar ----------

    def _url(self, path: str) -> str:
        return f"{self.base}/{self.version}/{path.lstrip('/')}"

    def _send(self, method: str, path: str, params: dict, retry: bool) -> dict:
        """Gecici ag hatalarinda yeniden dener.

        DIKKAT: retry=True yalnizca tekrarlanmasi zararsiz cagrilar icindir.
        media_publish tekrarlanirsa ayni gonderi iki kez paylasilabilir;
        o yuzden orada asla kullanilmaz.
        """
        params = {"access_token": self.access_token, **params}
        url = self._url(path)
        attempts = self.retries if retry else 1
        last: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                if method == "POST":
                    response = requests.post(url, data=params, timeout=self.timeout)
                else:
                    response = requests.get(url, params=params, timeout=self.timeout)
                return self._handle(response)
            except (requests.Timeout, requests.ConnectionError) as exc:
                last = exc
                if attempt < attempts:
                    wait = 4.0 * attempt
                    print(f"      Graph API yanıt vermedi "
                          f"({exc.__class__.__name__}); {wait:.0f} sn sonra "
                          f"yeniden denenecek ({attempt}/{attempts - 1})")
                    time.sleep(wait)

        raise InstagramError(f"Graph API'ye ulaşılamadı: {last}") from last

    def _post(self, path: str, params: dict, retry: bool = False) -> dict:
        return self._send("POST", path, params, retry)

    def _get(self, path: str, params: dict) -> dict:
        return self._send("GET", path, params, retry=True)

    @staticmethod
    def _handle(response: requests.Response) -> dict:
        try:
            payload = response.json()
        except ValueError:
            raise InstagramError(
                f"Graph API beklenmeyen yanit ({response.status_code}): "
                f"{response.text[:400]}"
            ) from None
        if "error" in payload:
            error = payload["error"]
            raise InstagramError(
                f"Graph API hatasi [{error.get('code')}/"
                f"{error.get('error_subcode')}]: {error.get('message')}"
            )
        if not response.ok:
            raise InstagramError(f"Graph API {response.status_code}: {payload}")
        return payload

    # ---------- adimlar ----------

    def create_item(self, image_url: str) -> str:
        """Carousel icin tek bir gorsel container'i olusturur."""
        data = self._post(
            f"{self.user_id}/media",
            {"image_url": image_url, "is_carousel_item": "true"},
            retry=True,
        )
        container_id = data.get("id")
        if not container_id:
            raise InstagramError(f"Container id donmedi: {data}")
        return container_id

    def create_carousel(self, children: list[str], caption: str) -> str:
        data = self._post(
            f"{self.user_id}/media",
            {
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
            },
            retry=True,
        )
        container_id = data.get("id")
        if not container_id:
            raise InstagramError(f"Carousel id donmedi: {data}")
        return container_id

    def wait_until_ready(self, container_id: str, attempts: int = 30,
                         delay: float = 4.0) -> None:
        """Container FINISHED olana kadar bekler."""
        last = "?"
        for _ in range(attempts):
            data = self._get(container_id, {"fields": "status_code,status"})
            last = data.get("status_code", "?")
            if last == "FINISHED":
                return
            if last == "ERROR":
                raise InstagramError(
                    f"Container {container_id} hata verdi: {data.get('status')}"
                )
            time.sleep(delay)
        raise InstagramError(
            f"Container {container_id} {attempts * delay:.0f} sn icinde hazir olmadi "
            f"(son durum: {last})."
        )

    def publish(self, creation_id: str) -> str:
        data = self._post(
            f"{self.user_id}/media_publish", {"creation_id": creation_id}
        )
        media_id = data.get("id")
        if not media_id:
            raise InstagramError(f"Yayin id donmedi: {data}")
        return media_id

    # ---------- tek adimda ----------

    def publish_carousel(self, image_urls: list[str], caption: str) -> str:
        if not 2 <= len(image_urls) <= 10:
            raise InstagramError(
                f"Carousel 2-10 gorsel kabul eder, {len(image_urls)} verildi."
            )

        children: list[str] = []
        for index, url in enumerate(image_urls, start=1):
            print(f"  [{index}/{len(image_urls)}] container olusturuluyor: {url}")
            children.append(self.create_item(url))

        for child in children:
            self.wait_until_ready(child)

        print("  carousel container olusturuluyor")
        carousel_id = self.create_carousel(children, caption)
        self.wait_until_ready(carousel_id)

        print("  yayinlaniyor")
        return self.publish(carousel_id)

    # ---------- token bakimi ----------

    def get_account(self, fields: str | None = None) -> dict:
        """Bagli Instagram hesabinin bilgilerini dondurur."""
        if fields is None:
            fields = "username" if self.is_instagram_login else "username,name"
        return self._get(self.user_id, {"fields": fields})

    def debug_token(self) -> dict:
        """Token'in gecerliligi ve izinleri.

        Yalnizca Facebook Login yolunda vardir; Instagram Login yolunda
        graph.instagram.com boyle bir ucnokta sunmaz.
        """
        if self.is_instagram_login:
            raise TokenInspectionUnsupported(
                "Instagram Login yolunda token inceleme ucnoktasi yok."
            )
        if not (self.app_id and self.app_secret):
            # Sistem kullanici token'i kendini inceleyemez; Graph API burada
            # bir uygulama token'i ister.
            raise TokenInspectionUnsupported(
                "Token inceleme icin uygulama kimligi gerekiyor. "
                "Istersen .env icine IG_APP_ID ve IG_APP_SECRET ekle."
            )
        return self._get(
            "debug_token",
            {
                "input_token": self.access_token,
                "access_token": f"{self.app_id}|{self.app_secret}",
            },
        )


def wait_for_public_url(url: str, attempts: int = 20, delay: float = 6.0) -> None:
    """Gorselin public URL'den gercekten servis edildigini dogrular."""
    for attempt in range(1, attempts + 1):
        try:
            response = requests.head(url, timeout=20, allow_redirects=True)
            if response.status_code == 200:
                return
            if attempt == 1:
                response = requests.get(url, timeout=20, stream=True)
                if response.status_code == 200:
                    return
        except requests.RequestException:
            pass
        time.sleep(delay)
    raise InstagramError(
        f"Gorsel public URL'den erisilemedi: {url}\n"
        "Instagram gorselleri kendi sunucularindan ceker; URL erisilebilir olmali."
    )
