"""Field slug normalization helpers for Registration Engine.

field_definitions uses kebab-case (e.g. 'first-name')
registration components use snake_case (e.g. 'first_name')
"""


def normalize_to_snake(slug: str) -> str:
    """Convert any slug format to snake_case."""
    if not slug:
        return slug
    return slug.replace("-", "_").lower()


def normalize_to_kebab(slug: str) -> str:
    """Convert any slug format to kebab-case."""
    if not slug:
        return slug
    return slug.replace("_", "-").lower()


def are_field_slugs_equivalent(slug_a: str, slug_b: str) -> bool:
    """Check if two field slugs refer to the same field regardless of format."""
    if not slug_a or not slug_b:
        return False
    return normalize_to_snake(slug_a) == normalize_to_snake(slug_b)
