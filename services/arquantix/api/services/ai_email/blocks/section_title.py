"""
Section Title block MJML template
Branded with Arquantix theme
"""
from ..schemas import SectionTitleBlock
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


def render_section_title(block: SectionTitleBlock, theme_name: str = "arquantix_v1") -> str:
    """Render section title block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
    
    mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="28px" font-weight="700" color="{colors["text"]}" line-height="1.3">'
    mjml += f'<p style="margin: 0;">{escape_xml(block.title)}</p>'
    mjml += '</mj-text>'
    
    if block.subtitle:
        mjml += f'<mj-spacer height="{spacing["xs"]}px" />'
        mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="16px" color="{colors["textSecondary"]}" line-height="1.5">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.subtitle)}</p>'
        mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml









