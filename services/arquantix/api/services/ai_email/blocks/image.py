"""
Image block MJML template
Branded with Arquantix theme
"""
from ..schemas import ImageBlock
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


def render_image(block: ImageBlock, theme_name: str = "arquantix_v1") -> str:
    """Render image block as MJML"""
    theme = get_theme(theme_name)
    spacing = theme["spacing"]
    radius = theme["radius"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    
    # Image
    alt = escape_xml(block.alt_text or "")
    mjml += f'<mj-image src="{escape_xml(block.image_url)}" alt="{alt}" width="100%" border-radius="{radius}px" padding="0 {spacing["md"]}px" />'
    
    # Caption (optional)
    if block.caption:
        mjml += f'<mj-text align="center" padding="{spacing["xs"]}px {spacing["md"]}px 0" font-size="14px" color="#999999" line-height="1.4">'
        mjml += f'<p style="margin: 0; font-style: italic;">{escape_xml(block.caption)}</p>'
        mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml









