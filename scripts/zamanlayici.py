"""Bilgisayarda gunluk paylasim gorevi kurar (Windows Gorev Zamanlayici).

  python scripts/zamanlayici.py --durum     # mevcut gorevi goster
  python scripts/zamanlayici.py --kur       # gorevi kur / guncelle
  python scripts/zamanlayici.py --kaldir    # gorevi sil

Neden: GitHub Actions'in cron'u "en iyi caga" ile calisiyor ve bu depoda
saatlerce gecikebiliyor. Bilgisayar acikken bu gorev saati saatine calisir;
GitHub'daki zamanlama da yedek olarak durmaya devam eder. Ayni gune ikinci
gonderi cikmaz, cunku paylasim oncesi kontrol ediliyor.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from main import force_utf8_stdout  # noqa: E402
import settings_io as io  # noqa: E402

TASK_NAME = "KOUdeHava-GunlukPaylasim"
WRAPPER = ROOT / "scripts" / "gunluk_paylas.cmd"
LOG_DIR = ROOT / "output" / "_log"


def write_wrapper() -> Path:
    """Gorevin calistiracagi toplu is dosyasini olusturur."""
    python = Path(sys.executable)
    # pythonw varsa konsol penceresi acilmasin
    windowless = python.with_name("pythonw.exe")
    runner = windowless if windowless.exists() else python

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / "gunluk.log"

    WRAPPER.write_text(
        "@echo off\r\n"
        f'cd /d "{ROOT}"\r\n'
        f'echo [%date% %time%] baslatildi >> "{log}"\r\n'
        f'"{runner}" "{ROOT / "scripts" / "yayinla.py"}" >> "{log}" 2>&1\r\n'
        f'echo [%date% %time%] cikis=%errorlevel% >> "{log}"\r\n',
        encoding="utf-8",
    )
    return WRAPPER


def task_status() -> str | None:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout if result.returncode == 0 else None


def install(time_hhmm: str) -> int:
    wrapper = write_wrapper()
    print(f"Çalıştırılacak dosya: {wrapper}")
    print(f"Günlük kaydı        : {LOG_DIR / 'gunluk.log'}")

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", f'"{wrapper}"',
         "/SC", "DAILY", "/ST", time_hhmm, "/F"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print((result.stdout or result.stderr).strip())
    if result.returncode != 0:
        return result.returncode

    print(f"\nGörev kuruldu: her gün {time_hhmm} (bilgisayar saatiyle).")
    print("Bilgisayar o saatte kapalıysa görev çalışmaz; GitHub'daki")
    print("zamanlama yedek olarak devam ediyor.")
    return 0


def remove() -> int:
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print((result.stdout or result.stderr).strip())
    return result.returncode


def main() -> int:
    force_utf8_stdout()
    ap = argparse.ArgumentParser(description="Günlük paylaşım görevi")
    ap.add_argument("--kur", action="store_true", help="Görevi kur / güncelle")
    ap.add_argument("--kaldir", action="store_true", help="Görevi sil")
    ap.add_argument("--durum", action="store_true", help="Mevcut durumu göster")
    ap.add_argument("--saat", help="Paylaşım saati (varsayılan: ayarlardaki)")
    args = ap.parse_args()

    if sys.platform != "win32":
        print("Bu betik Windows Görev Zamanlayıcı içindir.", file=sys.stderr)
        return 2

    time_hhmm = args.saat or io.read_workflow_time()

    if args.kaldir:
        return remove()
    if args.kur:
        return install(time_hhmm)

    # varsayilan: durum
    status = task_status()
    if status:
        print("Görev kurulu:\n")
        for line in status.splitlines():
            if any(k in line for k in ("TaskName", "Görev Adı", "Next Run",
                                       "Sonraki", "Status", "Durum",
                                       "Last Run", "Son Ç")):
                print("  " + line.strip())
    else:
        print(f"Görev kurulu değil ({TASK_NAME}).")
        print(f"Kurmak için:  python scripts/zamanlayici.py --kur")
        print(f"Ayarlardaki paylaşım saati: {time_hhmm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
