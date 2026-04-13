"""
Header block MJML template
Branded with Arquantix theme
Note: This is the content header block. The template header is rendered separately.
"""
from ..schemas import HeaderBlock
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


def render_header(block: HeaderBlock, theme_name: str = "arquantix_v1") -> str:
    """Render header block as MJML (content header, not template header)"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    
    if block.logo_url and block.logo_url.strip():
        mjml += f'<mj-image src="{escape_xml(block.logo_url)}" alt="{escape_xml(block.company_name)}" width="180px" align="center" padding="0 {spacing["md"]}px" />'
    else:
        # Text logo fallback
        mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="28px" font-weight="700" color="#1a1a1a" letter-spacing="0.05em">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.company_name)}</p>'
        mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["sm"]}px" />'
    mjml += '<mj-divider border-color="#e5e5e5" border-width="1px" padding="0" />'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml






