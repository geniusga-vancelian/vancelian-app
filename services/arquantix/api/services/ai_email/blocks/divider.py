"""
Divider block MJML template
Branded with Arquantix theme
"""
from ..schemas import DividerBlock
from ..theme.arquantix_v1 import get_theme


def render_divider(block: DividerBlock, theme_name: str = "arquantix_v1") -> str:
    """Render divider block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += f'<mj-divider border-color="{colors["border"]}" border-width="1px" padding="0 {spacing["md"]}px" />'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml









