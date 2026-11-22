"""Ayarlarin okunmasi/yazilmasi: config, .env ve workflow cron'u.

Arayuz (scripts/ayarlar.py) ve betikler ayni mantigi kullansin diye
burada toplandi.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "campuses.json"
ENV_PATH = ROOT / ".env"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily.yml"

# Turkiye yil boyunca UTC+3 (yaz saati uygulamasi yok)
TR_UTC_OFFSET = 3


# ---------------------------------------------------------------- config

def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# ------------------------------------------------------------------- env

def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def save_env(values: dict[str, str]) -> None:
    """Var olan yorumlari ve sirayi koruyarak gunceller."""
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    seen: set[str] = set()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.partition("=")[0].strip()
        if key in values:
            lines[i] = f"{key}={values[key]}"
            seen.add(key)

    for key, value in values.items():
        if key not in seen:
            lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -------------------------------------------------------------- zamanlama

def tr_time_to_cron(time_hhmm: str) -> str:
    """'06:30' -> '30 3 * * *' (UTC)."""
    hour, _, minute = time_hhmm.partition(":")
    h = int(hour) % 24
    m = int(minute or 0) % 60
    return f"{m} {(h - TR_UTC_OFFSET) % 24} * * *"


def cron_to_tr_time(cron: str) -> str:
    """'30 3 * * *' -> '06:30'."""
    parts = cron.split()
    if len(parts) < 2:
        return "06:30"
    try:
        m, h = int(parts[0]), int(parts[1])
    except ValueError:
        return "06:30"
    return f"{(h + TR_UTC_OFFSET) % 24:02d}:{m:02d}"


def read_workflow_time() -> str:
    if not WORKFLOW_PATH.exists():
        return "06:30"
    match = re.search(r'- cron:\s*"([^"]+)"',
                      WORKFLOW_PATH.read_text(encoding="utf-8"))
    return cron_to_tr_time(match.group(1)) if match else "06:30"


# Yedek calistirma, asil saatten bu kadar sonra denenir
BACKUP_DELAY_MINUTES = 50


def backup_time(time_hhmm: str) -> str:
    """Asil saatten BACKUP_DELAY_MINUTES sonrasi."""
    hour, _, minute = time_hhmm.partition(":")
    total = (int(hour) * 60 + int(minute or 0) + BACKUP_DELAY_MINUTES) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def write_workflow_time(time_hhmm: str) -> bool:
    """Workflow'daki asil ve yedek cron'u gunceller.

    GitHub'in zamanlayicisi gecikebildigi icin iki zaman tutuluyor; ayni
    gune ikinci gonderi cikmasini paylasim oncesi kontrol engelliyor.
    """
    if not WORKFLOW_PATH.exists():
        return False
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    backup = backup_time(time_hhmm)
    crons = [tr_time_to_cron(time_hhmm), tr_time_to_cron(backup)]
    times = [time_hhmm, backup]

    index = 0

    def swap_cron(match: re.Match) -> str:
        nonlocal index
        value = crons[index] if index < len(crons) else match.group(2)
        index += 1
        return match.group(1) + value + match.group(3)

    new_text = re.sub(r'(- cron:\s*")([^"]+)(")', swap_cron, text)

    # Yorumlardaki saat aciklamalari da guncellensin
    comment_index = 0

    def swap_comment(match: re.Match) -> str:
        nonlocal comment_index
        if comment_index >= len(crons):
            return match.group(0)
        cron = crons[comment_index]
        label = "# " if comment_index == 0 else "# yedek: "
        line = (f"{label}{int(cron.split()[1]):02d}:{int(cron.split()[0]):02d} "
                f"UTC = {times[comment_index]} Türkiye saati")
        if comment_index == 0:
            line += " (TR yıl boyunca UTC+3)"
        comment_index += 1
        return match.group(1) + line + "\n"

    new_text = re.sub(r"( *)#.*UTC = .*Türkiye saati.*\n", swap_comment, new_text)

    if new_text != text:
        WORKFLOW_PATH.write_text(new_text, encoding="utf-8")
        return True
    return False


# ------------------------------------------------------- gorsel barindirma

def git_remote_slug() -> str | None:
    """origin uzak adresinden 'kullanici/repo' cikarir."""
    import subprocess
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not url:
        return None
    url = url.removesuffix(".git")
    for prefix in ("https://github.com/", "git@github.com:",
                   "ssh://git@github.com/"):
        if url.startswith(prefix):
            return url[len(prefix):]
    return None


def current_branch() -> str:
    import subprocess
    try:
        name = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "main"
    return name or "main"


def derive_image_base_url() -> str | None:
    """Gorsellerin servis edilecegi raw URL kokunu uzak adresten turetir."""
    slug = git_remote_slug()
    if not slug:
        return None
    return f"https://raw.githubusercontent.com/{slug}/{current_branch()}/output"
