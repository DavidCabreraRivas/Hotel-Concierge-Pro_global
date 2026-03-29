"""
sync_landing.py — Sincroniza actividades de Base44 con la landing de GitHub Pages
Uso: python sync_landing.py [--push]

Lee las actividades activas desde Base44, genera las cards HTML y actualiza
index.html + es/index.html. Con --push hace git commit + push automatico.

Requisitos: pip install requests
"""
import json
import re
import sys
import subprocess
from pathlib import Path

# --- Config ---
BASE44_APP_ID = "69177d69d023f43024a2f422"
# Base44 public API endpoint (entities query)
BASE44_API = f"https://app.base44.com/api/entities"
LANDING_DIR = Path(__file__).parent
INDEX_EN = LANDING_DIR / "index.html"
INDEX_ES = LANDING_DIR / "es" / "index.html"

# Category display config
CATEGORY_CONFIG = {
    "excursions": {"icon": "🚢", "label_en": "Excursions", "label_es": "Excursiones"},
    "adventure": {"icon": "🏄", "label_en": "Adventure", "label_es": "Aventura"},
    "beach": {"icon": "🏖️", "label_en": "Beach", "label_es": "Playa"},
    "dining": {"icon": "🍷", "label_en": "Dining", "label_es": "Gastronomia"},
    "wellness": {"icon": "🧘", "label_en": "Wellness", "label_es": "Bienestar"},
    "culture": {"icon": "🎭", "label_en": "Culture", "label_es": "Cultura"},
    "nightlife": {"icon": "🌙", "label_en": "Nightlife", "label_es": "Vida Nocturna"},
}

BOOKING_URL = "https://app.hotel-conciergepro.com"


def fetch_activities_from_base44():
    """Fetch active activities from Base44 API."""
    try:
        import requests
        url = f"https://app.base44.com/api/entities/{BASE44_APP_ID}/Activity"
        params = {"query": json.dumps({"active": True}), "limit": 100}
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("entities", [])
    except Exception:
        pass

    # Fallback: read from local cache
    cache = LANDING_DIR / "activities_cache.json"
    if cache.exists():
        print("[INFO] API no disponible, usando cache local")
        return json.loads(cache.read_text(encoding="utf-8"))

    print("[ERROR] No se pudo obtener actividades ni de API ni de cache")
    return None


def fetch_activities_from_cache():
    """Read activities from local JSON cache (manual export from Base44)."""
    cache = LANDING_DIR / "activities_cache.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    return None


def generate_card_html(activity):
    """Generate HTML card for one activity."""
    name_en = activity.get("name", "")
    name_es = activity.get("name_es", name_en)
    desc_en = activity.get("description", "")
    desc_es = activity.get("description_es", desc_en)
    cat = activity.get("category", "excursions")
    cat_label = CATEGORY_CONFIG.get(cat, {}).get("label_en", cat.title())
    img = activity.get("image_url", "")
    location = activity.get("location", "")
    duration = activity.get("duration", "")
    price = activity.get("price_eur") or activity.get("price_credits", 0)
    is_featured = activity.get("is_featured", False)
    features_en = activity.get("features", [])[:3]
    features_es = activity.get("features_es", features_en)[:3]

    featured_html = '<span class="card-featured">FEATURED</span>' if is_featured else ""

    features_html = ""
    for i, feat_en in enumerate(features_en):
        feat_es = features_es[i] if i < len(features_es) else feat_en
        features_html += f'                    <span class="card-feature" data-en="{feat_en}" data-es="{feat_es}">{feat_en}</span>\n'

    return f"""
        <!-- {name_en} -->
        <div class="activity-card" data-cat="{cat}">
            <div class="card-img">
                <img src="{img}" alt="{name_en}" loading="lazy">
                <span class="card-badge">{cat_label}</span>
                {featured_html}
            </div>
            <div class="card-body">
                <h3 data-en="{name_en}" data-es="{name_es}">{name_en}</h3>
                <div class="card-meta">
                    <span>📍 {location}</span>
                    <span>⏱️ {duration}</span>
                </div>
                <p class="card-desc" data-en="{desc_en}" data-es="{desc_es}">{desc_en}</p>
                <div class="card-features">
{features_html}                </div>
                <div class="card-footer">
                    <div class="card-price">&euro;{price} <span>/ person</span></div>
                    <a href="{BOOKING_URL}" class="btn-book" data-en="Book Now" data-es="Reservar">Book Now</a>
                </div>
            </div>
        </div>
"""


def inject_cards_into_html(html_path, cards_html, total_count, cat_count):
    """Replace the activities grid content in the HTML file."""
    html = html_path.read_text(encoding="utf-8")

    # Replace content between activities-grid div
    pattern = r'(<div class="activities-grid" id="activitiesGrid">)(.*?)(    </div>\n</section>)'
    replacement = rf'\1\n{cards_html}\n\3'
    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)

    # Update stats numbers
    new_html = re.sub(
        r'(<div class="num">)\d+(</div><div class="label" data-en="Experiences")',
        rf'\g<1>{total_count}\2',
        new_html
    )

    html_path.write_text(new_html, encoding="utf-8")
    print(f"[OK] Actualizado: {html_path} ({total_count} actividades)")


def save_cache(activities):
    """Save activities to local JSON cache."""
    cache = LANDING_DIR / "activities_cache.json"
    cache.write_text(json.dumps(activities, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Cache guardada: {cache} ({len(activities)} actividades)")


def git_push(message):
    """Commit and push changes."""
    try:
        subprocess.run(["git", "add", "-A"], cwd=LANDING_DIR, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=LANDING_DIR, check=True)
        subprocess.run(["git", "push", "origin", "master"], cwd=LANDING_DIR, check=True)
        print("[OK] Push a GitHub completado")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git: {e}")


def main():
    do_push = "--push" in sys.argv
    use_cache = "--cache" in sys.argv

    print("=" * 50)
    print("  Hotel Concierge Pro — Sync Landing")
    print("=" * 50)

    # Fetch activities
    if use_cache:
        activities = fetch_activities_from_cache()
    else:
        activities = fetch_activities_from_base44()

    if not activities:
        print("[ERROR] Sin actividades. Usa --cache para leer desde cache local.")
        print("        O exporta manualmente desde Base44 a activities_cache.json")
        sys.exit(1)

    # Filter: only complete activities (must have name)
    valid = [a for a in activities if a.get("name") and a.get("active", True)]
    print(f"[INFO] {len(valid)} actividades validas de {len(activities)} totales")

    # Sort: featured first, then by category
    valid.sort(key=lambda a: (0 if a.get("is_featured") else 1, a.get("category", "")))

    # Generate HTML cards
    cards_html = ""
    for act in valid:
        cards_html += generate_card_html(act)

    # Count categories
    cats = set(a.get("category") for a in valid)

    # Inject into EN and ES
    if INDEX_EN.exists():
        inject_cards_into_html(INDEX_EN, cards_html, len(valid), len(cats))
    if INDEX_ES.exists():
        inject_cards_into_html(INDEX_ES, cards_html, len(valid), len(cats))

    # Save cache
    save_cache(valid)

    # Git push if requested
    if do_push:
        git_push(f"Sync {len(valid)} activities from Base44\n\nBy DavidCabrera")
    else:
        print("\n[INFO] Usa --push para hacer commit + push automatico")

    print(f"\n[DONE] Landing actualizada con {len(valid)} actividades en {len(cats)} categorias")


if __name__ == "__main__":
    main()
