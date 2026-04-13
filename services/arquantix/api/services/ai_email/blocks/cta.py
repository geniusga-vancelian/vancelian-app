"""
CTA block MJML template
Branded with Arquantix theme
"""
from ..schemas import CtaBlock
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


def render_cta(block: CtaBlock, theme_name: str = "arquantix_v1") -> str:
    """Render CTA block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    button = theme["button"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
    
    mjml += f'<mj-button href="{escape_xml(block.url)}" background-color="{colors["bronze"]}" color="#ffffff" font-size="{button["fontSize"]}" font-weight="{button["fontWeight"]}" padding="{button["padding"]}" border-radius="{button["radius"]}px" align="center">'
    mjml += escape_xml(block.label)
    mjml += '</mj-button>'
    
    if block.hint:
        mjml += f'<mj-spacer height="{spacing["sm"]}px" />'
        mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="14px" color="{colors["textMuted"]}" line-height="1.4">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.hint)}</p>'
        mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml

