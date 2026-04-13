#!/usr/bin/env python3
"""Obsolète : le « client current » test a été retiré.

Utiliser à la place::

    python3 -m scripts.purge_all_pe_clients

pour supprimer **tous** les ``pe_clients`` et les données associées (dev uniquement).
"""
from __future__ import annotations

import sys


def main() -> None:
    print(
        "Ce script est obsolète (plus de client « test » courant).\n"
        "Pour tout supprimer côté clients PE : python3 -m scripts.purge_all_pe_clients",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
