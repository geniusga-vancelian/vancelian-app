"""
Rigid Email Block Registry
Defines allowed types, variants, and validators
Extended with slot metadata for optional blocks
"""
from typing import Dict, List, Tuple, Literal, Any, Optional
from dataclasses import dataclass
from .schemas import EmailSpec, Block


# Registry: type -> list of allowed variants
BLOCK_REGISTRY: Dict[str, List[str]] = {
    "HERO": ["image_top", "text_only"],
    "SECTION_TITLE": ["centered"],
    "TEXT": ["body"],
    "BULLETS": ["default"],
    "FEATURE_CARDS": ["3up"],
    "IMAGE": ["contained"],
    "CTA": ["primary"],
    "DIVIDER": ["default"],
    "SPACER": ["md", "lg"],
    "SOCIAL_ICONS": ["default"],
    "FOOTER": ["default"],
}

# Block type display names
BLOCK_TYPE_NAMES = {
    "HERO": "Hero",
    "SECTION_TITLE": "Section Title",
    "TEXT": "Text",
    "BULLETS": "Bullet List",
    "FEATURE_CARDS": "Feature Cards",
    "IMAGE": "Image",
    "CTA": "Call to Action",
    "DIVIDER": "Divider",
    "SPACER": "Spacer",
    "SOCIAL_ICONS": "Social Icons",
    "FOOTER": "Footer",
}

# Max blocks per type
MAX_BLOCKS_PER_TYPE: Dict[str, int] = {
    "HERO": 1,
    "SECTION_TITLE": 3,
    "TEXT": 5,
    "BULLETS": 2,
    "FEATURE_CARDS": 2,
    "IMAGE": 3,
    "CTA": 3,
    "DIVIDER": 2,
    "SPACER": 3,
    "SOCIAL_ICONS": 1,
    "FOOTER": 1,
}

# Total max blocks
MAX_TOTAL_BLOCKS = 10


@dataclass
class BlockDefinition:
    """Block metadata with slot information"""
    type: str
    variant: str
    slot: Literal["core", "optional"] = "core"
    max_occurrences: Optional[int] = None
    editable_props: List[str] = None
    
    def __post_init__(self):
        if self.editable_props is None:
            self.editable_props = []


# Block definitions with slot metadata
# Default: all blocks are "core" unless specified
BLOCK_DEFINITIONS: Dict[Tuple[str, str], BlockDefinition] = {
    # Core blocks (default)
    ("HERO", "image_top"): BlockDefinition(
        type="HERO",
        variant="image_top",
        slot="core",
        editable_props=["title", "subtitle", "image_url", "cta_label", "cta_url"],
    ),
    ("HERO", "text_only"): BlockDefinition(
        type="HERO",
        variant="text_only",
        slot="core",
        editable_props=["title", "subtitle", "cta_label", "cta_url"],
    ),
    ("SECTION_TITLE", "centered"): BlockDefinition(
        type="SECTION_TITLE",
        variant="centered",
        slot="core",
        editable_props=["title", "subtitle"],
    ),
    ("TEXT", "body"): BlockDefinition(
        type="TEXT",
        variant="body",
        slot="core",  # Can be optional in some templates
        editable_props=["heading", "body"],
    ),
    ("BULLETS", "default"): BlockDefinition(
        type="BULLETS",
        variant="default",
        slot="core",
        editable_props=["heading", "items"],
    ),
    ("FEATURE_CARDS", "3up"): BlockDefinition(
        type="FEATURE_CARDS",
        variant="3up",
        slot="core",
        editable_props=["heading", "items"],
    ),
    ("CTA", "primary"): BlockDefinition(
        type="CTA",
        variant="primary",
        slot="core",
        editable_props=["label", "url", "hint"],
    ),
    ("FOOTER", "default"): BlockDefinition(
        type="FOOTER",
        variant="default",
        slot="core",
        editable_props=["company_name", "address", "unsubscribe_url_placeholder"],
    ),
    # Optional blocks
    ("IMAGE", "contained"): BlockDefinition(
        type="IMAGE",
        variant="contained",
        slot="optional",
        max_occurrences=3,
        editable_props=["image_url", "alt_text", "caption"],
    ),
    ("DIVIDER", "default"): BlockDefinition(
        type="DIVIDER",
        variant="default",
        slot="optional",
        max_occurrences=2,
        editable_props=[],
    ),
    ("SPACER", "md"): BlockDefinition(
        type="SPACER",
        variant="md",
        slot="optional",
        max_occurrences=3,
        editable_props=[],
    ),
    ("SPACER", "lg"): BlockDefinition(
        type="SPACER",
        variant="lg",
        slot="optional",
        max_occurrences=3,
        editable_props=[],
    ),
    ("SOCIAL_ICONS", "default"): BlockDefinition(
        type="SOCIAL_ICONS",
        variant="default",
        slot="core",  # Always included in footer modules
        max_occurrences=1,
        editable_props=["links", "size"],
    ),
}


def get_block_definition(block_type: str, variant: str = "default") -> BlockDefinition:
    """Get block definition by type and variant"""
    key = (block_type.upper(), variant)
    if key in BLOCK_DEFINITIONS:
        return BLOCK_DEFINITIONS[key]
    # Fallback to default variant
    default_key = (block_type.upper(), "default")
    if default_key in BLOCK_DEFINITIONS:
        return BLOCK_DEFINITIONS[default_key]
    # Fallback to core with all props editable
    return BlockDefinition(
        type=block_type.upper(),
        variant=variant,
        slot="core",
        editable_props=[],
    )


def get_core_structure(spec: EmailSpec) -> List[Tuple[str, str, str]]:
    """
    Extract core blocks structure from EmailSpec
    Returns list of (type, variant, slot) tuples
    """
    structure = []
    for block in spec.blocks:
        block_type = block.type
        variant = getattr(block, "variant", "default")
        definition = get_block_definition(block_type, variant)
        structure.append((block_type, variant, definition.slot))
    return structure


def get_optional_slots(spec: EmailSpec) -> Dict[str, int]:
    """
    Get allowed optional slots for a template spec
    Returns dict of {block_type: max_occurrences}
    """
    optional_slots = {}
    for block in spec.blocks:
        block_type = block.type.upper()
        variant = getattr(block, "variant", "default")
        definition = get_block_definition(block_type, variant)
        if definition.slot == "optional":
            key = f"{block_type}_{variant}"
            if key not in optional_slots:
                optional_slots[key] = definition.max_occurrences or 999
    return optional_slots


def validate_spec_with_registry(spec: EmailSpec) -> None:
    """
    Validate EmailSpec against rigid registry rules
    Raises ValueError with clear message if invalid
    """
    errors: List[str] = []
    
    # Check theme
    if spec.theme != "arquantix_v1":
        errors.append(f"Invalid theme: {spec.theme}. Only 'arquantix_v1' is allowed.")
    
    # Check total blocks
    if len(spec.blocks) > MAX_TOTAL_BLOCKS:
        errors.append(f"Too many blocks: {len(spec.blocks)}. Maximum {MAX_TOTAL_BLOCKS} allowed.")
    
    if len(spec.blocks) < 2:
        errors.append("At least 2 blocks required (content + footer).")
    
    # Count blocks by type
    block_counts: Dict[str, int] = {}
    block_types: List[str] = []
    
    for i, block in enumerate(spec.blocks):
        block_type = block.type.upper()
        block_types.append(block_type)
        
        # Check if type is in registry
        if block_type not in BLOCK_REGISTRY:
            errors.append(f"Block {i+1}: Unknown block type '{block.type}'. Allowed types: {', '.join(BLOCK_REGISTRY.keys())}")
            continue
        
        # Check variant
        if hasattr(block, 'variant'):
            variant = block.variant
            allowed_variants = BLOCK_REGISTRY[block_type]
            if variant not in allowed_variants:
                errors.append(f"Block {i+1} ({block_type}): Invalid variant '{variant}'. Allowed: {', '.join(allowed_variants)}")
        
        # Count blocks
        block_counts[block_type] = block_counts.get(block_type, 0) + 1
        
        # Check max per type
        max_for_type = MAX_BLOCKS_PER_TYPE.get(block_type, 999)
        if block_counts[block_type] > max_for_type:
            errors.append(f"Too many {BLOCK_TYPE_NAMES.get(block_type, block_type)} blocks: {block_counts[block_type]}. Maximum {max_for_type} allowed.")
    
    # Check hero count
    hero_count = block_counts.get("HERO", 0)
    if hero_count > 1:
        errors.append(f"Maximum 1 Hero block allowed, found {hero_count}.")
    
    # Check footer is last
    if not spec.blocks or spec.blocks[-1].type.upper() != "FOOTER":
        errors.append("Last block must be a FOOTER block.")
    
    # Check footer has unsubscribe placeholder
    if spec.blocks and spec.blocks[-1].type.upper() == "FOOTER":
        footer = spec.blocks[-1]
        if hasattr(footer, 'unsubscribe_url_placeholder'):
            if "{{unsubscribe_url}}" not in footer.unsubscribe_url_placeholder:
                errors.append("Footer must contain {{unsubscribe_url}} placeholder.")
    
    if errors:
        raise ValueError("EmailSpec validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


def get_block_renderer(block_type: str, variant: str = "default") -> str:
    """
    Get renderer function name for block type and variant
    Returns module.function name
    """
    type_lower = block_type.lower()
    variant_lower = variant.lower()
    
    # Map to renderer functions
    renderer_map: Dict[Tuple[str, str], str] = {
        ("hero", "image_top"): "blocks.hero.render_hero",
        ("hero", "text_only"): "blocks.hero.render_hero",
        ("section_title", "centered"): "blocks.section_title.render_section_title",
        ("text", "body"): "blocks.text.render_text",
        ("bullets", "default"): "blocks.bullets.render_bullets",
        ("feature_cards", "3up"): "blocks.feature_cards.render_feature_cards",
        ("image", "contained"): "blocks.image.render_image",
        ("cta", "primary"): "blocks.cta.render_cta",
        ("divider", "default"): "blocks.divider.render_divider",
        ("spacer", "md"): "blocks.spacer.render_spacer",
        ("spacer", "lg"): "blocks.spacer.render_spacer",
        ("footer", "default"): "blocks.footer.render_footer",
    }
    
    key = (type_lower, variant_lower)
    if key in renderer_map:
        return renderer_map[key]
    
    # Fallback to default variant
    default_key = (type_lower, "default")
    if default_key in renderer_map:
        return renderer_map[default_key]
    
    raise ValueError(f"No renderer found for block type '{block_type}' variant '{variant}'")


def get_registry_info() -> Dict[str, Any]:
    """Get registry information for system prompt"""
    return {
        "allowed_types": list(BLOCK_REGISTRY.keys()),
        "variants": BLOCK_REGISTRY,
        "max_blocks": MAX_TOTAL_BLOCKS,
        "max_per_type": MAX_BLOCKS_PER_TYPE,
    }

