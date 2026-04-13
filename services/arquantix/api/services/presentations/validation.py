"""Validation content_json contre schema_json (JSON Schema)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError


class SlideContentValidationError(ValueError):
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []


def validate_content_against_schema(
    schema: Optional[Mapping[str, Any]],
    content: Optional[Mapping[str, Any]],
) -> None:
    if not schema:
        return
    instance = content if content is not None else {}
    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errs:
        messages = [e.message for e in errs[:12]]
        raise SlideContentValidationError(
            "content_json ne respecte pas schema_json du template",
            errors=messages,
        )
