"""
validate_activities.py — Bot de validación y corrección automática de actividades
Uso: python validate_activities.py [--fix] [--strict]

Sin flags: solo reporta errores
--fix: corrige automáticamente lo que pueda
--strict: falla con exit code 1 si hay errores críticos (para CI/hooks)

Ejecutar SIEMPRE antes de hacer push.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

LANDING_DIR = Path(__file__).parent
CACHE_FILE = LANDING_DIR / "activities_cache.json"
LOG_FILE = LANDING_DIR / "validation_log.txt"

# ══════════════════════════════════════════════════════════════
# REGLAS DE VALIDACIÓN — Modificar aquí para añadir nuevas reglas
# ══════════════════════════════════════════════════════════════

REQUIRED_FIELDS = {
    "name": "Nombre EN obligatorio",
    "name_es": "Nombre ES obligatorio",
    "category": "Categoría obligatoria",
    "source_type": "source_type obligatorio (own/loyalty/b2b_api)",
}

PRICE_RULES = {
    "min_price": 5,        # Precio mínimo EUR (evitar €0)
    "max_price": 500,       # Precio máximo EUR (detectar errores de tipeo)
    "field": "price_eur",   # Campo de precio principal
}

IMAGE_RULES = {
    "required": True,                    # Toda actividad debe tener imagen
    "min_url_length": 20,                # URL mínima razonable
    "banned_domains": [],                # Dominios prohibidos (vacío por ahora)
    "allowed_domains": [                 # Dominios permitidos
        "cdn.pixabay.com",
        "images.unsplash.com",
        "images.pexels.com",
        "upload.wikimedia.org",
        "hotel-conciergepro.com",
    ],
}

VALID_CATEGORIES = [
    "excursions", "adventure", "beach", "dining", "wellness",
    "culture", "nightlife", "transfers", "car_rental", "attractions"
]

VALID_SOURCE_TYPES = ["own", "loyalty", "b2b_api"]

# Actividades que deben ser OWN (protección contra regresión)
MUST_BE_OWN = [
    "South Tour (Timanfaya + La Geria)",
    "Senderismo Parque Natural Volcanes",
    "Wine Tour La Geria (4 Wineries)",
    "Cesar Manrique Art & Architecture Tour",
    "Comedy Drag Night Show",
    "Premium Massage Pack with Transport",
    "5-Star Dinner + Holistic Massage Pack with Transport",
    "In-Room Massage",
    "Traditional Manicure & Pedicure",
    "Electric Bike Rental",
    "Private Group Tour - Vineyard & Wine Tasting",
]

# Actividades prohibidas (eliminadas intencionalmente)
BANNED_ACTIVITIES = [
    "E-Scooter Rental",
    "Wine Tasting Tour - La Geria Vineyards",   # duplicado
    "Electric Bike Rental with Route Map",        # duplicado
]

# Precios de referencia (para detectar si alguien los borra)
REFERENCE_PRICES = {
    "Grand Tour Lanzarote (Timanfaya + Jameos + La Geria)": 65,
    "South Tour (Timanfaya + La Geria)": 38,
    "Kayak & Snorkel Papagayo": 45,
    "Buggy Volcano Tour": 90,
    "Wine Tour La Geria (4 Wineries)": 65,
    "Cesar Manrique Art & Architecture Tour": 48,
    "Volcano Dinner at Timanfaya": 85,
    "Submarine Lanzarote": 30,
    "Aqualava Waterpark": 22,
    "Rancho Texas Animal Park": 25,
    "Airport Transfer Sedan (1-3 pax)": 35,
    "Airport Transfer Minivan (4-7 pax)": 55,
    "Economy Car Rental (Fiat 500 or similar)": 25,
    "Premium Massage Pack with Transport": 95,
    "5-Star Dinner + Holistic Massage Pack with Transport": 150,
    "In-Room Massage": 60,
    "Traditional Manicure & Pedicure": 45,
    "Electric Bike Rental": 25,
    "Private Group Tour - Vineyard & Wine Tasting": 55,
    "Comedy Drag Night Show": 40,
}

# Placeholder por categoría (fallback si no hay imagen)
CATEGORY_PLACEHOLDERS = {
    "excursions": "https://cdn.pixabay.com/photo/2019/12/01/13/42/landscape-4665914_1280.jpg",
    "adventure": "https://cdn.pixabay.com/photo/2020/04/04/12/26/buggy-5002888_1280.jpg",
    "beach": "https://cdn.pixabay.com/photo/2017/07/21/03/55/playa-del-papagayo-2524325_1280.jpg",
    "dining": "https://cdn.pixabay.com/photo/2015/10/02/15/00/tapas-968457_1280.jpg",
    "wellness": "https://cdn.pixabay.com/photo/2017/08/02/14/26/massage-therapy-2573846_1280.jpg",
    "culture": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Jameos_del_agua%2C_Lanzarote.JPG/1280px-Jameos_del_agua%2C_Lanzarote.JPG",
    "nightlife": "https://cdn.pixabay.com/photo/2016/11/29/12/35/bar-1869656_1280.jpg",
    "transfers": "https://cdn.pixabay.com/photo/2016/09/01/21/08/mercedes-1637706_1280.jpg",
    "car_rental": "https://cdn.pixabay.com/photo/2016/12/03/18/57/car-1880381_1280.jpg",
    "attractions": "https://cdn.pixabay.com/photo/2018/08/14/13/23/ocean-3605547_1280.jpg",
}


# ══════════════════════════════════════════════════════════════
# MOTOR DE VALIDACIÓN
# ══════════════════════════════════════════════════════════════

class ValidationResult:
    def __init__(self):
        self.errors = []      # Críticos — deben arreglarse
        self.warnings = []    # No críticos — revisar
        self.fixes = []       # Correcciones aplicadas automáticamente
        self.removed = []     # Actividades eliminadas

    def error(self, activity_name, msg):
        self.errors.append(f"❌ [{activity_name}] {msg}")

    def warn(self, activity_name, msg):
        self.warnings.append(f"⚠️  [{activity_name}] {msg}")

    def fix(self, activity_name, msg):
        self.fixes.append(f"🔧 [{activity_name}] {msg}")

    def remove(self, activity_name, msg):
        self.removed.append(f"🗑️  [{activity_name}] {msg}")

    def print_report(self):
        total = len(self.errors) + len(self.warnings)
        print(f"\n{'='*60}")
        print(f"  VALIDATION REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")

        if self.removed:
            print(f"\n🗑️  REMOVED ({len(self.removed)}):")
            for r in self.removed:
                print(f"  {r}")

        if self.fixes:
            print(f"\n🔧 AUTO-FIXED ({len(self.fixes)}):")
            for f in self.fixes:
                print(f"  {f}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"  {e}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")

        print(f"\n{'='*60}")
        return len(self.errors)


def validate_and_fix(activities, do_fix=False):
    """Run all validations. If do_fix=True, correct what we can."""
    result = ValidationResult()

    # 1. Remove banned activities
    clean = []
    for a in activities:
        name = a.get("name", "")
        if name in BANNED_ACTIVITIES:
            result.remove(name, "Actividad prohibida (eliminada intencionalmente)")
            continue
        clean.append(a)

    if do_fix:
        activities = clean

    # 2. Validate each activity
    for a in activities:
        name = a.get("name", "???")

        # Required fields
        for field, msg in REQUIRED_FIELDS.items():
            if not a.get(field):
                result.error(name, f"Campo faltante: {field} — {msg}")
                if do_fix and field == "source_type":
                    a["source_type"] = "loyalty"
                    result.fix(name, "source_type → 'loyalty' (default)")

        # Category validation
        cat = a.get("category", "")
        if cat and cat not in VALID_CATEGORIES:
            result.error(name, f"Categoría inválida: '{cat}' (válidas: {VALID_CATEGORIES})")

        # Source type validation
        st = a.get("source_type", "")
        if st and st not in VALID_SOURCE_TYPES:
            result.error(name, f"source_type inválido: '{st}'")

        # Price validation
        price = a.get(PRICE_RULES["field"])
        if price is None or price == 0:
            # Try to fix from reference prices
            if do_fix and name in REFERENCE_PRICES:
                a[PRICE_RULES["field"]] = REFERENCE_PRICES[name]
                result.fix(name, f"price_eur → {REFERENCE_PRICES[name]}€ (referencia)")
            else:
                result.error(name, f"Sin precio EUR (price_eur = {price})")
        elif price < PRICE_RULES["min_price"]:
            result.error(name, f"Precio sospechosamente bajo: {price}€ (mín: {PRICE_RULES['min_price']}€)")
        elif price > PRICE_RULES["max_price"]:
            result.warn(name, f"Precio muy alto: {price}€ (máx recomendado: {PRICE_RULES['max_price']}€)")

        # Image validation
        img = a.get("image_url")
        if not img or len(img) < IMAGE_RULES["min_url_length"]:
            if do_fix:
                placeholder = CATEGORY_PLACEHOLDERS.get(cat, CATEGORY_PLACEHOLDERS["excursions"])
                a["image_url"] = placeholder
                result.fix(name, f"Imagen placeholder asignada ({cat})")
            else:
                result.error(name, "Sin imagen")

        # OWN protection
        if name in MUST_BE_OWN:
            if a.get("source_type") != "own":
                if do_fix:
                    a["source_type"] = "own"
                    a["priority_score"] = 80
                    result.fix(name, "source_type → 'own' + priority_score → 80")
                else:
                    result.error(name, "Debe ser source_type='own' pero es '{}'".format(a.get("source_type")))

        # Priority score coherence
        if a.get("source_type") == "own" and (a.get("priority_score") or 50) < 80:
            if do_fix:
                a["priority_score"] = 80
                result.fix(name, "priority_score → 80 (OWN debe ser ≥80)")
            else:
                result.warn(name, f"OWN con priority_score bajo: {a.get('priority_score')}")

        # Accessibility coherence
        if a.get("wheelchair_accessible") and not a.get("reduced_mobility_friendly"):
            if do_fix:
                a["reduced_mobility_friendly"] = True
                result.fix(name, "reduced_mobility_friendly → True (wheelchair implica reduced)")
            else:
                result.warn(name, "wheelchair_accessible=True pero reduced_mobility_friendly=False")

        # Description check
        if not a.get("description"):
            result.warn(name, "Sin descripción EN")
        if not a.get("description_es"):
            result.warn(name, "Sin descripción ES")

    # 3. Duplicate check
    names = [a.get("name") for a in activities]
    seen = set()
    for n in names:
        if n in seen:
            result.error(n, "DUPLICADO detectado")
        seen.add(n)

    return activities if do_fix else None, result


def main():
    do_fix = "--fix" in sys.argv
    strict = "--strict" in sys.argv

    print("=" * 60)
    print("  Hotel Concierge Pro — Activity Validator")
    print("  Mode:", "FIX" if do_fix else "CHECK ONLY")
    print("=" * 60)

    if not CACHE_FILE.exists():
        print(f"[ERROR] {CACHE_FILE} no encontrado")
        sys.exit(1)

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        activities = json.load(f)

    print(f"[INFO] {len(activities)} actividades cargadas")

    fixed_activities, result = validate_and_fix(activities, do_fix=do_fix)

    error_count = result.print_report()

    if do_fix and fixed_activities is not None:
        # Re-sort: OWN first
        fixed_activities.sort(key=lambda a: (
            -(a.get("priority_score") or 50),
            0 if a.get("is_featured") else 1,
            a.get("name", "")
        ))

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(fixed_activities, f, ensure_ascii=False, indent=2)

        print(f"\n[SAVED] {len(fixed_activities)} actividades guardadas")
        print(f"  Fixes: {len(result.fixes)}")
        print(f"  Removed: {len(result.removed)}")

    # Save log
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n--- {datetime.now().isoformat()} ---\n")
        f.write(f"Mode: {'FIX' if do_fix else 'CHECK'}\n")
        f.write(f"Errors: {len(result.errors)}, Warnings: {len(result.warnings)}, Fixes: {len(result.fixes)}\n")
        for line in result.errors + result.warnings + result.fixes + result.removed:
            f.write(f"  {line}\n")

    if strict and error_count > 0:
        print(f"\n[STRICT] {error_count} errores — exit code 1")
        sys.exit(1)


if __name__ == "__main__":
    main()
