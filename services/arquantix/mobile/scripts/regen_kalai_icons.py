#!/usr/bin/env python3
"""Regenerate the Dart catalog of KALAI line icons.

Reads every SVG inside ``assets/icons/kalai/line/`` and produces
``lib/design_system/atoms/kalai_icons.dart`` with one constant per icon
(camelCase identifier -> asset path) plus an ``all`` map keyed by the
original kebab-case name.

Run from the Flutter project root (``services/arquantix/mobile``):

    python3 scripts/regen_kalai_icons.py
"""

from __future__ import annotations

import os
import sys

ICON_DIR = "assets/icons/kalai/line"
OUT = "lib/design_system/atoms/kalai_icons.dart"


def to_camel(name: str) -> str:
    parts = name.split("-")
    head = parts[0]
    tail = "".join(p.capitalize() for p in parts[1:])
    return head + tail


def main() -> int:
    if not os.path.isdir(ICON_DIR):
        print(f"Icon dir introuvable : {ICON_DIR}", file=sys.stderr)
        return 1

    files = sorted(f for f in os.listdir(ICON_DIR) if f.endswith(".svg"))
    if not files:
        print(f"Aucun SVG trouve dans {ICON_DIR}", file=sys.stderr)
        return 1

    seen: dict[str, str] = {}
    entries: list[tuple[str, str, str]] = []
    for fname in files:
        base = fname[:-4]
        ident = to_camel(base)
        if ident in seen:
            ident = ident + "_"
        seen[ident] = base
        entries.append((ident, base, fname))

    with open(OUT, "w", encoding="utf-8") as out:
        out.write(
            "// GENERATED FILE - DO NOT EDIT MANUALLY.\n"
            "//\n"
            "// Catalogue des icones KALAI (line) du design system Vancelian.\n"
            "// Genere depuis assets/icons/kalai/line/*.svg.\n"
            "//\n"
            "// Utilisation :\n"
            "//   KalaiIcon(KalaiIcons.add, size: 24, color: AppColors.indigo)\n"
            "//\n"
            "// Pour regenerer ce fichier, voir scripts/regen_kalai_icons.py.\n"
            "\n"
            "library;\n"
            "\n"
            "/// Catalogue de toutes les icones KALAI (line).\n"
            "///\n"
            "/// Chaque constante expose le chemin vers l'asset SVG correspondant,\n"
            "/// utilisable directement avec [KalaiIcon] ou [SvgPicture.asset].\n"
            "class KalaiIcons {\n"
            "  KalaiIcons._();\n"
            "\n"
            "  /// Prefixe (dossier) commun a toutes les icones KALAI line.\n"
            "  static const String _base = 'assets/icons/kalai/line/';\n"
            "\n"
        )
        for ident, base, fname in entries:
            out.write(
                f"  /// `{base}.svg`\n"
                f"  static const String {ident} = '${{_base}}{fname}';\n\n"
            )

        out.write(
            "  /// Liste exhaustive (nom lisible -> chemin asset) de toutes les icones.\n"
            "  ///\n"
            "  /// Utile pour la galerie du design system ou pour iterer dynamiquement.\n"
            "  static const Map<String, String> all = <String, String>{\n"
        )
        for ident, base, fname in entries:
            out.write(f"    '{base}': '${{_base}}{fname}',\n")
        out.write("  };\n}\n")

    print(f"Genere {OUT} avec {len(entries)} icones.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
