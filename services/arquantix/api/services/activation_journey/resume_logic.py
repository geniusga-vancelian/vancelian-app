"""Aligné sur ``MobileAppProfile.shouldShowRegistrationResume`` (Flutter)."""
from __future__ import annotations

from typing import List, Optional


def should_show_registration_resume(
    *,
    client_status: Optional[str],
    registration_macro_stage: Optional[str],
    registration_completion_ratio: Optional[float],
    registration_derived_total_count: Optional[int],
    registration_derived_completed_count: Optional[int],
    registration_missing_steps: Optional[List[str]],
    registration_derived_next_step_key: Optional[str],
    registration_derived_progress_percent: Optional[int],
) -> bool:
    """True si le parcours d’inscription / vérification compte doit encore être proposé."""
    status = (client_status or "").strip().upper()
    if status == "ACTIVE":
        td = registration_derived_total_count
        dc = registration_derived_completed_count
        if td is not None and td > 0 and dc is not None and dc < td:
            return True
        missing = registration_missing_steps
        if missing and len(missing) > 0:
            return True
        next_key = registration_derived_next_step_key
        if next_key and next_key.strip():
            dp = registration_derived_progress_percent
            if dp is not None and dp >= 100 and (not missing or len(missing) == 0):
                pass
            else:
                return True
        macro = (registration_macro_stage or "").strip().lower()
        if macro and macro != "active_client":
            return True
        r = registration_completion_ratio
        if r is not None and r < 0.999:
            return True
        dp = registration_derived_progress_percent
        if dp is not None and dp < 100:
            return True
        return False

    td = registration_derived_total_count
    dc = registration_derived_completed_count
    if td is not None and td > 0 and dc is not None and dc < td:
        return True

    if status == "PARTIAL":
        return True

    if registration_missing_steps and len(registration_missing_steps) > 0:
        return True

    next_key = registration_derived_next_step_key
    if next_key and next_key.strip():
        return True

    macro_norm = (registration_macro_stage or "").strip().lower()
    if macro_norm and macro_norm != "active_client":
        return True

    r = registration_completion_ratio
    if r is not None and r < 0.999:
        return True

    dp = registration_derived_progress_percent
    if dp is not None and dp < 100:
        return True

    return False
