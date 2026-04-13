"""
MJML rendering functions
Compiles EmailSpec to MJML and then to HTML
Uses branded template and rigid registry
"""
import subprocess
import tempfile
import os
from typing import Tuple
from .schemas import EmailSpec, Block
from .registry import validate_spec_with_registry
from .theme.arquantix_v1 import get_theme
from .templates.arquantix_base import render_base_mjml
from .blocks import (
    hero, text, feature_cards, cta, footer,
    section_title, bullets, image, divider, spacer, social_icons, header
)


def build_mjml(spec: EmailSpec) -> str:
    """
    Build complete MJML document from EmailSpec
    Validates against registry, uses branded template
    Returns MJML string
    """
    # Validate against rigid registry
    validate_spec_with_registry(spec)
    
    # Get theme
    theme = get_theme(spec.theme)
    
    # Render all blocks
    body_sections_mjml = ""
    for block in spec.blocks:
        block_mjml = _render_block(block, spec.theme)
        body_sections_mjml += block_mjml
    
    # Build complete MJML with branded template
    mjml = render_base_mjml(
        subject=spec.subject,
        preheader=spec.preheader,
        body_sections_mjml=body_sections_mjml,
        theme=theme
    )
    
    return mjml


def _render_block(block: Block, theme_name: str = "arquantix_v1") -> str:
    """Render a single block to MJML using theme"""
    block_type = block.type
    
    if block_type == "header":
        return header.render_header(block, theme_name)
    elif block_type == "hero":
        return hero.render_hero(block, theme_name)
    elif block_type == "section_title":
        return section_title.render_section_title(block, theme_name)
    elif block_type == "text":
        return text.render_text(block, theme_name)
    elif block_type == "bullets":
        return bullets.render_bullets(block, theme_name)
    elif block_type == "feature_cards":
        return feature_cards.render_feature_cards(block, theme_name)
    elif block_type == "image":
        return image.render_image(block, theme_name)
    elif block_type == "cta":
        return cta.render_cta(block, theme_name)
    elif block_type == "divider":
        return divider.render_divider(block, theme_name)
    elif block_type == "spacer":
        return spacer.render_spacer(block, theme_name)
    elif block_type == "social_icons":
        return social_icons.render_social_icons(block.model_dump(), theme_name)
    elif block_type == "footer":
        return footer.render_footer(block, theme_name)
    else:
        raise ValueError(f"Unknown block type: {block_type}")


def compile_mjml(mjml: str) -> Tuple[str, str]:
    """
    Compile MJML to HTML using npx mjml
    Returns (html, error_message)
    If error, returns fallback HTML with error message
    Security: Rejects HTML containing <script tags
    """
    # Security check: reject MJML that would generate <script> tags
    if "<script" in mjml.lower() or "javascript:" in mjml.lower():
        error_msg = "Security: Script tags are not allowed in email templates"
        return _fallback_html(error_msg), error_msg
    
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mjml', delete=False) as f:
            f.write(mjml)
            temp_path = f.name
        
        try:
            # Run mjml via npx
            # mjml CLI: file as positional argument, -s for stdout output
            result = subprocess.run(
                ['npx', '--yes', 'mjml', temp_path, '-s'],  # -s = --stdout (output to stdout)
                capture_output=True,
                text=True,
                timeout=30,  # Increased timeout for first-time npx download
                check=False
            )
            
            if result.returncode == 0:
                html = result.stdout
                # Additional security check on compiled HTML
                if "<script" in html.lower() or "javascript:" in html.lower():
                    error_msg = "Security: Compiled HTML contains script tags (rejected)"
                    return _fallback_html(error_msg), error_msg
                return html, ""
            else:
                error_msg = result.stderr or "MJML compilation failed"
                return _fallback_html(error_msg), error_msg
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return _fallback_html("MJML compilation timeout"), "MJML compilation timeout"
    except FileNotFoundError:
        return _fallback_html("Node.js/npx not found. Please install Node.js to compile MJML."), "Node.js/npx not found"
    except Exception as e:
        return _fallback_html(str(e)), str(e)


def _fallback_html(error_msg: str) -> str:
    """Generate fallback HTML when MJML compilation fails"""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Preview</title>
</head>
<body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 4px;">
        <h2 style="color: #d32f2f; margin-bottom: 20px;">MJML Compilation Error</h2>
        <p style="color: #666; line-height: 1.6;">{error_msg}</p>
        <p style="color: #999; font-size: 14px; margin-top: 20px;">Please ensure Node.js and MJML are installed, or check the server logs for details.</p>
    </div>
</body>
</html>"""

