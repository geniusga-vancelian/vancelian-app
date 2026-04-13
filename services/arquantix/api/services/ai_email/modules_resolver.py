"""
Module resolver for Email Builder
Loads EmailModule and EmailModuleI18n from database and returns EmailSpec
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import sys
from pathlib import Path
api_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(api_dir))
from database import EmailModule, EmailModuleI18n, EmailTemplateEntity, EmailStatusEnum, TranslationStatusEnum
from .schemas import EmailSpec
import json


def get_module_spec(
    db: Session,
    module_id: str,
    locale: str,
    default_locale: str = "fr"
) -> Optional[EmailSpec]:
    """
    Get module spec, with locale fallback
    
    Steps:
    1. Fetch EmailModule by id
    2. If locale != default_locale:
       - Try EmailModuleI18n where (moduleId, locale) -> use its spec if exists and APPROVED/MACHINE
       - Else fallback to module.spec (base)
    3. Return spec JSON parsed into EmailSpec
    
    Handles both:
    - Full EmailSpec (with subject and blocks)
    - Single block (wrapped in EmailSpec)
    
    Args:
        db: SQLAlchemy session
        module_id: UUID of EmailModule
        locale: Target locale
        default_locale: Default locale (usually "fr")
    
    Returns:
        EmailSpec or None if module not found
    """
    def _normalize_spec(spec_dict: dict) -> EmailSpec:
        """Normalize spec dict to EmailSpec - handles both full specs and single blocks"""
        # Check if it's already a full EmailSpec (has subject and blocks)
        if "subject" in spec_dict and "blocks" in spec_dict:
            return EmailSpec(**spec_dict)
        
        # Otherwise, it's a single block - wrap it in EmailSpec
        # Check if it has a "type" field (indicating it's a block)
        if "type" in spec_dict:
            from .schemas import FooterBlock, SpacerBlock
            # Create EmailSpec with the single block
            # For header/footer modules, ensure footer is last and at least 2 blocks
            block_type = spec_dict.get("type")
            blocks = [spec_dict]  # Single block
            
            # EmailSpec requires at least 2 blocks
            # If it's a footer, add a spacer before it
            if block_type == "footer":
                blocks.insert(0, SpacerBlock(variant="md").model_dump())
            # If it's not a footer, add a footer to satisfy EmailSpec validation
            else:
                blocks.append(FooterBlock(
                    company_name="Arquantix",
                    unsubscribe_url_placeholder="{{unsubscribe_url}}"
                ).model_dump())
            
            return EmailSpec(
                subject="Email Subject",
                preheader=None,
                locale=locale,
                theme="arquantix_v1",
                blocks=blocks
            )
        
        # Fallback: try to create EmailSpec as-is (might fail)
        return EmailSpec(**spec_dict)
    
    # Load base module
    module = db.query(EmailModule).filter(EmailModule.id == module_id).first()
    if not module:
        return None
    
    # Check if module is VALIDATED
    if module.status != EmailStatusEnum.VALIDATED:
        # For non-validated modules, always use base spec
        spec_dict = module.spec
        if isinstance(spec_dict, str):
            spec_dict = json.loads(spec_dict)
        return _normalize_spec(spec_dict)
    
    # If locale is default, use base spec
    if locale == default_locale:
        spec_dict = module.spec
        if isinstance(spec_dict, str):
            spec_dict = json.loads(spec_dict)
        return _normalize_spec(spec_dict)
    
    # Try to load translation
    # Note: EmailModuleI18n uses module_id (not moduleId) in SQLAlchemy
    translation = db.query(EmailModuleI18n).filter(
        and_(
            EmailModuleI18n.module_id == module_id,
            EmailModuleI18n.locale == locale
        )
    ).first()
    
    if translation:
        # Use translation if available (MACHINE or APPROVED)
        if translation.translation_status in [TranslationStatusEnum.MACHINE, TranslationStatusEnum.APPROVED]:
            spec_dict = translation.spec
            if isinstance(spec_dict, str):
                spec_dict = json.loads(spec_dict)
            return _normalize_spec(spec_dict)
    
    # Fallback to base spec
    spec_dict = module.spec
    if isinstance(spec_dict, str):
        spec_dict = json.loads(spec_dict)
    return _normalize_spec(spec_dict)


def get_template_entity(db: Session, template_id: str) -> Optional[EmailTemplateEntity]:
    """
    Get EmailTemplateEntity by slug (template_id)
    
    Args:
        db: SQLAlchemy session
        template_id: Slug of template
    
    Returns:
        EmailTemplateEntity or None
    """
    return db.query(EmailTemplateEntity).filter(
        EmailTemplateEntity.slug == template_id
    ).first()


def get_template_modules(
    db: Session,
    template_entity: EmailTemplateEntity,
    locale: str
) -> tuple[Optional[EmailSpec], Optional[EmailSpec], list[EmailSpec]]:
    """
    Resolve all modules for a template
    
    Returns:
        (header_spec, footer_spec, fixed_specs[])
    """
    header_spec = get_module_spec(db, template_entity.header_module_id, locale)
    footer_spec = get_module_spec(db, template_entity.footer_module_id, locale)
    
    fixed_specs: list[EmailSpec] = []
    if template_entity.fixed_module_ids:
        fixed_module_ids = template_entity.fixed_module_ids
        if isinstance(fixed_module_ids, list):
            for fixed_id in fixed_module_ids:
                fixed_spec = get_module_spec(db, fixed_id, locale)
                if fixed_spec:
                    fixed_specs.append(fixed_spec)
    
    return header_spec, footer_spec, fixed_specs

