"""Parcours d’activation client — modèle dynamique, pondération, états UX."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database import Person
from services.portfolio_engine.clients.models import Client

from .resume_logic import should_show_registration_resume
from .signals import has_first_deposit, has_first_investment

ACTIVATION_JOURNEY_CONFIG_VERSION = 3

WEIGHT_ACCOUNT = 0.7
WEIGHT_DEPOSIT = 0.2
WEIGHT_INVEST = 0.1

_STAGE_KEYS = ("account_verification", "first_deposit", "first_investment")
_STAGE_WEIGHTS = (WEIGHT_ACCOUNT, WEIGHT_DEPOSIT, WEIGHT_INVEST)


def _registration_ratio_for_weighting(profile_dict: Dict[str, Any]) -> float:
    """Ratio 0..1 depuis le moteur d’inscription (jalons dérivés ou ratios admin)."""
    r = profile_dict.get("registration_derived_completion_ratio")
    if isinstance(r, (int, float)) and 0 <= float(r) <= 1:
        return float(r)
    p = profile_dict.get("registration_derived_progress_percent")
    if isinstance(p, int) and 0 <= p <= 100:
        return p / 100.0
    if isinstance(p, float) and 0 <= p <= 100:
        return p / 100.0
    ratio = profile_dict.get("registration_completion_ratio")
    if isinstance(ratio, (int, float)) and 0 <= float(ratio) <= 1:
        return float(ratio)
    return 0.0


def _next_step_index(account_ok: bool, deposit_ok: bool, invest_ok: bool) -> Optional[int]:
    if not account_ok:
        return 0
    if not deposit_ok:
        return 1
    if not invest_ok:
        return 2
    return None


def _stage_ux_status_v3(
    *,
    index: int,
    account_ok: bool,
    deposit_ok: bool,
    invest_ok: bool,
    next_idx: Optional[int],
    reg_ratio: float,
    reg_incomplete: bool,
) -> str:
    """``completed`` | ``locked`` | ``available`` | ``in_progress`` (v3).

    - **completed** : étape satisfaite.
    - **locked** : prérequis non remplis (étapes suivantes du funnel).
    - **available** : prérequis OK, étape accessible mais pas encore entamée (dépôt / invest
      ; ou inscription non commencée pour l’étape 1).
    - **in_progress** : étape 1 uniquement — inscription entamée (ratio strictement entre 0 et 1,
      ou ratio ≥ 1 mais parcours encore considéré incomplet).
    """
    completes = (account_ok, deposit_ok, invest_ok)
    if completes[index]:
        return "completed"
    if next_idx is None:
        return "completed"
    if index < next_idx:
        return "completed"
    if index > next_idx:
        return "locked"
    # index == next_idx : prochaine action
    if index == 0:
        if not reg_incomplete:
            return "completed"
        if 0 < reg_ratio < 1:
            return "in_progress"
        if reg_ratio >= 1.0 and reg_incomplete:
            return "in_progress"
        return "available"
    # first_deposit / first_investment : accessibles, pas encore faits
    return "available"


def _remaining_steps_message(remaining: int) -> str:
    if remaining <= 0:
        return ""
    if remaining == 1:
        return "Une dernière étape"
    if remaining == 2:
        return "Encore deux étapes"
    return f"Encore {remaining} étapes"


def build_activation_journey(
    db: Session,
    *,
    person: Optional[Person],  # noqa: ARG001
    client: Client,
    profile_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Bloc ``activation_journey`` pour le profil mobile (pondération + états UX)."""
    reg_incomplete = should_show_registration_resume(
        client_status=profile_dict.get("client_status"),
        registration_macro_stage=profile_dict.get("registration_macro_stage"),
        registration_completion_ratio=profile_dict.get("registration_completion_ratio"),
        registration_derived_total_count=profile_dict.get("registration_derived_total_count"),
        registration_derived_completed_count=profile_dict.get(
            "registration_derived_completed_count"
        ),
        registration_missing_steps=profile_dict.get("registration_missing_steps"),
        registration_derived_next_step_key=profile_dict.get("registration_derived_next_step_key"),
        registration_derived_progress_percent=profile_dict.get(
            "registration_derived_progress_percent"
        ),
    )
    account_ok = not reg_incomplete
    deposit_ok = has_first_deposit(db, client)
    invest_ok = has_first_investment(db, client)

    reg_ratio = _registration_ratio_for_weighting(profile_dict)

    if not account_ok:
        weighted = WEIGHT_ACCOUNT * reg_ratio
    else:
        weighted = WEIGHT_ACCOUNT
        if deposit_ok:
            weighted += WEIGHT_DEPOSIT
        if invest_ok:
            weighted += WEIGHT_INVEST
    weighted_percent = min(100, max(0, int(round(weighted * 100))))

    next_idx = _next_step_index(account_ok, deposit_ok, invest_ok)
    completes = (account_ok, deposit_ok, invest_ok)
    remaining = sum(1 for c in completes if not c)

    primary_cta_label: Optional[str] = None
    primary_route: Optional[str] = None
    if next_idx == 0:
        primary_cta_label = "Continuer votre profil"
        primary_route = "registration_resume"
    elif next_idx == 1:
        primary_cta_label = "Alimenter mon compte"
        primary_route = "deposit"
    elif next_idx == 2:
        primary_cta_label = "Investir maintenant"
        primary_route = "invest_crypto"

    next_lbl = profile_dict.get("registration_derived_next_step_label")
    pct = profile_dict.get("registration_derived_progress_percent")
    sub_verify = "Quelques informations suffisent pour sécuriser votre profil."
    if not account_ok:
        parts: List[str] = []
        if isinstance(pct, int) and pct > 0:
            parts.append(f"Déjà {pct} %")
        if isinstance(next_lbl, str) and next_lbl.strip():
            parts.append(next_lbl.strip())
        if parts:
            sub_verify = " · ".join(parts)

    titles = (
        "Sécuriser votre profil",
        "Alimenter votre compte",
        "Votre premier investissement",
    )
    default_subs = (
        sub_verify,
        "Un versement pour ouvrir l’investissement.",
        "Faites fructifier votre épargne en quelques gestes.",
    )
    routes = ("registration_resume", "deposit", "invest_crypto")

    row_cta_labels = [
        "Continuer votre profil" if not account_ok else "C’est fait",
        "Alimenter mon compte" if not deposit_ok else "C’est fait",
        "Investir maintenant" if not invest_ok else "C’est fait",
    ]

    stages: List[Dict[str, Any]] = []
    for i, key in enumerate(_STAGE_KEYS):
        c = completes[i]
        st = _stage_ux_status_v3(
            index=i,
            account_ok=account_ok,
            deposit_ok=deposit_ok,
            invest_ok=invest_ok,
            next_idx=next_idx,
            reg_ratio=reg_ratio,
            reg_incomplete=reg_incomplete,
        )
        is_next = next_idx is not None and i == next_idx
        stages.append(
            {
                "key": key,
                "id": key,
                "status": st,
                "weight": _STAGE_WEIGHTS[i],
                "is_next_step": is_next,
                "title": titles[i],
                "subtitle": default_subs[i],
                "cta_label": row_cta_labels[i],
                "target_route": routes[i],
            }
        )

    show = not (account_ok and deposit_ok and invest_ok)
    all_done = account_ok and deposit_ok and invest_ok

    # Priorité : URL injectée dans le profil (CMS / admin) > variable d’environnement.
    _hero_cms = (profile_dict.get("activation_journey_hero_image_url") or "").strip()
    _hero_env = (os.environ.get("ACTIVATION_JOURNEY_HERO_IMAGE_URL") or "").strip()
    hero_image_url = _hero_cms or _hero_env or None

    return {
        "config_version": ACTIVATION_JOURNEY_CONFIG_VERSION,
        "show_module": show,
        "activation_complete": all_done,
        "completion_message": "Tout est en place" if all_done else None,
        "weighted_progress_percent": weighted_percent,
        "headline": "Trois étapes pour investir en toute confiance",
        "hero_subtitle": "Simple, rapide, sans friction — tout est prêt pour la suite.",
        "hero_image_url": hero_image_url,
        "remaining_steps_message": _remaining_steps_message(remaining),
        "primary_cta_label": primary_cta_label if show and next_idx is not None else None,
        "primary_cta_target_route": primary_route if show and next_idx is not None else None,
        "stages": stages,
    }
