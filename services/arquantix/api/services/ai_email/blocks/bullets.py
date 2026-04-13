"""
Bullets block MJML template
Branded with Arquantix theme
"""
from ..schemas import BulletsBlock
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


def render_bullets(block: BulletsBlock, theme_name: str = "arquantix_v1") -> str:
    """Render bullets block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    
    if block.heading:
        mjml += f'<mj-text padding="0 {spacing["md"]}px {spacing["sm"]}px" font-size="20px" font-weight="600" color="{colors["text"]}" line-height="1.3">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.heading)}</p>'
        mjml += '</mj-text>'
    
    # Bullet list
    mjml += f'<mj-text padding="0 {spacing["md"]}px" font-size="16px" color="{colors["text"]}" line-height="1.8">'
    mjml += '<ul style="margin: 0; padding-left: 24px; list-style: none;">'
    for item in block.items:
        mjml += f'<li style="margin-bottom: {spacing["xs"]}px; padding-left: 8px; position: relative;">'
        mjml += f'<span style="position: absolute; left: -16px; color: {colors["bronze"]};">•</span>'
        mjml += escape_xml(item)
        mjml += '</li>'
    mjml += '</ul>'
    mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml









