"""
sync_landing.py — Sincroniza actividades de Base44 con activities_cache.json
Uso: python sync_landing.py [--push]

La landing carga actividades dinamicamente desde activities_cache.json.
Este script actualiza ese JSON desde Base44 API.

Requisitos: pip install requests
"""
import json
import sys
import subprocess
from pathlib import Path

# --- Config ---
BASE44_APP_ID = "69177d69d023f43024a2f422"
LANDING_DIR = Path(__file__).parent
CACHE_FILE = LANDING_DIR / "activities_cache.json"

# Category display config
CATEGORY_CONFIG = {
    "excursions": {"icon": "\U0001f6a2", "label_en": "Excursions", "label_es": "Excursiones"},
    "adventure": {"icon": "\U0001f3c4", "label_en": "Adventure", "label_es": "Aventura"},
    "beach": {"icon": "\U0001f3d6\ufe0f", "label_en": "Beach", "label_es": "Playa"},
    "dining": {"icon": "\U0001f377", "label_en": "Dining", "label_es": "Gastronomia"},
    "wellness": {"icon": "\U0001f9d8", "label_en": "Wellness", "label_es": "Bienestar"},
    "culture": {"icon": "\U0001f3ad", "label_en": "Culture", "label_es": "Cultura"},
    "nightlife": {"icon": "\U0001f319", "label_en": "Nightlife", "label_es": "Vida Nocturna"},
    "transfers": {"icon": "\U0001f690", "label_en": "Transfers", "label_es": "Transfers"},
    "car_rental": {"icon": "\U0001f697", "label_en": "Car Rental", "label_es": "Alquiler Coches"},
    "attractions": {"icon": "\U0001f39f\ufe0f", "label_en": "Attractions", "label_es": "Atracciones"},
}

BOOKING_URL = "https://app.hotel-conciergepro.com"


def fetch_activities_from_base44():
    """Fetch active activities from Base44 API."""
    try:
        import requests
        url = f"https://app.base44.com/api/entities/{BASE44_APP_ID}/Activity"
        params = {"query": json.dumps({"active": True}), "limit": 200}
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            activities = data.get("entities", [])
            print(f"[OK] {len(activities)} actividades desde Base44 API")
            return activities
    except Exception as e:
        print(f"[WARN] API error: {e}")

    # Fallback: read from local cache
    if CACHE_FILE.exists():
        print("[INFO] API no disponible, usando cache local")
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))

    print("[ERROR] No se pudo obtener actividades ni de API ni de cache")
    return None


def sort_activities(activities):
    """Sort: OWN first (priority_score DESC), then featured, then alphabetical."""
    return sorted(activities, key=lambda a: (
        -(a.get("priority_score", 50)),
        0 if a.get("is_featured") else 1,
        a.get("name", "")
    ))


def save_cache(activities):
    """Save activities to local JSON cache."""
    CACHE_FILE.write_text(
        json.dumps(activities, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    own_count = sum(1 for a in activities if a.get("source_type") == "own")
    loyalty_count = sum(1 for a in activities if a.get("source_type") != "own")
    print(f"[OK] Cache: {len(activities)} actividades ({own_count} OWN, {loyalty_count} LOYALTY)")


def print_summary(activities):
    """Print activity summary by source_type and category."""
    from collections import Counter
    types = Counter(a.get("source_type", "unknown") for a in activities)
    cats = Counter(a.get("category", "unknown") for a in activities)

    print("\n--- Resumen ---")
    print(f"Total: {len(activities)}")
    for t, c in types.most_common():
        print(f"  {t}: {c}")
    print(f"Categorias: {len(cats)}")
    for cat, c in cats.most_common():
        label = CATEGORY_CONFIG.get(cat, {}).get("label_es", cat)
        print(f"  {label}: {c}")


def git_push(message):
    """Commit and push changes."""
    try:
        subprocess.run(["git", "add", "activities_cache.json"], cwd=LANDING_DIR, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=LANDING_DIR, check=True)
        subprocess.run(["git", "push", "origin", "master"], cwd=LANDING_DIR, check=True)
        print("[OK] Push a GitHub completado")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git: {e}")


def main():
    do_push = "--push" in sys.argv

    print("=" * 50)
    print("  Hotel Concierge Pro — Sync Activities")
    print("=" * 50)

    # Fetch activities
    activities = fetch_activities_from_base44()
    if not activities:
        print("[ERROR] Sin actividades.")
        sys.exit(1)

    # Filter: only valid active activities
    valid = [a for a in activities if a.get("name") and a.get("active", True)]
    print(f"[INFO] {len(valid)} actividades validas de {len(activities)} totales")

    # Sort
    valid = sort_activities(valid)

    # Save cache
    save_cache(valid)

    # Summary
    print_summary(valid)

    # Git push if requested
    if do_push:
        git_push(f"Sync {len(valid)} activities from Base44\n\nBy DavidCabrera")
    else:
        print("\n[INFO] Usa --push para hacer commit + push automatico")

    print(f"\n[DONE] activities_cache.json actualizado")


if __name__ == "__main__":
    main()
