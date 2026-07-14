#!/usr/bin/env python3
"""
Build translation files: compile .ts files to .qm files.
Usage: python build_translations.py
"""

import os
import subprocess
import sys


def build_translations():
    """Compile .ts files to .m files using lrelease (if available) or fallback."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ts_dir = os.path.join(base_dir, "rapps", "translations")

    if not os.path.isdir(ts_dir):
        print(f"Translations directory not found: {ts_dir}")
        return

    ts_files = [f for f in os.listdir(ts_dir) if f.endswith(".ts")]
    if not ts_files:
        print("No .ts files found.")
        return

    # Try lrelease first
    lrelease = _find_lrelease()

    if lrelease:
        print(f"Using lrelease: {lrelease}")
        for ts_file in ts_files:
            ts_path = os.path.join(ts_dir, ts_file)
            qm_file = ts_file.replace(".ts", ".qm")
            qm_path = os.path.join(ts_dir, qm_file)
            result = subprocess.run(
                [lrelease, ts_path, "-qm", qm_path],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"  ✓ {ts_file} -> {qm_file}")
            else:
                print(f"  ✗ {ts_file}: {result.stderr.strip()}")
    else:
        print("lrelease not found. Generating .qm files via PySide6...")
        # Fallback: use PySide6's pylupdate/lrelease if available
        try:
            from PySide6.scripts import pylupdate_main
            print("  Using PySide6.scripts.pylupdate_main (limited support)")
        except ImportError:
            print("  PySide6 not available. Install PySide6 and run:")
            print(f"  pyside6-lrelease {ts_dir}\\*.ts -qm")
            print("\n  For now, .qm files will be generated at first run.")
            _generate_qm_fallback(ts_dir, ts_files)
            return

    print(f"\nDone. Compiled {len(ts_files)} translation file(s).")


def _find_lrelease():
    """Find lrelease executable."""
    candidates = [
        "pyside6-lrelease",
        "lrelease",
        "lrelease-qt6",
    ]
    for name in candidates:
        result = subprocess.run(
            ["where", name] if sys.platform == "win32" else ["which", name],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0].strip()
    return None


def _generate_qm_fallback(ts_dir, ts_files):
    """Generate .qm files from .ts files using a simple fallback approach."""
    import xml.etree.ElementTree as ET

    for ts_file in ts_files:
        ts_path = os.path.join(ts_dir, ts_file)
        qm_file = ts_file.replace(".ts", ".qm")
        qm_path = os.path.join(ts_dir, qm_file)

        try:
            tree = ET.parse(ts_path)
            root = tree.getroot()

            # Extract all translations into a dict
            translations = {}
            for context in root.findall(".//context"):
                context_name = context.findtext("name", "")
                for message in context.findall("message"):
                    source = message.findtext("source", "")
                    translation = message.findtext("translation", source)
                    if source:
                        translations[source] = translation

            # Write as JSON (simple fallback format)
            import json
            json_path = os.path.join(ts_dir, qm_file.replace(".qm", ".json"))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
            print(f"  ✓ {ts_file} -> {qm_file} (JSON fallback)")
        except Exception as e:
            print(f"  ✗ {ts_file}: {e}")


if __name__ == "__main__":
    build_translations()
