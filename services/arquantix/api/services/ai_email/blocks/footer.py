"""
Footer block MJML template
Branded with Arquantix theme
Note: This is the content footer block. The template footer is rendered separately.
"""
from ..schemas import FooterBlock
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


def render_footer(block: FooterBlock, theme_name: str = "arquantix_v1") -> str:
    """Render footer block as MJML (content footer, not template footer)"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
    
    mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px {spacing["sm"]}px" font-size="14px" font-weight="500" color="{colors["textSecondary"]}" line-height="1.4">'
    mjml += f'<p style="margin: 0;">{escape_xml(block.company_name)}</p>'
    mjml += '</mj-text>'
    
    if block.address:
        mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px {spacing["sm"]}px" font-size="13px" color="{colors["textMuted"]}" line-height="1.5">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.address)}</p>'
        mjml += '</mj-text>'
    
    mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px" font-size="12px" color="{colors["textMuted"]}" line-height="1.4">'
    mjml += f'<p style="margin: 0;"><a href="{escape_xml(block.unsubscribe_url_placeholder)}" style="color: {colors["textMuted"]}; text-decoration: underline;">Unsubscribe</a></p>'
    mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["lg"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml

