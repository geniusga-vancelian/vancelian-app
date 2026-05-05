"""Tests unitaires Phase 2 wiki v1.4 patch 3 — migration 151.

Couvre :
  * Présence + activation du nouveau slug `vancelian_product_catalog`.
  * Désactivation des 3 fiches non-canoniques (`scpi`,
    `livret_vancelian`, `managed_mandate`).
  * Lecture via `read_product_knowledge` retourne le body attendu pour
    le catalogue, et `not_found` (ou inactive) pour les fiches désactivées.
  * Sanity du contenu du catalogue : mentionne les 5 familles, pas
    SCPI ni livret rémunéré.
"""

from __future__ import annotations

from sqlalchemy import text

from database import SessionLocal


# ─────────────────────────────────────────────────────────────────────
# A. État DB après migration 151
# ─────────────────────────────────────────────────────────────────────


class TestMigration151AppliedToDb:
    def test_catalog_slug_present_and_active(self):
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT slug, title, is_active "
                    "FROM product_knowledge "
                    "WHERE slug = 'vancelian_product_catalog'"
                )
            ).fetchone()
            assert row is not None, (
                "vancelian_product_catalog must be seeded by migration 151"
            )
            assert row.is_active is True
            assert "Vancelian" in row.title or "produit" in row.title.lower()

    def test_scpi_slug_deactivated(self):
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT is_active FROM product_knowledge "
                    "WHERE slug = 'product_basics_scpi'"
                )
            ).fetchone()
            assert row is not None, "row must still exist (soft-delete)"
            assert row.is_active is False, (
                "scpi must be deactivated by migration 151"
            )

    def test_livret_slug_deactivated(self):
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT is_active FROM product_knowledge "
                    "WHERE slug = 'product_basics_livret_vancelian'"
                )
            ).fetchone()
            assert row is not None
            assert row.is_active is False

    def test_managed_mandate_slug_deactivated(self):
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT is_active FROM product_knowledge "
                    "WHERE slug = 'product_basics_managed_mandate'"
                )
            ).fetchone()
            # Si la fiche existe (seed 149), elle doit être désactivée.
            # Si elle n'existe pas (déjà absente), c'est OK aussi.
            if row is not None:
                assert row.is_active is False

    def test_canonical_active_slugs_still_active(self):
        """Garde-fou : on n'a pas accidentellement désactivé les fiches
        produit légitimes."""
        with SessionLocal() as db:
            for slug in (
                "product_basics_vault",
                "product_basics_crypto_bundle",
                "product_basics_exclusive_offer",
                "deposit_delay_sepa_in",
                "kyc_review_typical_delay",
            ):
                row = db.execute(
                    text(
                        "SELECT is_active FROM product_knowledge "
                        "WHERE slug = :slug"
                    ),
                    {"slug": slug},
                ).fetchone()
                assert row is not None, f"{slug} should exist"
                assert row.is_active is True, (
                    f"{slug} must remain active (regression guard)"
                )


# ─────────────────────────────────────────────────────────────────────
# B. Sanity du contenu de `vancelian_product_catalog`
# ─────────────────────────────────────────────────────────────────────


class TestCatalogContentSanity:
    def test_lists_five_canonical_families(self):
        """Le body doit explicitement mentionner les 5 familles
        produit Vancelian (validation éditoriale)."""
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT body FROM product_knowledge "
                    "WHERE slug = 'vancelian_product_catalog' "
                    "AND is_active = TRUE"
                )
            ).fetchone()
            assert row is not None
            body = row.body.lower()
            # 5 familles minimum reprises de la réponse référence.
            assert "coffre" in body and (
                "flexible" in body and "avenir" in body
            )
            assert "offre" in body and "exclusive" in body
            assert "crypto basket" in body or "crypto baskets" in body
            assert "trading spot" in body or "spot" in body
            assert "compte eur" in body or "carte visa" in body or "iban" in body

    def test_explicitly_excludes_non_offered_products(self):
        """Le body doit dire **explicitement** que SCPI / livret / mandat
        ne font pas partie de la gamme — c'est l'antidote à
        l'hallucination de la conv 534d545b."""
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT body FROM product_knowledge "
                    "WHERE slug = 'vancelian_product_catalog'"
                )
            ).fetchone()
            assert row is not None
            body = row.body.lower()
            # Section "ne propose PAS" présente.
            assert "scpi" in body
            assert "livret" in body
            assert "mandat" in body or "gestion" in body
            # Phrase d'exclusion explicite.
            assert "ne propose" in body or "à ne pas confondre" in body
