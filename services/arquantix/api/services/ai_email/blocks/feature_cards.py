"""
Feature cards block MJML template
Branded with Arquantix theme
"""
from ..schemas import FeatureCardsBlock
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


def render_feature_cards(block: FeatureCardsBlock, theme_name: str = "arquantix_v1") -> str:
    """Render feature cards block as MJML"""
    theme = get_theme(theme_name)
    colors = theme["colors"]
    spacing = theme["spacing"]
    radius = theme["radius"]
    card = theme["card"]
    
    mjml = '<mj-section background-color="#ffffff" padding="0">'
    mjml += '<mj-column>'
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    
    if block.heading:
        mjml += f'<mj-text align="center" padding="0 {spacing["md"]}px {spacing["lg"]}px" font-size="24px" font-weight="600" color="{colors["text"]}" line-height="1.3">'
        mjml += f'<p style="margin: 0;">{escape_xml(block.heading)}</p>'
        mjml += '</mj-text>'
    
    # Cards in columns (max 3, variant 3up)
    num_items = len(block.items)
    if num_items == 1:
        column_width = "100%"
    elif num_items == 2:
        column_width = "50%"
    else:
        column_width = "33.33%"
    
    mjml += '<mj-group>'
    for item in block.items:
        mjml += f'<mj-column width="{column_width}">'
        # Card container
        mjml += f'<mj-text padding="{spacing["sm"]}px" background-color="{card["background"]}" border="{card["border"]}" border-radius="{card["radius"]}px">'
        mjml += f'<div style="padding: {spacing["md"]}px;">'
        mjml += f'<p style="margin: 0 0 {spacing["xs"]}px 0; font-size: 18px; font-weight: 600; color: {colors["text"]};">{escape_xml(item.title)}</p>'
        mjml += f'<p style="margin: 0; font-size: 14px; color: {colors["textSecondary"]}; line-height: 1.6;">{escape_xml(item.body)}</p>'
        mjml += '</div>'
        mjml += '</mj-text>'
        mjml += '</mj-column>'
    mjml += '</mj-group>'
    
    mjml += f'<mj-spacer height="{spacing["md"]}px" />'
    mjml += '</mj-column>'
    mjml += '</mj-section>'
    
    return mjml

