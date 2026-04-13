"""Classification des données pour le chiffrement applicatif (Tier 1)."""
from __future__ import annotations

# Niveaux (audit, politique de clé — même DEK Tier 1, séparation logique)
CLASS_HIGH_SENSITIVE = "HIGH_SENSITIVE"  # email, téléphone, KYC, adresse
CLASS_MEDIUM = "MEDIUM"  # métadonnées, champs secondaires

# Champs typés (documentation + routage futur multi-clé)
HIGH_SENSITIVE_FIELDS = frozenset(
    {
        "email",
        "phone",
        "phone_e164",
        "kyc",
        "address",
        "street",
        "postal_code",
        "city",
        "country",
    }
)

MEDIUM_SENSITIVE_FIELDS = frozenset({"metadata", "profile_fragment", "notes"})
