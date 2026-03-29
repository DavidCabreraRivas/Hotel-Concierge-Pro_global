"""
import_csv_to_base44.py — Importa actividades desde CSV a Base44
Uso: python import_csv_to_base44.py [--dry-run]

Lee import_activities.csv y crea registros Activity en Base44.
Con --dry-run solo muestra lo que haria sin crear nada.

Requisitos: pip install requests
"""
import csv
import json
import sys
from pathlib import Path

BASE44_APP_ID = "69177d69d023f43024a2f422"
CSV_FILE = Path(__file__).parent / "import_activities.csv"


def parse_csv():
    """Parse CSV file into activity dicts."""
    activities = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            activity = {
                "name": row["name"].strip(),
                "name_es": row["name_es"].strip(),
                "category": row["category"].strip(),
                "price_eur": float(row["price_eur"]) if row.get("price_eur") else 0,
                "price_credits": float(row["price_credits"]) if row.get("price_credits") else 0,
                "duration": row["duration"].strip(),
                "location": row["location"].strip(),
                "provider": row["provider"].strip(),
                "commission_percentage": float(row["commission_percentage"]) if row.get("commission_percentage") else 0,
                "description": row["description"].strip(),
                "description_es": row["description_es"].strip(),
                "features": [f.strip() for f in row["features"].split("|")] if row.get("features") else [],
                "features_es": [f.strip() for f in row["features_es"].split("|")] if row.get("features_es") else [],
                "integration_type": row.get("integration_type", "manual").strip(),
                "is_featured": row.get("is_featured", "false").strip().lower() == "true",
                "active": row.get("active", "true").strip().lower() == "true",
            }
            activities.append(activity)
    return activities


def display_summary(activities):
    """Show summary of activities to import."""
    cats = {}
    for a in activities:
        cat = a["category"]
        cats[cat] = cats.get(cat, 0) + 1

    print(f"\nTotal actividades: {len(activities)}")
    print(f"Categorias: {len(cats)}")
    for cat, count in sorted(cats.items()):
        print(f"  - {cat}: {count}")

    featured = sum(1 for a in activities if a["is_featured"])
    print(f"Destacadas: {featured}")

    providers = set(a["provider"] for a in activities)
    print(f"Proveedores unicos: {len(providers)}")
    for p in sorted(providers):
        count = sum(1 for a in activities if a["provider"] == p)
        print(f"  - {p}: {count} actividades")

    avg_commission = sum(a["commission_percentage"] for a in activities) / len(activities)
    print(f"Comision media: {avg_commission:.1f}%")

    print("\n--- Lista completa ---")
    for i, a in enumerate(activities, 1):
        feat = " *FEATURED*" if a["is_featured"] else ""
        print(f"  {i:2d}. [{a['category']:12s}] {a['name'][:55]:55s} {a['price_eur']:6.0f}EUR  {a['commission_percentage']:2.0f}%{feat}")


def upload_to_base44(activities):
    """Upload activities to Base44 via API."""
    try:
        import requests
    except ImportError:
        print("[ERROR] Instala requests: pip install requests")
        return False

    url = f"https://app.base44.com/api/entities/{BASE44_APP_ID}/Activity"
    created = 0
    errors = 0

    for a in activities:
        try:
            resp = requests.post(url, json=a, timeout=10)
            if resp.status_code in (200, 201):
                created += 1
                print(f"  [OK] {a['name'][:50]}")
            else:
                errors += 1
                print(f"  [ERR] {a['name'][:50]} — {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            errors += 1
            print(f"  [ERR] {a['name'][:50]} — {e}")

    print(f"\nResultado: {created} creadas, {errors} errores")
    return errors == 0


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 55)
    print("  Hotel Concierge Pro — CSV Import to Base44")
    print("=" * 55)

    if not CSV_FILE.exists():
        print(f"[ERROR] No encontrado: {CSV_FILE}")
        sys.exit(1)

    activities = parse_csv()

    if not activities:
        print("[ERROR] CSV vacio")
        sys.exit(1)

    display_summary(activities)

    if dry_run:
        print("\n[DRY RUN] No se ha subido nada. Quita --dry-run para importar.")
    else:
        print("\n[UPLOAD] Subiendo a Base44...")
        upload_to_base44(activities)

    # Also update local cache
    cache = Path(__file__).parent / "activities_cache.json"
    if cache.exists():
        existing = json.loads(cache.read_text(encoding="utf-8"))
    else:
        existing = []

    # Merge: add new activities not already in cache (by name)
    existing_names = {a["name"] for a in existing}
    new_activities = [a for a in activities if a["name"] not in existing_names]
    if new_activities:
        merged = existing + new_activities
        cache.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[CACHE] Anadidas {len(new_activities)} nuevas al cache ({len(merged)} total)")
    else:
        print(f"\n[CACHE] Sin nuevas actividades para anadir")


if __name__ == "__main__":
    main()
