"""
MJML renderer for Social Icons block
"""
from typing import Dict, Optional, Any
from ..theme.arquantix_v1 import get_theme


def render_social_icons(block_data: Dict[str, Any], theme_name: str = "arquantix_v1") -> str:
    """
    Render SOCIAL_ICONS block as MJML
    Uses <mj-social> with theme styling
    """
    theme = get_theme(theme_name)
    links = block_data.get("links", {})
    size = block_data.get("size", "sm")
    
    # Map size to icon size (MJML supports: small, medium, large)
    icon_size_map = {
        "sm": "small",
        "md": "medium",
    }
    icon_size = icon_size_map.get(size, "small")
    
    # Build social elements
    social_elements = []
    
    # Social platform configs (MJML social icons)
    social_configs = {
        "twitter": {"name": "Twitter", "icon": "https://www.mailjet.com/images/theme/v1/icons/ico-social/twitter.png"},
        "facebook": {"name": "Facebook", "icon": "https://www.mailjet.com/images/theme/v1/icons/ico-social/facebook.png"},
        "youtube": {"name": "YouTube", "icon": "https://www.mailjet.com/images/theme/v1/icons/ico-social/youtube.png"},
        "instagram": {"name": "Instagram", "icon": "https://www.mailjet.com/images/theme/v1/icons/ico-social/instagram.png"},
        "linkedin": {"name": "LinkedIn", "icon": "https://www.mailjet.com/images/theme/v1/icons/ico-social/linkedin.png"},
        "telegram": {"name": "Telegram", "icon": "https://www.mailjet.com/images/theme/v1/icons/ico-social/telegram.png"},
    }
    
    # Only include links that are provided
    for platform, url in links.items():
        if url and platform in social_configs:
            config = social_configs[platform]
            social_elements.append(
                f'        <mj-social-element name="{config["name"]}" href="{url}" icon-size="{icon_size}" icon-color="#333333" />'
            )
    
    # If no links, return empty (or a placeholder message)
    if not social_elements:
        return ""
    
    # Render MJML social block
    social_elements_str = "\n".join(social_elements)
    
    mjml = f'''    <mj-social
      font-size="15px"
      icon-size="{icon_size}"
      mode="horizontal"
      icon-padding="10px"
      padding="20px 0"
      border-radius="{theme["RADIUS"]}px"
    >
{social_elements_str}
    </mj-social>'''
    
    return mjml

