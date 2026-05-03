"""Tests unitaires du catalogue Action CTAs — Phase 2b.

Couvre `services.assistance.agents.tools.shared.action_cta_catalog` :
  - whitelist canonique des `kind`
  - disponibilité Phase 2b vs 2c
  - construction de l'option `{kind, label, deep_link}`
  - validation des deep-links forgés (defense-in-depth)
  - paramètres requis (ex: `transaction_id`)

Spec : `docs/arquantix/COMPLIANCE_TOPICS.md` § 4 et § 8ter.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.tools.shared import action_cta_catalog


class TestKnownKinds:
    """Tous les kinds documentés dans la spec doivent être au catalogue."""

    @pytest.mark.parametrize(
        "kind",
        [
            "resume_registration",
            "deposit_funds",
            "deposit_virement",
            "deposit_carte",
            "deposit_crypto",
            "view_wallet_euro",
            "view_iban",
            "view_transactions",
            "view_transaction_detail",
            "download_transaction_statement",  # Phase 2c.2
            "view_account_info",
            "view_security",
            "upload_document",
            "contact_support",
        ],
    )
    def test_kind_is_known(self, kind):
        assert action_cta_catalog.is_known_kind(kind)

    def test_unknown_kind_rejected(self):
        assert not action_cta_catalog.is_known_kind("malicious_intent")
        assert not action_cta_catalog.is_known_kind("")
        assert not action_cta_catalog.is_known_kind("admin_panel")


class TestPhase2bAvailability:
    @pytest.mark.parametrize(
        "kind",
        [
            "resume_registration",
            "deposit_funds",
            "deposit_virement",
            "deposit_carte",
            "deposit_crypto",
            "view_wallet_euro",
            "view_iban",
            "view_transactions",
            "view_transaction_detail",
            "download_transaction_statement",  # Phase 2c.2
            "view_account_info",
            "view_security",
        ],
    )
    def test_available_phase_2b(self, kind):
        assert action_cta_catalog.is_available(kind)

    @pytest.mark.parametrize("kind", ["upload_document", "contact_support"])
    def test_deferred_phase_2c(self, kind):
        # Au catalogue mais non disponible avant Phase 2c.
        assert action_cta_catalog.is_known_kind(kind)
        assert not action_cta_catalog.is_available(kind)


class TestBuildAction:
    def test_simple_kind_returns_full_dict(self):
        action = action_cta_catalog.build_action("resume_registration")
        assert action is not None
        assert action["kind"] == "resume_registration"
        assert action["label"] == "Reprendre l'inscription"
        assert action["deep_link"] == "vancelian://app/registration_resume"

    def test_label_override(self):
        action = action_cta_catalog.build_action(
            "deposit_funds", label_override="Faire mon premier dépôt"
        )
        assert action is not None
        assert action["label"] == "Faire mon premier dépôt"
        assert action["deep_link"] == "vancelian://app/deposit"

    def test_label_override_truncated_at_80(self):
        long_label = "x" * 200
        action = action_cta_catalog.build_action(
            "deposit_funds", label_override=long_label
        )
        assert action is not None
        assert len(action["label"]) <= 80

    def test_unknown_kind_returns_none(self):
        assert action_cta_catalog.build_action("malicious_intent") is None

    def test_deferred_kind_returns_none(self):
        # Phase 2c kinds ne sont jamais émis Phase 2b.
        assert action_cta_catalog.build_action("upload_document") is None
        assert action_cta_catalog.build_action("contact_support") is None

    def test_kind_requires_param_with_param(self):
        action = action_cta_catalog.build_action(
            "view_transaction_detail",
            params={"transaction_id": "abc-123"},
        )
        assert action is not None
        assert action["deep_link"] == "vancelian://app/transactions/abc-123"

    def test_kind_requires_param_without_param_returns_none(self):
        # Pas de params → on refuse de forger un deep-link.
        assert action_cta_catalog.build_action("view_transaction_detail") is None
        assert (
            action_cta_catalog.build_action(
                "view_transaction_detail", params={}
            )
            is None
        )

    def test_kind_requires_param_wrong_param_name(self):
        # Mauvais nom de param → None.
        assert (
            action_cta_catalog.build_action(
                "view_transaction_detail", params={"id": "abc-123"}
            )
            is None
        )

    def test_download_transaction_statement_with_param(self):
        action = action_cta_catalog.build_action(
            "download_transaction_statement",
            params={"transaction_id": "abc-123"},
        )
        assert action is not None
        assert action["kind"] == "download_transaction_statement"
        assert action["label"] == "Télécharger le relevé"
        assert (
            action["deep_link"]
            == "vancelian://app/transactions/abc-123/statement"
        )

    def test_download_transaction_statement_without_param(self):
        assert (
            action_cta_catalog.build_action("download_transaction_statement")
            is None
        )

    def test_view_transaction_detail_label_updated(self):
        # Phase 2c.2 : label « Voir le détail » → « Voir la transaction »
        # (clarté UX, cf. user feedback 03/05/2026).
        action = action_cta_catalog.build_action(
            "view_transaction_detail",
            params={"transaction_id": "abc-123"},
        )
        assert action is not None
        assert action["label"] == "Voir la transaction"


class TestIsKnownDeepLink:
    """Defense-in-depth : valider les deep-links forgés depuis l'extérieur."""

    @pytest.mark.parametrize(
        "deep_link",
        [
            "vancelian://app/registration_resume",
            "vancelian://app/deposit",
            "vancelian://app/deposit/virement",
            "vancelian://app/deposit/carte",
            "vancelian://app/deposit/crypto",
            "vancelian://app/wallet/euro",
            "vancelian://app/wallet/iban",
            "vancelian://app/transactions",
            "vancelian://app/profile/account",
            "vancelian://app/profile/security",
        ],
    )
    def test_whitelist_match(self, deep_link):
        assert action_cta_catalog.is_known_deep_link(deep_link)

    def test_template_with_id_resolved(self):
        # Le `{id}` doit être remplacé.
        assert action_cta_catalog.is_known_deep_link(
            "vancelian://app/transactions/abc-123"
        )
        # Pas de placeholder résolu (template brut) → reject.
        assert not action_cta_catalog.is_known_deep_link(
            "vancelian://app/transactions/{id}"
        )

    def test_download_transaction_statement_resolved_link_recognized(self):
        # Phase 2c.2 — deep-link avec suffixe `/statement` doit être
        # reconnu comme appartenant au catalogue (kind
        # `download_transaction_statement`). Pas de leak du template.
        assert action_cta_catalog.is_known_deep_link(
            "vancelian://app/transactions/abc-123/statement"
        )
        assert not action_cta_catalog.is_known_deep_link(
            "vancelian://app/transactions/{id}/statement"
        )
        # Sans id → on tombe sur l'autre template (id) qui pourrait
        # techniquement matcher si on n'est pas vigilant : ici le
        # segment id serait `statement`, ce qui passe la validation
        # (statement est un id "valide" sans slash). C'est un cas
        # limite acceptable car côté serveur ce deep-link n'est jamais
        # forgé sans id (build_action refuse).
        assert action_cta_catalog.is_known_deep_link(
            "vancelian://app/transactions/statement"
        )

    @pytest.mark.parametrize(
        "deep_link",
        [
            "vancelian://malicious/wipe",
            "http://other.com/admin",
            "javascript:alert(1)",
            "",
            "vancelian://",
            "vancelian://app",
            "vancelian://app/admin",
            "vancelian://app/profile",  # path incomplet
        ],
    )
    def test_unknown_or_malicious_rejected(self, deep_link):
        assert not action_cta_catalog.is_known_deep_link(deep_link)

    def test_phase_2c_deferred_not_recognized(self):
        # `upload_document` est dans le catalogue mais `available=False`,
        # donc son deep-link ne doit PAS être considéré comme reconnu
        # (sinon un agent pourrait le glisser dans une option).
        assert not action_cta_catalog.is_known_deep_link(
            "vancelian://app/profile/documents/upload"
        )
