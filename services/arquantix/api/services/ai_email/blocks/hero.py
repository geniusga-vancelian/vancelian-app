"""
Hero block MJML template
Branded with Arquantix theme
"""
from ..schemas import HeroBlock
from ..theme.arquantix_v1 import get_theme


def escape_xml(text: str) -> str:
    """Escape XML special characters"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_hero(block: HeroBlock, theme_name: str = "arquantix_v1") -> str:
    """Render hero block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    radius = theme["radius"]
    button = theme["button"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["xl"]}px" />'
    
    # Image (if variant is image_top and image_url provided)
    if block.variant == "image_top" and block.image_url:
        mjml += f'<mj-image src="{escape_xml(block.image_url)}" alt="" width="100%" border-radius="{radius}px" padding="0 {spacing["md"]}px" />'
        mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
    
    # Title
    mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="36px" font-weight="700" color="{colors["text"]}" line-height="1.2">'
    mjml += f'<p style="margin: 0;">{escape_xml(block.title)}</p>'
    mjml += '</mj-text>'
    
    # Subtitle
    if block.subtitle:
        mjml += f'<mj-spacer height="{spacing["sm"]}px" />'
        mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="18px" color="{colors["textSecondary"]}" line-height="1.5">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.subtitle)}</p>'
        mjml += '</mj-text>'
    
    # CTA
    if block.cta_label and block.cta_url:
        mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
        mjml += f'<mj-button href="{escape_xml(block.cta_url)}" background-color="{colors["bronze"]}" color="#ffffff" font-size="{button["fontSize"]}" font-weight="{button["fontWeight"]}" padding="{button["padding"]}" border-radius="{button["radius"]}px" align="center">'
        mjml += escape_xml(block.cta_label)
        mjml += '</mj-button>'
    
    mjml += f'<mj-spacer height="{spacing["xl"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml

