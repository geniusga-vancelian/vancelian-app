"""
Text block MJML template
Branded with Arquantix theme
"""
from ..schemas import TextBlock
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


def render_text(block: TextBlock, theme_name: str = "arquantix_v1") -> str:
    """Render text block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    
    if block.heading:
        mjml += f'<mj-text padding="0 {spacing["md"]}px {spacing["sm"]}px" font-size="22px" font-weight="600" color="{colors["text"]}" line-height="1.3">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.heading)}</p>'
        mjml += '</mj-text>'
    
    # Body text - convert line breaks to <br/>
    body_html = escape_xml(block.body).replace('\n', '<br/>')
    mjml += f'<mj-text padding="0 {spacing["md"]}px" font-size="16px" color="{colors["text"]}" line-height="1.7">'
    mjml += f'<p style="margin: 0;">{body_html}</p>'
    mjml += '</mj-text>'
    
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml

