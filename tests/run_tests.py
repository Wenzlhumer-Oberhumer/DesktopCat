"""Einfacher, abhaengigkeitsfreier Test-Runner fuer tests/."""
import importlib.util
import sys
import traceback
from pathlib import Path

# Projektwurzel zu sys.path hinzufuegen
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PyQt6.QtWidgets import QApplication

def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Konnte Spec fuer {path} nicht laden")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def main():
    # Fuer Qt-Signale und Widgets wird eine Instanz benoetigt
    app = QApplication.instance() or QApplication(sys.argv)
    assert app is not None

    test_files = [
        "test_paths",
        "test_cli_protocol",
        "test_cli_loop",
        "test_gemini",
        "test_updater",
        "test_characters",
        "test_new_tools",
        "test_confirm",
        "test_name_kylie",
        "test_memory_store",
        "test_daily",
        "test_accessories",
    ]

    total = 0
    passed = 0
    failed = 0

    print("=== Starte Desktop Cat Test-Suite ===")

    tests_dir = _ROOT / "tests"

    for mod_name in test_files:
        file_path = tests_dir / f"{mod_name}.py"
        try:
            mod = load_module_from_path(mod_name, file_path)
        except Exception as exc:
            print(f"\n[FEHLER] Konnte Modul {mod_name} nicht laden: {exc}")
            traceback.print_exc()
            failed += 1
            continue

        test_funcs = [getattr(mod, name) for name in dir(mod) if name.startswith("test_") and callable(getattr(mod, name))]
        print(f"\n--- {mod_name} ({len(test_funcs)} Tests) ---")

        for fn in test_funcs:
            total += 1
            try:
                fn()
                print(f"  [OK] {fn.__name__}")
                passed += 1
            except Exception as exc:
                print(f"  [FEHLER] {fn.__name__}: {exc}")
                traceback.print_exc()
                failed += 1

    print("\n===============================")
    print(f"Ergebnis: {passed}/{total} bestanden, {failed} fehlgeschlagen.")
    print("===============================")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
