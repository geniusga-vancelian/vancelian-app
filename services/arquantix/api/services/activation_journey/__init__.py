"""Parcours d’activation client (Home) — 3 macro-étapes."""
from .build import ACTIVATION_JOURNEY_CONFIG_VERSION, build_activation_journey
from .resume_logic import should_show_registration_resume
from .signals import has_first_deposit, has_first_investment

__all__ = [
    "ACTIVATION_JOURNEY_CONFIG_VERSION",
    "build_activation_journey",
    "should_show_registration_resume",
    "has_first_deposit",
    "has_first_investment",
]
