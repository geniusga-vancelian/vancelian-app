"""
Arquantix Base Email Template
Branded header and footer wrapper
"""
import os
from typing import Dict, Any


def escape_xml(text: str) -> str:
    """Escape XML special characters"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_base_mjml(
    *,
    subject: str,
    preheader: str = None,
    body_sections_mjml: str,
    theme: Dict[str, Any]
) -> str:
    """
    Render complete MJML document with Arquantix branding
    
    Args:
        subject: Email subject
        preheader: Preview text (optional)
        body_sections_mjml: Rendered MJML for body sections (blocks)
        theme: Theme configuration dict
    
    Returns:
        Complete MJML document string
    """
    width = theme.get("width", 600)
    font_family = theme.get("fontFamily", "Arial, sans-serif")
    colors = theme.get("colors", {})
    spacing = theme.get("spacing", {})
    radius = theme.get("radius", 12)
    button = theme.get("button", {})
    
    # Get logo URL from env (optional)
    logo_url = os.getenv("ARQUANTIX_EMAIL_LOGO_URL", "")
    
    mjml = '<?xml version="1.0" encoding="UTF-8"?>'
    mjml += '<mjml>'
    mjml += '<mj-head>'
    
    # Title and preview
    mjml += f'<mj-title>{escape_xml(subject)}</mj-title>'
    if preheader:
        mjml += f'<mj-preview>{escape_xml(preheader)}</mj-preview>'
    
    # Global attributes
    mjml += '<mj-attributes>'
    mjml += f'<mj-all font-family="{escape_xml(font_family)}" />'
    mjml += f'<mj-button background-color="{colors.get("bronze", "#C6A47C")}" color="#ffffff" font-weight="{button.get("fontWeight", "600")}" border-radius="{radius}px" padding="{button.get("padding", "16px 40px")}" font-size="{button.get("fontSize", "16px")}" />'
    mjml += '<mj-text padding="0" line-height="1.6" />'
    mjml += '<mj-section padding="0" />'
    mjml += '<mj-column padding="0" />'
    mjml += '</mj-attributes>'
    
    # Custom styles
    mjml += '<mj-style>'
    mjml += f'.card {{ background-color: {colors.get("surface", "#ffffff")}; border: 1px solid {colors.get("border", "#e5e5e5")}; border-radius: {radius}px; padding: {spacing.get("md", 24)}px; }}'
    mjml += f'.muted {{ color: {colors.get("textMuted", "#999999")}; }}'
    mjml += f'.text-secondary {{ color: {colors.get("textSecondary", "#666666")}; }}'
    mjml += '</mj-style>'
    
    mjml += '</mj-head>'
    
    # Body
    bg_color = colors.get("background", "#f8f8f8")
    mjml += f'<mj-body background-color="{bg_color}" width="{width}px">'
    
    # Header (branded)
    mjml += _render_header(logo_url, theme)
    
    # Body sections (blocks)
    mjml += body_sections_mjml
    
    # Footer (branded - legal/company info)
    mjml += _render_footer(theme)
    
    mjml += '</mj-body>'
    mjml += '</mjml>'
    
    return mjml


def _render_header(logo_url: str, theme: Dict[str, Any]) -> str:
    """Render branded header"""
    colors = theme.get("colors", {})
    spacing = theme.get("spacing", {})
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing.get("md", 24)}px" />'
    
    if logo_url and logo_url.strip():
        mjml += f'<mj-image src="{escape_xml(logo_url)}" alt="Arquantix" width="180px" align="center" padding="0 {spacing.get("md", 24)}px" />'
    else:
        # Text logo fallback
        mjml += '<mj-text align="center" padding="0" font-size="28px" font-weight="700" color="#1a1a1a" letter-spacing="0.05em">'
        mjml += '<p style="margin: 0;">ARQUANTIX</p>'
        mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing.get("sm", 16)}px" />'
    mjml += '<mj-divider border-color="#e5e5e5" border-width="1px" padding="0" />'
    mjml += f'<mj-spacer height="{spacing.get("md", 24)}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml


def _render_footer(theme: Dict[str, Any]) -> str:
    """Render branded footer (legal/company info)"""
    colors = theme.get("colors", {})
    spacing = theme.get("spacing", {})
    
    mjml = '<mj-section background-color="#1a1a1a" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing.get("lg", 40)}px" />'
    
    # Company info
    mjml += '<mj-text align="center" padding="0" font-size="12px" color="#999999" line-height="1.6">'
    mjml += '<p style="margin: 0;">© 2025 Arquantix. All rights reserved.</p>'
    mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing.get("sm", 16)}px" />'
    
    # Legal links (optional - can be customized)
    mjml += '<mj-text align="center" padding="0" font-size="11px" color="#666666">'
    mjml += '<p style="margin: 0;">'
    mjml += '<a href="#" style="color: #999999; text-decoration: underline; margin: 0 8px;">Privacy Policy</a>'
    mjml += '<span style="color: #666666;">|</span>'
    mjml += '<a href="#" style="color: #999999; text-decoration: underline; margin: 0 8px;">Terms</a>'
    mjml += '</p>'
    mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing.get("lg", 40)}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml









