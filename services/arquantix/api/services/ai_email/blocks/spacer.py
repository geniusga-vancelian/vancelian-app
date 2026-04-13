"""
Spacer block MJML template
Branded with Arquantix theme
"""
from ..schemas import SpacerBlock
from ..theme.arquantix_v1 import get_theme


def render_spacer(block: SpacerBlock, theme_name: str = "arquantix_v1") -> str:
    """Render spacer block as MJML"""
    theme = get_theme(theme_name)
    spacing = theme["spacing"]
    
    # Map variant to spacing value
    height_map = {
        "md": spacing["md"],
        "lg": spacing["lg"],
    }
    
    height = height_map.get(block.variant, spacing["md"])
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{height}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml









