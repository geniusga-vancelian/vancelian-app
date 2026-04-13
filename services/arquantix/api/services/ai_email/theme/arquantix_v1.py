"""
Arquantix Brand Pack v1 - Theme tokens
Premium fintech email design system
"""
from typing import Dict, Any

# Width
WIDTH = 600

# Typography
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"
FONT_FAMILY_MONO = "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', monospace"

# Colors (Arquantix brand)
COLORS = {
    "background": "#f8f8f8",  # Light gray background
    "surface": "#ffffff",  # White cards/sections
    "text": "#1a1a1a",  # Dark text
    "textSecondary": "#666666",  # Muted text
    "textMuted": "#999999",  # Very muted text
    "border": "#e5e5e5",  # Subtle borders
    "bronze": "#C6A47C",  # Brand bronze (primary CTA)
    "bronzeDark": "#A6895F",  # Darker bronze (hover)
    "error": "#d32f2f",
    "success": "#2e7d32",
}

# Spacing scale (px)
SPACING = {
    "xs": 8,
    "sm": 16,
    "md": 24,
    "lg": 40,
    "xl": 60,
}

# Border radius
RADIUS = 12

# Button styles
BUTTON = {
    "padding": "16px 40px",
    "radius": RADIUS,
    "fontWeight": "600",
    "fontSize": "16px",
}

# Section padding
SECTION_PADDING = {
    "vertical": SPACING["lg"],
    "horizontal": SPACING["md"],
}

# Card styles
CARD = {
    "background": COLORS["surface"],
    "border": f"1px solid {COLORS['border']}",
    "radius": RADIUS,
    "padding": SPACING["md"],
}


def get_theme(theme_name: str = "arquantix_v1") -> Dict[str, Any]:
    """
    Get theme configuration by name
    Returns dict with all theme tokens
    """
    if theme_name == "arquantix_v1":
        return {
            "name": "arquantix_v1",
            "width": WIDTH,
            "fontFamily": FONT_FAMILY,
            "fontFamilyMono": FONT_FAMILY_MONO,
            "colors": COLORS,
            "spacing": SPACING,
            "radius": RADIUS,
            "button": BUTTON,
            "sectionPadding": SECTION_PADDING,
            "card": CARD,
        }
    else:
        # Fallback to arquantix_v1
        return get_theme("arquantix_v1")









