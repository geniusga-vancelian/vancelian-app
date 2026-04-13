"""
Email Template types and registry
"""
from dataclasses import dataclass
from typing import List, Optional, Callable
from ..schemas import EmailSpec


@dataclass
class EmailTemplate:
    """
    Rigid email template with locked structure
    """
    id: str
    name: str
    description: str
    locale_defaults: Optional[List[str]] = None
    initial_spec: Optional[EmailSpec] = None
    initial_spec_builder: Optional[Callable[[str], EmailSpec]] = None
    locked: bool = True
    
    def get_initial_spec(self, locale: str = "en") -> EmailSpec:
        """
        Get initial EmailSpec for this template
        Uses initial_spec if provided, otherwise calls initial_spec_builder
        """
        if self.initial_spec:
            # Clone the spec and update locale
            spec_dict = self.initial_spec.model_dump()
            spec_dict["locale"] = locale
            return EmailSpec(**spec_dict)
        elif self.initial_spec_builder:
            return self.initial_spec_builder(locale)
        else:
            raise ValueError(f"Template {self.id} has no initial_spec or builder")


# Global registry of templates
_TEMPLATES: dict[str, EmailTemplate] = {}


def register_template(template: EmailTemplate) -> None:
    """Register a template in the global registry"""
    _TEMPLATES[template.id] = template


def get_template(template_id: str) -> EmailTemplate:
    """Get template by ID, raises KeyError if not found"""
    if template_id not in _TEMPLATES:
        raise KeyError(f"Template '{template_id}' not found")
    return _TEMPLATES[template_id]


def list_templates() -> List[EmailTemplate]:
    """List all registered templates"""
    return list(_TEMPLATES.values())


def get_default_template_id() -> str:
    """Get default template ID"""
    return "welcome_v1"









