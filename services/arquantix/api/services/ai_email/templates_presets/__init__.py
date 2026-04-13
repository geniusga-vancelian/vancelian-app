"""
Rigid email templates presets
Pre-built email structures with locked layouts
"""
from .types import EmailTemplate, register_template, get_template, list_templates, get_default_template_id

# Import templates to register them
from . import arquantix_v1  # noqa: F401

__all__ = [
    "EmailTemplate",
    "register_template",
    "get_template",
    "list_templates",
    "get_default_template_id",
]
