#!/usr/bin/env python3
"""
Double-écriture : chiffre les soumissions contact existantes (plaintext → *_encrypted).

Prérequis :
  - Migration 113 appliquée
  - CRYPTO_LOCAL_MASTER_KEY_B64 ou KMS configuré
  - APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS=true (optionnel ; le script chiffre quand même)

Usage (depuis le répertoire ``api/``) :

  PYTHONPATH=. CRYPTO_LOCAL_MASTER_KEY_B64=... python scripts/backfill_contact_submissions_encryption.py
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")

# noqa: E402 — env avant imports applicatifs
from database import ContactSubmission, SessionLocal  # type: ignore  # pylint: disable=wrong-import-position
from services.security.crypto_access import encrypt_value  # type: ignore
from services.security.crypto_service import is_encryption_configured, is_v1_ciphertext  # type: ignore


def main() -> int:
    if not is_encryption_configured():
        print("ERROR: configure CRYPTO_LOCAL_MASTER_KEY_B64 or KMS", file=sys.stderr)
        return 1
    db = SessionLocal()
    n = 0
    try:
        rows = db.query(ContactSubmission).all()
        for r in rows:
            if r.name_encrypted and is_v1_ciphertext(r.name_encrypted):
                continue
            r.name_encrypted = encrypt_value(
                r.name or "",
                purpose="contact_submission_write",
                operation_id="migration_backfill_contact",
            )
            r.email_encrypted = encrypt_value(
                r.email or "",
                purpose="contact_submission_write",
                operation_id="migration_backfill_contact",
            )
            r.message_encrypted = encrypt_value(
                r.message or "",
                purpose="contact_submission_write",
                operation_id="migration_backfill_contact",
            )
            n += 1
        db.commit()
        print(f"backfilled {n} row(s)")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
