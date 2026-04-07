"""
sync_and_validate.py — Pipeline completo: Base44 → JSON → Validar → Fix → Push
Uso: python sync_and_validate.py [--push]

Este es el ÚNICO comando que debes usar para actualizar la landing.
Combina sync + validación + corrección automática + push.
"""
import subprocess
import sys
from pathlib import Path

LANDING_DIR = Path(__file__).parent


def run(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'─'*50}")
    print(f"  {description}")
    print(f"{'─'*50}")
    result = subprocess.run(
        [sys.executable] + cmd,
        cwd=LANDING_DIR,
        capture_output=False
    )
    return result.returncode == 0


def main():
    do_push = "--push" in sys.argv

    print("=" * 60)
    print("  Hotel Concierge Pro — Full Sync Pipeline")
    print("=" * 60)

    # Step 1: Sync from Base44
    print("\n[1/4] Syncing from Base44...")
    run(["sync_landing.py"], "Sync Base44 → activities_cache.json")

    # Step 2: Validate (check only first)
    print("\n[2/4] Validating...")
    run(["validate_activities.py"], "Check for errors")

    # Step 3: Auto-fix
    print("\n[3/4] Auto-fixing...")
    run(["validate_activities.py", "--fix"], "Apply automatic fixes")

    # Step 4: Final validation (strict)
    print("\n[4/4] Final validation (strict)...")
    ok = run(["validate_activities.py", "--strict"], "Strict validation")

    if not ok:
        print("\n⛔ Pipeline FAILED — hay errores que requieren corrección manual")
        print("   Revisa el reporte arriba y corrige en Base44 o en el JSON")
        sys.exit(1)

    print("\n✅ Pipeline OK — todas las validaciones pasadas")

    if do_push:
        print("\n[PUSH] Pushing to GitHub Pages...")
        subprocess.run(
            ["git", "add", "activities_cache.json"],
            cwd=LANDING_DIR
        )
        subprocess.run(
            ["git", "commit", "-m",
             f"Auto-sync: validated activities\n\nBy DavidCabrera"],
            cwd=LANDING_DIR
        )
        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=LANDING_DIR
        )
        print("[OK] Push completado")
    else:
        print("\n[INFO] Usa --push para hacer git push automático")


if __name__ == "__main__":
    main()
