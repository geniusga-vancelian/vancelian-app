"""Minimal field validators for registration submit.

Validates basic formats to prevent aberrant data. Not a full validation engine.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
COUNTRY_ISO2_RE = re.compile(r"^[A-Za-z]{2}$")


class FieldValidationError:
    """A single field validation error."""
    def __init__(self, slug: str, message: str):
        self.slug = slug
        self.message = message


def validate_country_iso2_value(binding_slug: str, value: Any) -> Optional[FieldValidationError]:
    """Strict ISO 3166-1 alpha-2 for composite address country bindings."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return FieldValidationError(
            binding_slug,
            f"Country must be a 2-letter ISO code (string), got {type(value).__name__}",
        )
    s = value.strip()
    if not COUNTRY_ISO2_RE.match(s):
        return FieldValidationError(
            binding_slug,
            f"Country must be exactly 2 letters (ISO 3166-1 alpha-2), got {value!r}",
        )
    return None


def validate_field_value(
    component_type: str,
    binding_slug: str,
    value: Any,
    props: Optional[Dict] = None,
) -> Optional[FieldValidationError]:
    """Validate a single field value based on component_type.

    Returns None if valid, or a FieldValidationError if invalid.
    """
    if value is None or value == "" or value == []:
        return None

    props = props or {}

    if component_type == "text_input":
        if binding_slug and "email" in binding_slug:
            if isinstance(value, str) and not EMAIL_RE.match(value):
                return FieldValidationError(binding_slug, f"Invalid email format: {value}")

    if component_type == "date_picker":
        if isinstance(value, str):
            try:
                if "/" in value:
                    datetime.strptime(value, "%d/%m/%Y")
                else:
                    datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return FieldValidationError(binding_slug, f"Invalid date format: {value}")

    if component_type == "select":
        options = props.get("options", [])
        if options and isinstance(value, str):
            valid_values = [o.get("value") for o in options if isinstance(o, dict)]
            if valid_values and value not in valid_values:
                return FieldValidationError(
                    binding_slug,
                    f"Invalid option '{value}'. Valid: {valid_values}",
                )

    if component_type == "multi_select":
        options = props.get("options", [])
        if options and isinstance(value, list):
            valid_values = set(o.get("value") for o in options if isinstance(o, dict))
            if valid_values:
                invalid = [v for v in value if v not in valid_values]
                if invalid:
                    return FieldValidationError(
                        binding_slug,
                        f"Invalid options: {invalid}. Valid: {sorted(valid_values)}",
                    )

    if component_type == "checkbox":
        if not isinstance(value, bool):
            return FieldValidationError(
                binding_slug,
                f"Checkbox value must be boolean, got {type(value).__name__}",
            )

    return None


def validate_screen_answers(
    components: list,
    answers: Dict[str, Any],
) -> List[FieldValidationError]:
    """Validate all answers against their component definitions.

    `components` should be SQLAlchemy RegistrationScreenComponent objects.
    """
    from .address_autocomplete import (
        resolved_address_step_binding_slugs,
        resolved_binding_slugs,
    )

    errors = []
    for comp in components:
        if comp.component_type == "address_autocomplete":
            props = comp.props_json or {}
            for logical, slug in resolved_binding_slugs(props).items():
                if slug not in answers:
                    continue
                value = answers[slug]
                if logical == "country":
                    err = validate_country_iso2_value(slug, value)
                    if err:
                        errors.append(err)
                    continue
                err = validate_field_value("text_input", slug, value, props)
                if err:
                    errors.append(err)
            continue
        if comp.component_type == "address_step":
            props = comp.props_json or {}
            line2_opt = props.get("address_line_2_optional", True)
            for logical, slug in resolved_address_step_binding_slugs(props).items():
                if slug not in answers:
                    continue
                value = answers[slug]
                if logical == "country_of_residence":
                    err = validate_country_iso2_value(slug, value)
                    if err:
                        errors.append(err)
                    continue
                if logical == "address_line_2" and line2_opt:
                    if value is None or value == "":
                        continue
                err = validate_field_value("text_input", slug, value, props)
                if err:
                    errors.append(err)
            continue
        slug = comp.binding_slug
        if not slug or slug not in answers:
            continue
        value = answers[slug]
        props = comp.props_json or {}
        error = validate_field_value(comp.component_type, slug, value, props)
        if error:
            errors.append(error)
    return errors
