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


def write_workflow_time(time_hhmm: str) -> bool:
    """Workflow cron'unu gunceller. Degisiklik olduysa True doner."""
    if not WORKFLOW_PATH.exists():
        return False
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    cron = tr_time_to_cron(time_hhmm)
    new_text, count = re.subn(r'(- cron:\s*")[^"]+(")',
                              lambda m: m.group(1) + cron + m.group(2),
                              text, count=1)
    if count and new_text != text:
        # yorum satirindaki saat aciklamasi da guncellensin
        new_text = re.sub(
            r"#.*=.*Türkiye saati.*\n",
            f"# {cron.split()[1]}:{int(cron.split()[0]):02d} UTC = "
            f"{time_hhmm} Türkiye saati (TR yıl boyunca UTC+3)\n",
            new_text, count=1)
        WORKFLOW_PATH.write_text(new_text, encoding="utf-8")
        return True
    return False
