"""Repositories introspectifs des agents — Phase 2a.

Cf. `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 5.2 (sécurité matérielle
tipping-off : la frontière de filtrage est ici, **pas** dans le prompt).

Convention :

  - Chaque repo expose des fonctions sync `fetch_*(...)` qui prennent une
    `Session` SQLAlchemy ouverte en argument.
  - Aucune fonction de repo ne lève d'exception non-attendue : tous les
    fail-cases sont traduits en valeurs par défaut neutres (un agent ne
    doit jamais planter sur une donnée manquante).
  - Aucune valeur sensible (`risk_score`, `level`, `deny_reason`,
    `watchlist_match`, etc.) n'est jamais retournée. La traduction se
    fait dans le repo, pas chez le caller.
"""

from __future__ import annotations

from services.assistance.agents.repositories import compliance_repo, product_repo

__all__ = ["compliance_repo", "product_repo"]
