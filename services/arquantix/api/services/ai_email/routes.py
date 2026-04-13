"""
FastAPI routes for AI Email Builder
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from sqlalchemy.orm import Session
import os
import httpx
import sys
from pathlib import Path
# Add api directory to path for auth import
api_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(api_dir))
from auth import get_current_user, AdminUser
from .schemas import (
    ComposeEmailRequest,
    ComposeEmailResponse,
    TranscribeAudioResponse,
    EmailSpec
)
from .schemas_ugg import (
    ComposeEmailUGGRequest,
    ComposeEmailUGGResponse,
    EmailSpecUGG
)
from .agent import compose_email_spec
from .agent_ugg import compose_email_spec_ugg
from .render import build_mjml, compile_mjml
from .templates_mjml.render_ugg import render_ugg_mjml
from .templates_presets import list_templates, get_default_template_id
from .assemble import assemble_email
# Import modules_resolver conditionally to avoid errors if EmailModule doesn't exist
try:
    from .modules_resolver import get_module_spec, get_template_entity, get_template_modules
    from database import get_db, EmailStatusEnum
    MODULES_RESOLVER_AVAILABLE = True
except ImportError:
    # EmailModule and related classes may not exist yet
    MODULES_RESOLVER_AVAILABLE = False
    get_module_spec = None
    get_template_entity = None
    get_template_modules = None
    EmailStatusEnum = None

from database import get_db

router = APIRouter(prefix="/api/ai", tags=["ai-email"])


@router.get("/email/templates")
async def list_email_templates(
    current_user: AdminUser = Depends(get_current_user),
    show_legacy: bool = False
):
    """
    List all available email templates
    Returns only arquantix_ugg_v1 by default, or all templates if show_legacy=true
    """
    if show_legacy and os.getenv("SHOW_LEGACY_TEMPLATES", "false").lower() == "true":
        # Return all templates (legacy mode)
        templates = list_templates()
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "locked": t.locked,
            }
            for t in templates
        ]
    else:
        # Return only arquantix_ugg_v1
        return [
            {
                "id": "arquantix_ugg_v1",
                "name": "Arquantix UGG v1",
                "description": "Single golden template based on UGG-style MJML. AI generates JSON only.",
                "locked": False,
            }
        ]


@router.post("/email/compose", response_model=ComposeEmailResponse)
async def compose_email(
    request: ComposeEmailRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compose email from prompt using OpenAI
    Supports both hardcoded templates and DB templates with imposed modules
    
    Returns EmailSpec, MJML, and compiled HTML
    """
    
    try:
        # Validate prompt length
        if len(request.prompt) > 2000:
            raise HTTPException(status_code=400, detail="Prompt too long (max 2000 chars)")
        
        template_source = request.templateSource or "hardcoded"
        warnings: list[str] = []
        
        # Route 1: DB Template (with imposed modules)
        if template_source == "db":
            if not MODULES_RESOLVER_AVAILABLE:
                raise HTTPException(status_code=501, detail="DB templates not available - EmailModule classes not found in database")
            if not request.templateId:
                raise HTTPException(status_code=400, detail="templateId required when templateSource=db")
            
            # Load template entity
            template_entity = get_template_entity(db, request.templateId)
            if not template_entity:
                raise HTTPException(status_code=404, detail=f"Template '{request.templateId}' not found")
            
            # Ensure template is VALIDATED
            if template_entity.status != EmailStatusEnum.VALIDATED:
                raise HTTPException(status_code=400, detail=f"Template '{request.templateId}' must be VALIDATED")
            
            # Create modules resolver function
            def modules_resolver(module_id: str, locale: str):
                return get_module_spec(db, module_id, locale)
            
            # Build body base spec from template bodyStarterModuleId or bodyTemplate
            locale = request.locale or "en"
            body_base_spec = _create_body_spec_from_template(
                template_entity, 
                request.previous_spec, 
                locale,
                modules_resolver
            )
            
            # Generate BODY only with AI
            lock_structure = request.lockStructure if request.lockStructure is not None else True
            assistant_text, body_spec, compose_warnings = compose_email_spec(
                request.prompt,
                body_base_spec,
                locale,
                template_id=None,  # No template for body generation
                lock_structure=lock_structure,
            )
            warnings.extend(compose_warnings)
            
            # Filter out HEADER/FOOTER blocks from AI spec (if any)
            body_blocks_only = [b for b in body_spec.blocks if b.type not in ["header", "footer"]]
            if len(body_blocks_only) < len(body_spec.blocks):
                warnings.append("Ignored HEADER/FOOTER blocks from AI - using modules instead")
            body_spec.blocks = body_blocks_only
            
            # Assemble final spec with modules
            template_dict = {
                "headerModuleId": template_entity.header_module_id,
                "footerModuleId": template_entity.footer_module_id,
                "fixedModuleIds": template_entity.fixed_module_ids or [],
                "bodyTemplate": template_entity.body_template,
                "lockPolicy": template_entity.lock_policy,
                "heroPolicy": template_entity.hero_policy,
                "theme": template_entity.theme,
            }
            
            final_spec, assemble_warnings = assemble_email(
                template_dict,
                body_spec,
                locale,
                modules_resolver,
            )
            warnings.extend(assemble_warnings)
            
            # Validate final spec
            from .registry import validate_spec_with_registry
            try:
                validate_spec_with_registry(final_spec)
            except ValueError as e:
                warnings.append(f"Registry validation warning: {str(e)}")
            
            spec = final_spec
            template_id = request.templateId
        
        # Route 2: Hardcoded Template (existing flow)
        else:
            template_id = request.templateId
            if not template_id:
                template_id = get_default_template_id()
                warnings.append(f"templateId missing -> defaulted to {template_id}")
            
            lock_structure = request.lockStructure if request.lockStructure is not None else True
            
            # Compose email spec (full spec)
            assistant_text, spec, compose_warnings = compose_email_spec(
                request.prompt,
                request.previous_spec,
                request.locale or "en",
                template_id=template_id,
                lock_structure=lock_structure,
            )
            warnings.extend(compose_warnings)
        
        # Build MJML
        mjml = build_mjml(spec)
        
        # Compile to HTML
        html, error = compile_mjml(mjml)
        
        if error:
            print(f"[AI Email] MJML compilation warning: {error}")
            warnings.append(f"MJML compilation warning: {error}")
        
        return ComposeEmailResponse(
            assistant_text=assistant_text,
            spec=spec,
            mjml=mjml,
            html=html,
            warnings=warnings if warnings else None,
            templateId=template_id,
            locked=lock_structure if template_source == "hardcoded" else True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI Email] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to compose email: {str(e)}")


def _create_body_spec_from_template(
    template_entity, 
    previous_spec: Optional[EmailSpec], 
    locale: str,
    modules_resolver = None
) -> Optional[EmailSpec]:
    """
    Create body base spec from template bodyTemplate or previous_spec
    """
    from .schemas import EmailSpec
    
    # If previous_spec exists, extract body portion
    if previous_spec:
        # Filter out header/footer blocks
        body_blocks = [b for b in previous_spec.blocks if b.type not in ["header", "footer"]]
        
        # Ensure we have at least 2 blocks (EmailSpec requirement)
        # Add a footer if we don't have one or if we have less than 2 blocks
        has_footer = any(b.type == "footer" for b in body_blocks)
        if not has_footer or len(body_blocks) < 2:
            from .schemas import FooterBlock
            # Remove any existing footer that might not be last
            body_blocks = [b for b in body_blocks if b.type != "footer"]
            # Add footer at the end
            footer_block = FooterBlock(
                type="footer",
                variant="default",
                company_name="Arquantix",
                unsubscribe_url_placeholder="{{unsubscribe_url}}"
            )
            body_blocks.append(footer_block)
        
        return EmailSpec(
            subject=previous_spec.subject,
            preheader=previous_spec.preheader,
            locale=locale,
            theme=template_entity.theme or "arquantix_v1",
            blocks=body_blocks,
        )
    
    # Try bodyStarterModuleId first (if available)
    # SQLAlchemy uses snake_case for column names
    body_starter_module_id = getattr(template_entity, 'body_starter_module_id', None)
    if body_starter_module_id and modules_resolver:
        starter_module = modules_resolver(body_starter_module_id, locale)
        if starter_module and starter_module.blocks:
            # Filter out header/footer blocks from starter (should not have any, but safety check)
            starter_blocks = [b for b in starter_module.blocks if b.type not in ["header", "footer", "social_icons"]]
            if starter_blocks:
                # Use subject from starter module if available, otherwise use a default
                starter_subject = starter_module.subject if starter_module.subject and len(starter_module.subject) > 0 else "Email Subject"
                
                # Add a footer block (required by EmailSpec validation)
                from .schemas import FooterBlock
                footer_block = FooterBlock(
                    type="footer",
                    variant="default",
                    company_name="Arquantix",
                    unsubscribe_url_placeholder="{{unsubscribe_url}}"
                )
                starter_blocks.append(footer_block)
                
                return EmailSpec(
                    subject=starter_subject,
                    preheader=starter_module.preheader,
                    locale=locale,
                    theme=template_entity.theme or "arquantix_v1",
                    blocks=starter_blocks,
                )
    
    # Otherwise, create from bodyTemplate
    body_template = template_entity.body_template
    if not body_template:
        return None
    
    # Extract core blocks from bodyTemplate
    core_blocks = body_template.get("core_blocks", [])
    if not core_blocks:
        return None
    
    # Create minimal blocks with empty props
    from .schemas import HeroBlock, SectionTitleBlock, TextBlock, BulletsBlock, FeatureCardsBlock, CtaBlock
    blocks = []
    
    for block_def in core_blocks:
        block_type = block_def.get("type")
        variant = block_def.get("variant", "default")
        props = block_def.get("props", {})
        
        if block_type == "hero":
            blocks.append(HeroBlock(
                variant=variant,
                title=props.get("title", ""),
                subtitle=props.get("subtitle"),
                image_url=props.get("image_url"),
                cta_label=props.get("cta_label"),
                cta_url=props.get("cta_url"),
            ))
        elif block_type == "section_title":
            blocks.append(SectionTitleBlock(
                variant=variant,
                title=props.get("title", ""),
                subtitle=props.get("subtitle"),
            ))
        elif block_type == "text":
            blocks.append(TextBlock(
                variant=variant,
                heading=props.get("heading"),
                body=props.get("body", ""),
            ))
        elif block_type == "bullets":
            blocks.append(BulletsBlock(
                variant=variant,
                heading=props.get("heading"),
                items=props.get("items", []),
            ))
        elif block_type == "feature_cards":
            blocks.append(FeatureCardsBlock(
                variant=variant,
                heading=props.get("heading"),
                items=props.get("items", []),
            ))
        elif block_type == "cta":
            blocks.append(CtaBlock(
                variant=variant,
                label=props.get("label", ""),
                url=props.get("url"),
                hint=props.get("hint"),
            ))
    
    # Add a footer block (required by EmailSpec validation)
    from .schemas import FooterBlock
    footer_block = FooterBlock(
        type="footer",
        variant="default",
        company_name="Arquantix",
        unsubscribe_url_placeholder="{{unsubscribe_url}}"
    )
    blocks.append(footer_block)
    
    return EmailSpec(
        subject="Email Subject",  # Default subject (will be replaced by AI)
        preheader=None,
        locale=locale,
        theme=template_entity.theme or "arquantix_v1",
        blocks=blocks,
    )


@router.post("/email/compose-ugg", response_model=ComposeEmailUGGResponse)
async def compose_email_ugg(
    request: ComposeEmailUGGRequest,
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Compose email using arquantix_ugg_v1 template
    AI generates ONLY EmailSpecUGG JSON, never MJML/HTML
    Template is hardcoded MJML file, AI only fills JSON fields
    """
    try:
        # Validate prompt length
        if len(request.prompt) > 2000:
            raise HTTPException(status_code=400, detail="Prompt too long (max 2000 chars)")
        
        locale = request.locale or "en"
        warnings: list[str] = []
        
        # Generate EmailSpecUGG using AI agent
        assistant_text, spec, agent_warnings = compose_email_spec_ugg(
            prompt=request.prompt,
            previous_spec=request.previous_spec,
            locale=locale
        )
        warnings.extend(agent_warnings)
        
        # Render MJML from EmailSpecUGG
        try:
            mjml = render_ugg_mjml(spec)
        except Exception as e:
            warnings.append(f"MJML rendering error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to render MJML: {str(e)}")
        
        # Compile MJML to HTML using existing compiler
        from .render import compile_mjml as compile_mjml_func
        html, compile_error = compile_mjml_func(mjml)
        if compile_error:
            warnings.append(f"MJML compilation warning: {compile_error}")
        
        return ComposeEmailUGGResponse(
            assistant_text=assistant_text,
            templateId="arquantix_ugg_v1",
            mjml=mjml,
            html=html,
            spec=spec,
            warnings=warnings if warnings else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/voice/transcribe", response_model=TranscribeAudioResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Transcribe audio to text using OpenAI Whisper
    Accepts audio/webm, audio/wav, audio/mpeg
    Note: This endpoint is kept for backward compatibility.
    The frontend now uses Next.js API routes that call OpenAI directly.
    """
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    
    # Validate file type
    allowed_types = ["audio/webm", "audio/wav", "audio/mpeg", "audio/mp3", "audio/x-m4a"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check size (max 15MB)
    max_size = 15 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File too large (max 15MB)")
    
    try:
        # Call OpenAI Whisper API
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        files = {
            "file": (file.filename or "audio.webm", content, file.content_type)
        }
        
        data = {
            "model": "whisper-1"
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()
            transcript = result.get("text", "")
            
            if not transcript:
                raise HTTPException(status_code=500, detail="No transcript returned")
            
            return TranscribeAudioResponse(transcript=transcript)
            
    except httpx.HTTPStatusError as e:
        error_detail = "OpenAI API error"
        try:
            error_data = e.response.json()
            error_detail = error_data.get("error", {}).get("message", error_detail)
        except:
            pass
        raise HTTPException(status_code=500, detail=error_detail)
    except Exception as e:
        print(f"[AI Email] Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to transcribe audio")

