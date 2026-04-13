"""
Structure locking for email templates
Enforces locked structure when iterating on templates
Extended with optional slots support
"""
from typing import List, Tuple, Optional, Dict
from .schemas import EmailSpec, Block
from .registry import validate_spec_with_registry, get_block_definition, get_core_structure, get_optional_slots


def extract_structure(spec: EmailSpec) -> List[Tuple[str, str]]:
    """
    Extract structure (type, variant) from EmailSpec
    Returns list of (type, variant) tuples
    """
    structure = []
    for block in spec.blocks:
        block_type = block.type
        variant = getattr(block, "variant", "default")
        structure.append((block_type, variant))
    return structure


def enforce_locked_structure(
    base: EmailSpec,
    proposed: EmailSpec,
) -> Tuple[EmailSpec, List[str]]:
    """
    Enforce locked structure from base spec onto proposed spec
    Extended to support optional slots
    
    Rules:
    - Core blocks: structure (type+variant, order, count) must match base
    - Optional blocks: can be added/removed if slot="optional" and max_occurrences respected
    - Copy compatible props from proposed to base blocks
    - If props missing, keep base props
    - Always revalidate via registry
    
    Returns:
        (final_spec, warnings)
    """
    warnings: List[str] = []
    
    # Extract core structure (type, variant, slot)
    base_core_structure = get_core_structure(base)
    proposed_structure = extract_structure(proposed)
    
    # Separate core and optional blocks in base
    base_core_blocks: List[Tuple[int, Block, str]] = []  # (index, block, slot)
    base_optional_blocks: List[Tuple[int, Block]] = []  # (index, block)
    
    for i, block in enumerate(base.blocks):
        block_type = block.type
        variant = getattr(block, "variant", "default")
        definition = get_block_definition(block_type, variant)
        if definition.slot == "core":
            base_core_blocks.append((i, block, definition.slot))
        else:
            base_optional_blocks.append((i, block))
    
    # Build final blocks preserving core structure
    final_blocks: List[Block] = []
    proposed_index = 0
    base_core_index = 0
    
    # Track optional blocks added from proposed
    optional_added: Dict[str, int] = {}  # {block_type_variant: count}
    
    # Process core blocks first (must match base order)
    for base_idx, base_block, slot in base_core_blocks:
        block_type = base_block.type
        variant = getattr(base_block, "variant", "default")
        
        # Find matching proposed block
        proposed_block = None
        while proposed_index < len(proposed.blocks):
            prop_block = proposed.blocks[proposed_index]
            prop_type = prop_block.type
            prop_variant = getattr(prop_block, "variant", "default")
            
            # Check if this is the matching core block
            if prop_type == block_type and prop_variant == variant:
                proposed_block = prop_block
                proposed_index += 1
                break
            else:
                # Check if it's an optional block we can insert
                prop_def = get_block_definition(prop_type, prop_variant)
                if prop_def.slot == "optional":
                    # Check if we can add this optional block
                    key = f"{prop_type}_{prop_variant}"
                    current_count = optional_added.get(key, 0)
                    max_occ = prop_def.max_occurrences or 999
                    
                    if current_count < max_occ:
                        # Add optional block before this core block
                        final_blocks.append(prop_block)
                        optional_added[key] = current_count + 1
                        proposed_index += 1
                    else:
                        warnings.append(f"Ignored extra {prop_type.upper()} block (max={max_occ})")
                        proposed_index += 1
                else:
                    # Core block mismatch - skip it
                    warnings.append(f"Reordered blocks: ignored {prop_type.upper()} at wrong position")
                    proposed_index += 1
        
        # Merge base + proposed for core block
        final_block = _merge_block(base_block, proposed_block, block_type, variant)
        final_blocks.append(final_block)
        base_core_index += 1
    
    # Process remaining optional blocks from proposed (before footer)
    while proposed_index < len(proposed.blocks):
        prop_block = proposed.blocks[proposed_index]
        prop_type = prop_block.type
        prop_variant = getattr(prop_block, "variant", "default")
        prop_def = get_block_definition(prop_type, prop_variant)
        
        if prop_def.slot == "optional":
            key = f"{prop_type}_{prop_variant}"
            current_count = optional_added.get(key, 0)
            max_occ = prop_def.max_occurrences or 999
            
            if current_count < max_occ:
                final_blocks.append(prop_block)
                optional_added[key] = current_count + 1
            else:
                warnings.append(f"Ignored extra {prop_type.upper()} block (max={max_occ})")
        else:
            # Core block that doesn't match - ignore
            warnings.append(f"Cannot add core block {prop_type.upper()} - structure locked")
        
        proposed_index += 1
    
    # Ensure footer is last
    if final_blocks and final_blocks[-1].type != "footer":
        # Find footer in base
        footer_block = base.blocks[-1]
        if footer_block.type == "footer":
            # Remove footer if it's elsewhere
            final_blocks = [b for b in final_blocks if b.type != "footer"]
            final_blocks.append(footer_block)
    
    # Build final spec
    final_spec = EmailSpec(
        subject=proposed.subject if proposed.subject else base.subject,
        preheader=proposed.preheader if proposed.preheader is not None else base.preheader,
        locale=proposed.locale,
        theme=base.theme,  # Always use base theme
        blocks=final_blocks,
    )
    
    # Revalidate
    try:
        validate_spec_with_registry(final_spec)
    except ValueError as e:
        warnings.append(f"Registry validation warning: {str(e)}")
        # Fallback to base spec if validation fails
        return base, warnings + [f"Validation failed, using base spec: {str(e)}"]
    
    return final_spec, warnings


def _merge_block(
    base_block: Block,
    proposed_block: Optional[Block],
    block_type: str,
    variant: str,
) -> Block:
    """
    Merge base block with proposed block props
    Keeps base structure, updates only editable props from definition
    """
    if not proposed_block:
        return base_block
    
    # Get block definition to know editable props
    definition = get_block_definition(block_type, variant)
    editable_props = definition.editable_props
    
    # Get base block dict
    base_dict = base_block.model_dump()
    
    # Get proposed block dict (only compatible fields)
    proposed_dict = proposed_block.model_dump()
    
    # Merge: use proposed props if they exist and are editable
    # Keep base props for structure-critical fields (type, variant)
    merged_dict = base_dict.copy()
    
    # Update only editable props
    for field in editable_props:
        if field in proposed_dict and proposed_dict[field] is not None:
            merged_dict[field] = proposed_dict[field]
    
    # Ensure type and variant are correct
    merged_dict["type"] = block_type
    merged_dict["variant"] = variant
    
    # Reconstruct block from merged dict
    from .schemas import (
        HeroBlock,
        SectionTitleBlock,
        TextBlock,
        BulletsBlock,
        FeatureCardsBlock,
        ImageBlock,
        CtaBlock,
        DividerBlock,
        SpacerBlock,
        FooterBlock,
    )
    
    block_classes = {
        "hero": HeroBlock,
        "section_title": SectionTitleBlock,
        "text": TextBlock,
        "bullets": BulletsBlock,
        "feature_cards": FeatureCardsBlock,
        "image": ImageBlock,
        "cta": CtaBlock,
        "divider": DividerBlock,
        "spacer": SpacerBlock,
        "footer": FooterBlock,
    }
    
    block_class = block_classes[block_type]
    return block_class(**merged_dict)

