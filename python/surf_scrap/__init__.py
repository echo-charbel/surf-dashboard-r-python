# surf_scrap/__init__.py

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
import requests


__all__ = ["scrape_surf_report"]  # => une seule fonction importable


# ----------------------------
# Helpers "privés" (non exportés)
# ----------------------------
_FR_WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
_FR_MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

# Directions (16 points) proches de ce que Surf-Report affiche (ex. "Sud Est", "Sud Sud Est", etc.)
_FR_COMPASS_16 = [
    "Nord", "Nord Nord Est", "Nord Est", "Est Nord Est",
    "Est", "Est Sud Est", "Sud Est", "Sud Sud Est",
    "Sud", "Sud Sud Ouest", "Sud Ouest", "Ouest Sud Ouest",
    "Ouest", "Ouest Nord Ouest", "Nord Ouest", "Nord Nord Ouest"
]


def _deg_to_fr_compass(deg: int) -> str:
    deg = deg % 360
    idx = int((deg + 11.25) // 22.5) % 16
    return _FR_COMPASS_16[idx]


def _format_fr_date(d: datetime) -> str:
    # Exemple attendu : "Samedi 22 Octobre"
    return f"{_FR_WEEKDAYS[d.weekday()]} {d.day} {_FR_MONTHS[d.month - 1]}"


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _normalize_output_path(output_csv_path: Optional[str]) -> str:
    """
    - Si None: ./data_surf.csv (dans le dossier courant)
    - Si dossier: <dossier>/data_surf.csv
    - Sinon: chemin tel quel
    """
    if output_csv_path is None:
        return os.path.join(os.getcwd(), "data_surf.csv")

    output_csv_path = os.path.abspath(output_csv_path)
    if os.path.isdir(output_csv_path):
        return os.path.join(output_csv_path, "data_surf.csv")
    return output_csv_path


_ENTRY_PATTERN = re.compile(
    r'\["(?P<dt>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"\]\s*=>\s*'
    r'object\(stdClass\)#\d+\s*\(\d+\)\s*\{\s*(?P<body>.*?)\n\s*\}',
    re.S
)

def _extract_phpdump_string(body: str, field: str) -> Optional[str]:
    """
    Extrait: ["field"]=> string(N) "VALUE"
    """
    m = re.search(
        rf'\["{re.escape(field)}"\]\s*=>\s*string\(\d+\)\s*"([^"]*)"',
        body
    )
    if not m:
        return None
    return m.group(1)


def _safe_float(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    x = x.strip()
    if x == "" or x == "-":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def _safe_int(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    x = x.strip()
    if x == "" or x == "-":
        return None
    try:
        return int(float(x))
    except ValueError:
        return None


# ----------------------------
# Fonction UNIQUE de la librairie
# ----------------------------
def scrape_surf_report(url: str, output_csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Scrape une page Surf-Report (ex: https://www.surf-report.com/meteo-surf/lacanau-s1043.html)
    et extrait, pour les 7 jours affichés, les colonnes:

    - Date (ex: "Samedi 22 Octobre")
    - Time (ex: "08:00")
    - Wave_size (ex: "0.8m - 0.7m")
    - Wind_speed (ex: "3km/h")
    - Wind_direction (ex: "Sud Est")

    Puis:
    - met les données dans un DataFrame
    - sauvegarde en CSV à l'emplacement demandé
    - retourne le DataFrame
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; surf_scrap/1.0; +https://www.surf-report.com/)",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # 1) Parse toutes les entrées horaires trouvées dans le HTML
    # (Sur Surf-Report, on observe souvent un bloc masqué contenant un dump structuré
    # des prévisions horaires avec houle/houleMax/ventMoyen/directionVent, etc.)
    rows: List[Dict[str, Any]] = []

    target_times = {"06:00", "09:00", "12:00", "15:00", "18:00", "21:00"}

    for m in _ENTRY_PATTERN.finditer(html):
        dt_str = m.group("dt")
        body = m.group("body")

        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        time_hm = dt.strftime("%H:%M")
        if time_hm not in target_times:
            continue

        houle = _safe_float(_extract_phpdump_string(body, "houle"))
        houle_max = _safe_float(_extract_phpdump_string(body, "houleMax"))
        vent = _safe_int(_extract_phpdump_string(body, "ventMoyen"))
        dir_deg = _safe_int(_extract_phpdump_string(body, "directionVent"))

        # Gardes-fous
        if houle is None or houle_max is None or vent is None or dir_deg is None:
            continue

        rows.append({
            "_dt": dt,
            "Date": _format_fr_date(dt),
            "Time": time_hm,
            "Wave_size": f"{houle:.1f}m - {houle_max:.1f}m",
            "Wind_speed": f"{vent}km/h",
            "Wind_direction": _deg_to_fr_compass(dir_deg),
        })

    if not rows:
        raise RuntimeError(
            "Aucune donnée n'a été extraite. Le HTML a peut-être changé ou la page ne contient pas le bloc attendu."
        )

    # 2) Garder les 7 premiers jours (tri chronologique)
    rows.sort(key=lambda r: r["_dt"])
    seen_dates: List[str] = []
    filtered: List[Dict[str, Any]] = []
    for r in rows:
        date_key = r["_dt"].strftime("%Y-%m-%d")
        if date_key not in seen_dates:
            if len(seen_dates) >= 7:
                break
            seen_dates.append(date_key)
        if date_key in seen_dates:
            filtered.append(r)

    # 3) DataFrame final (sans la colonne technique _dt)
    df = pd.DataFrame(filtered)[["Date", "Time", "Wave_size", "Wind_speed", "Wind_direction"]]

    # 4) Save CSV
    out_path = _normalize_output_path(output_csv_path)
    _ensure_parent_dir(out_path)
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[surf_scrap] CSV sauvegardé : {out_path}")

    return df