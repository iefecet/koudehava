# KOÜ Yerleşke Hava Durumu → Instagram

Kocaeli Üniversitesi'nin 18 yerleşkesinin hava durumunu her sabah otomatik olarak
Instagram'da **carousel** gönderi olarak paylaşan otomasyon.

- **Veri:** [Open-Meteo](https://open-meteo.com) (ücretsiz, API anahtarı gerektirmez)
- **Görsel:** HTML + CSS şablon → Playwright ile 1080×1350 PNG
- **Tema:** açık (varsayılan) veya koyu; hava durumuna göre değişen palet
- **Paylaşım:** Instagram Graph API (resmî Content Publishing API)
- **Zamanlama:** GitHub Actions cron, her gün 06:30 (TR)

---

## Nasıl çalışıyor

```
Open-Meteo (tek istek, 18 konum)
        ↓
HTML şablon → Playwright → 10 adet PNG
   • 00-ozet.png        tüm yerleşkelerin özeti
   • 01..09-<yerleşke>  seçili 9 yerleşkenin detayı
        ↓
PNG'ler repoya commit edilir → raw.githubusercontent.com'dan public URL
        ↓
Instagram Graph API: her görsel için container → carousel → publish
```

Instagram görselleri **kendi sunucularından çeker**, bu yüzden dosyaların public bir
URL'de olması zorunludur. Ekstra bir servise (Cloudinary vb.) üye olmamak için
görseller repoya yazılıp `raw.githubusercontent.com` üzerinden sunuluyor.

> **Not:** Instagram carousel en fazla **10 slayt** kabul eder. 18 yerleşkenin
> hepsi 1. slayttaki özet tablosunda yer alır; hangi 9 yerleşkenin kendi
> slaytını alacağı `config/campuses.json` içindeki `"carousel": true` ile belirlenir.

---

## Logolar

**KOÜ'de Hava** amblemi: beyaz zeminli dairesel rozet, koyu yeşil halka,
konturlu bulut, turuncu güneş ve altta yerleşke silueti.

| Dosya | Ne işe yarar |
|---|---|
| `assets/logo-koudehava.svg` | **Ana rozet** — yazılı (kaynak dosya) |
| `assets/logo-koudehava-mark.svg` | **Yazısız varyant** — küçük boyutlar |
| `assets/profil-1080.png` | Instagram profil fotoğrafı |
| `assets/logo-yazili-1080.png` | Rozet + "Yerleşke hava durumu" alt başlığı |
| `assets/logo-mark-1080.png` | Yazısız varyant, büyük |
| `assets/logo-256.png` | Yazısız varyant, küçük |

Gönderilerin üst barında **yazısız varyant** kullanılıyor: rozet orada 72 px'e
düşüyor ve içindeki "KOÜ'de Hava" yazısı okunmuyor — zaten hemen yanında
dizgiyle yazılıyor.

PNG'leri yeniden üretmek için:

```powershell
python scripts/make_logo.py
```

### Amblemi değiştirmek

`assets/konseptler/` altında dört alternatif var:

| Dosya | Konsept |
|---|---|
| `amblem-d-rozet.svg` | Dairesel rozet, yerleşke silueti *(kullanımda)* |
| `amblem-a-tepeler.svg` | Umuttepe + Kartepe silüeti, kar örtüsü |
| `amblem-b-ruzgargulu.svg` | Meteoroloji pusulası |
| `amblem-c-korfez.svg` | İzmit Körfezi ve gün doğumu |

Başka birine geçmek için üzerine kopyalayıp PNG'leri yenile:

```powershell
Copy-Item assets/konseptler/amblem-b-ruzgargulu.svg assets/logo-koudehava.svg -Force
```

```powershell
python scripts/make_logo.py
```

> Rozetin içindeki yazı canlı metindir (Plus Jakarta Sans). Görseller bu fontu
> yükleyen bir sayfada üretildiği için doğru çıkar; SVG'yi font yüklenmeyen bir
> ortamda açarsan yazı sistem fontuna düşer.

### Resmî Kocaeli Üniversitesi logosu

`assets/logo-kou.png` olarak ekli (184×184, şeffaf arka plan) ve gönderilerin
sol üstüne otomatik basılıyor. Değiştirmek istersen aynı klasöre şu adlardan
biriyle koyman yeterli, kod değişikliği gerekmez:

```
assets/logo-kou.svg   (tercih edilen — her ölçekte net)
assets/logo-kou.png
assets/logo-kou.jpg
```

Dosya silinirse yerine "KOÜ" yazan bir rozet basılır, otomasyon durmaz.
Şeffaf arka planlı bir sürüm kullan; koyu temaya geçersen logonun arkasına
otomatik olarak beyaz bir altlık konur.

> Vektörel (SVG) sürümünü bulabilirsen onu tercih et: mührün halka yazısı
> küçük boyutta çok daha net çıkar.

---

## Kurulum

### 1. Yerel test (Instagram'sız)

```powershell
pip install -r requirements.txt
```

```powershell
python -m playwright install chromium
```

```powershell
python src/main.py --dry-run
```

Görseller `output/YYYY-MM-DD/` altına, açıklama metni aynı klasörde
`caption.txt` olarak yazılır. Instagram'a hiçbir şey gönderilmez.

### 2. Hangi yol?

Meta'nın iki ayrı Instagram API yolu var. İkisi de gönderi paylaşabiliyor:

| | Instagram Login | Facebook Login |
|---|---|---|
| Facebook sayfası | **gerekmiyor** | zorunlu |
| Gönderi paylaşma | ✓ | ✓ |
| Hashtag arama, reklam | ✗ | ✓ |
| Uç nokta | `graph.instagram.com` | `graph.facebook.com` |

Bu otomasyon sadece gönderi paylaşıyor, bu yüzden **Instagram Login** yeterli —
Facebook sayfası açmana gerek kalmıyor. Kod ikisini de destekliyor ve
`setup_instagram.py` token'a bakıp hangisi olduğunu kendisi anlıyor.

### 3. Instagram hesabını hazırla

1. **Profesyonel hesap** yap: Ayarlar → Hesap türü ve araçlar → Profesyonel hesaba geç
   (Business veya Creator).
2. Hesap **herkese açık** olmalı — gizli hesaplar Meta paneline eklenemiyor.
3. Profil fotoğrafı olarak `assets/profil-1080.png` dosyasını yükleyebilirsin.

*(Facebook Login yolunu seçtiysen ayrıca bir Facebook Sayfası oluşturup
Instagram → Ayarlar → Sayfa bağlantısı adımını tamamla.)*

### 4. Meta uygulaması ve token

[developers.facebook.com/apps](https://developers.facebook.com/apps) → sağ üstten
**Create App**, sonra sırayla:

| Adım | Seçim |
|---|---|
| Connect a business | Bir işletme seç (doğrulama sonradan yapılabilir) |
| Use case | **Other** |
| App type | **Business** — Instagram ürünü yalnızca bu türe eklenebiliyor |
| Details | Uygulama adı + iletişim e-postası |

Uygulama açıldıktan sonra ürün listesinde **Instagram** → **Set up**. Bu,
"API setup with Instagram login" bölümünü ekler. *(Panelde bu başlık bazen
"API setup with Instagram business login" olarak görünüyor — ikisi aynı şey.)*

Sonra o bölümde:

1. **Generate access tokens** altında Instagram hesabını ekle.
2. Hesabın yanındaki **Generate token** düğmesine bas, Instagram'a giriş yap,
   çıkan token'ı kopyala.
3. İzinler — Instagram Login yolu için gerekli olanlar:
   `instagram_business_basic` ve `instagram_business_content_publish`.

> **Token'ı uzatmana gerek yok.** Panelden üretilen token zaten uzun ömürlü:
> 60 gün geçerli. (Kısa ömürlü olan, Business Login akışıyla alınan 1 saatlik
> token; bizim kullandığımız o değil.)

> **App Review gerekiyor mu?** Kendi hesabın için hayır. Meta'nın belgesi
> *"If your app only serves your Instagram professional account or an account
> you manage, Standard Access is all your app needs"* diyor. Başkasının hesabına
> paylaşım yapacaksan Advanced Access ve inceleme gerekiyor. Not: panelin
> uygulama oluşturma akışında bunun tersini ima eden bir uyarı da çıkabiliyor;
> takılırsan önce Standard Access ile dene, kendi hesabında çalışması gerekir.

> **Panel "Unified Login" diyorsa:** Yeni açılan uygulamalarda Meta,
> "API setup with Instagram login" yerine **Unified Login**'e yönlendiriyor.
> Bu da Facebook Sayfası istemiyor — Instagram hesabı doğrudan *business asset*
> olarak bağlanıyor. Sadece izin adları farklı oluyor:
> `instagram_basic` ve `instagram_content_publish`
> (`instagram_business_*` değil). Betikler iki adlandırmayı da tanıyor.
>
> Bu kurulumda **"2. Generate access tokens"** bölümündeki hesabın yanında
> görünen uzun sayı zaten `IG_USER_ID`'dir; ayrıca aramana gerek yok.

Token'ı aldıktan sonra gerisi otomatik — `IG_USER_ID`'yi elle aramana gerek yok:

```powershell
python scripts/setup_instagram.py EAAG...
```

Betik önce Instagram Login yolunu dener, olmazsa Facebook sayfalarını tarar;
bulduğu hesabı ve doğru `GRAPH_BASE` değerini `.env` dosyasına yazar.

### 5. Kurulumu doğrula

```powershell
python scripts/preflight.py
```

Yapılandırmadan Playwright'a, token süresinden izinlere kadar her şeyi kontrol
eder ve eksikleri tek tek söyler. Hiçbir şey paylaşmaz.

### 6. GitHub Actions'a al

1. Projeyi bir GitHub reposuna gönder. Repo **public** olmalı —
   `raw.githubusercontent.com` URL'lerine Instagram'ın erişmesi gerekiyor.

   ```powershell
   git init; git add -A; git commit -m "KOÜ'de Hava otomasyonu"
   ```

   ```powershell
   git remote add origin https://github.com/KULLANICI/koudehava.git; git push -u origin main
   ```

2. Repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - `IG_USER_ID`
   - `IG_ACCESS_TOKEN`
3. Settings → Actions → General → Workflow permissions →
   **Read and write permissions** (görselleri commit edebilmek için).
4. Actions sekmesi → `Günlük hava durumu paylaşımı` → **Run workflow**.
   İlk denemede `dry_run` kutusunu işaretle: üretir, paylaşmaz.
   Sonucu Artifacts bölümünden indirip kontrol edebilirsin.
5. Her şey yolundaysa `dry_run` işaretsiz bir kez daha çalıştır — ilk gönderi gider.

Bundan sonra her gün 06:30'da (TR) otomatik paylaşılır.

> `.env` dosyası `.gitignore`'da; token'lar repoya gitmez. GitHub Actions
> değerleri Secrets'tan okur, `IMAGE_BASE_URL`'i ise kendisi hesaplar.

---

## Komutlar

| Komut | Ne yapar |
|---|---|
| `python src/main.py --dry-run` | Sadece görsel + caption üretir |
| `python src/main.py` | Üretir ve Instagram'a paylaşır |
| `python src/main.py --publish-only` | Diskteki hazır görselleri paylaşır |
| `python src/main.py --date 2026-11-25` | Belirli bir gün için üretir |
| `python scripts/setup_instagram.py EAAG...` | IG_USER_ID'yi bulup `.env`'e yazar |
| `python scripts/preflight.py` | Kurulumu baştan sona doğrular |
| `python scripts/check_token.py` | Token süresini gösterir |
| `python scripts/make_logo.py` | Logo PNG'lerini üretir |

---

## Özelleştirme

| Ne | Nerede |
|---|---|
| **Açık / koyu tema** | `config/campuses.json` → `"theme": "light"` ya da `"dark"` |
| Yerleşke ekle/çıkar, koordinat düzelt | `config/campuses.json` |
| Hangi yerleşke kendi slaytını alsın | `config/campuses.json` → `"carousel": true` |
| Özet slaytını kapat | `config/campuses.json` → `carousel.include_summary_slide` |
| Tasarım, renkler, yerleşim | `src/templates/*.html` |
| Renk paletleri (hava tipi başına) | `src/theme.py` → `LIGHT` / `DARK` |
| Hava durumu ikonları | `src/icons.py` |
| Marka adı, alt başlık, kullanıcı adı | `config/campuses.json` → `account` |
| KOÜ'de Hava amblemi | `assets/logo-koudehava.svg` |
| Gönderi metni ve hashtag'ler | `src/caption.py` |
| Paylaşım saati | `.github/workflows/daily.yml` → `cron` |

Koordinatlar ilçe/mahalle merkezi seviyesindedir; Open-Meteo'nun grid çözünürlüğü
1–11 km olduğu için hava durumu açısından yeterlidir. Daha hassas istersen Google
Maps'te sağ tık → koordinatı kopyala ile `lat`/`lon` değerlerini güncelle.

---

## Bakım

- **Token ~60 günde bir dolar.** `scripts/check_token.py` kalan günü söyler; dolmadan
  Access Token Tool'dan yenileyip GitHub Secret'ı güncelle.
- `output/` klasörü her gün büyür. İstersen workflow'a eski klasörleri silen bir
  adım ekleyebilirsin; görseller ayrıca 14 gün artifact olarak da saklanıyor.
- Instagram API sürümü `GRAPH_VERSION` ile değiştirilebilir (varsayılan `v26.0`).
