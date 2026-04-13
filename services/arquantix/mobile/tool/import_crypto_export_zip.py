#!/usr/bin/env python3
"""Importe les SVG depuis l’archive « Export svg logo crypto » vers assets/crypto_svgs/.

Usage :
  python3 import_crypto_export_zip.py /chemin/vers/archive.zip

Les fichiers sont copiés en minuscules (`btc.svg`, `jto.svg`, …). Mettre à jour
`lib/design_system/assets/crypto_instrument_svgs.dart` : ensemble `_kBundledExportTickers`
doit lister exactement les tickers présents (majuscules).

Après ajout de nouveaux tickers dans l’export, régénérer la constante :

  python3 -c "import os; p='../assets/crypto_svgs'; ...
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "assets", "crypto_svgs"))


def main() -> int:
    argv = [a for a in sys.argv[1:] if a != "--emit-dart-set"]
    emit_dart = "--emit-dart-set" in sys.argv[1:]
    if len(argv) < 1:
        print(
            "Usage: import_crypto_export_zip.py <archive.zip> [--emit-dart-set]",
            file=sys.stderr,
        )
        return 1
    zpath = os.path.expanduser(argv[0])
    if not os.path.isfile(zpath):
        print(f"Fichier introuvable: {zpath}", file=sys.stderr)
        return 1

    os.makedirs(DEST_DIR, exist_ok=True)
    for name in os.listdir(DEST_DIR):
        if name.endswith(".svg"):
            os.remove(os.path.join(DEST_DIR, name))

    count = 0
    with zipfile.ZipFile(zpath, "r") as zf:
        for info in zf.infolist():
            if info.is_dir() or "__MACOSX" in info.filename:
                continue
            base = os.path.basename(info.filename)
            if not base.lower().endswith(".svg"):
                continue
            stem = os.path.splitext(base)[0]
            out = os.path.join(DEST_DIR, f"{stem.lower()}.svg")
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1

    print(f"Importé {count} SVG vers {DEST_DIR}")
    if emit_dart:
        keys = sorted(
            f[:-4].upper()
            for f in os.listdir(DEST_DIR)
            if f.endswith(".svg")
        )
        print("\n// Coller dans _kBundledExportTickers :\n")
        for k in keys:
            print(f"  '{k}',")
    else:
        print(
            "Si les tickers changent : mettre à jour _kBundledExportTickers "
            "dans crypto_instrument_svgs.dart (relancer avec --emit-dart-set)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
