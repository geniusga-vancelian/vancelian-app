"""
Renderer for arquantix_ugg_v1 MJML template
Safely substitutes placeholders with values from EmailSpecUGG
"""
from pathlib import Path
from typing import TYPE_CHECKING
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

if TYPE_CHECKING:
    from schemas_ugg import EmailSpecUGG


def escape_xml(text: str) -> str:
    """Escape XML special characters"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def load_template() -> str:
    """Load the MJML template file"""
    template_path = Path(__file__).parent / "arquantix_ugg_v1.mjml"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def render_ugg_mjml(spec) -> str:
    """
    Render MJML from EmailSpecUGG
    Safely substitutes placeholders, preserving placeholders in URLs
    """
    template = load_template()
    
    # Basic replacements
    mjml = template.replace("{{SUBJECT}}", escape_xml(spec.subject))
    mjml = mjml.replace("{{PREHEADER}}", escape_xml(spec.preheader))
    mjml = mjml.replace("{{OFFER_LINE}}", escape_xml(spec.offer_line))
    mjml = mjml.replace("{{INTRO_TEXT}}", escape_xml(spec.intro_text))
    mjml = mjml.replace("{{HERO_IMAGE_URL}}", spec.hero_image_url)  # Don't escape URLs
    mjml = mjml.replace("{{HERO_IMAGE_ALT}}", escape_xml(spec.hero_image_alt))
    
    # Headline lines (join with <br/>)
    headline_html = "<br/>".join([escape_xml(line) for line in spec.headline_lines])
    mjml = mjml.replace("{{HEADLINE_LINES}}", headline_html)
    
    # Carousel section
    carousel_section = _render_carousel(spec.carousel)
    mjml = mjml.replace("{{CAROUSEL_SECTION}}", carousel_section)
    
    # CTA buttons
    cta_primary = f'<mj-button href="{spec.ctas.primary.url}" align="center" padding="0 20px 15px">\n          {escape_xml(spec.ctas.primary.label)}\n        </mj-button>'
    mjml = mjml.replace("{{CTA_PRIMARY}}", cta_primary)
    
    if spec.ctas.secondary:
        cta_secondary = f'<mj-button href="{spec.ctas.secondary.url}" align="center" background-color="transparent" color="#C6A47C" border="2px solid #C6A47C" padding="0 20px">\n          {escape_xml(spec.ctas.secondary.label)}\n        </mj-button>'
        mjml = mjml.replace("{{CTA_SECONDARY}}", cta_secondary)
    else:
        mjml = mjml.replace("{{CTA_SECONDARY}}", "")
    
    # Promo block
    if spec.promo_block:
        promo_section = _render_promo_block(spec.promo_block)
        mjml = mjml.replace("{{PROMO_BLOCK_SECTION}}", promo_section)
    else:
        mjml = mjml.replace("{{PROMO_BLOCK_SECTION}}", "")
    
    # Rewards block
    if spec.rewards_block:
        rewards_section = _render_rewards_block(spec.rewards_block)
        mjml = mjml.replace("{{REWARDS_BLOCK_SECTION}}", rewards_section)
    else:
        mjml = mjml.replace("{{REWARDS_BLOCK_SECTION}}", "")
    
    # Footer
    mjml = mjml.replace("{{FOOTER_COMPANY_NAME}}", escape_xml(spec.footer.company_name))
    
    # Footer legal lines
    if spec.footer.legal_lines:
        legal_html = "\n".join([
            f'        <mj-text align="center" padding="0 0 10px" css-class="footer-text">\n          {escape_xml(line)}\n        </mj-text>'
            for line in spec.footer.legal_lines
        ])
        mjml = mjml.replace("{{FOOTER_LEGAL_LINES}}", legal_html)
    else:
        mjml = mjml.replace("{{FOOTER_LEGAL_LINES}}", "")
    
    # Footer address
    if spec.footer.address:
        address_html = f'        <mj-text align="center" padding="0 0 10px" css-class="footer-text">\n          {escape_xml(spec.footer.address)}\n        </mj-text>'
        mjml = mjml.replace("{{FOOTER_ADDRESS}}", address_html)
    else:
        mjml = mjml.replace("{{FOOTER_ADDRESS}}", "")
    
    # Footer phone
    if spec.footer.phone:
        phone_html = f'        <mj-text align="center" padding="0 0 10px" css-class="footer-text">\n          {escape_xml(spec.footer.phone)}\n        </mj-text>'
        mjml = mjml.replace("{{FOOTER_PHONE}}", phone_html)
    else:
        mjml = mjml.replace("{{FOOTER_PHONE}}", "")
    
    # Footer URLs (preserve placeholders)
    mjml = mjml.replace("{{VIEW_IN_BROWSER_URL}}", spec.footer.view_in_browser_url_placeholder)
    mjml = mjml.replace("{{PRIVACY_POLICY_URL}}", spec.footer.privacy_policy_url_placeholder)
    mjml = mjml.replace("{{UNSUBSCRIBE_URL}}", spec.footer.unsubscribe_url_placeholder)
    
    # Footer social links
    if spec.footer.social_links:
        social_html = _render_social_links(spec.footer.social_links)
        mjml = mjml.replace("{{FOOTER_SOCIAL_LINKS}}", social_html)
    else:
        mjml = mjml.replace("{{FOOTER_SOCIAL_LINKS}}", "")
    
    return mjml


def _render_carousel(carousel) -> str:
    """Render carousel section as MJML"""
    if not carousel.items:
        return ""
    
    items_html = []
    for item in carousel.items:
        item_html = f'''            <mj-column width="33.33%">
              <mj-image src="{item.image_url}" alt="{escape_xml(item.alt)}" width="150px" padding="10px" />
              <mj-text align="center" padding="0 10px" font-size="14px" color="#333">
                <a href="{item.href}" style="text-decoration: none; color: #333;">{escape_xml(item.alt)}</a>
              </mj-text>
            </mj-column>'''
        items_html.append(item_html)
    
    # Group items in rows of 3
    rows = []
    for i in range(0, len(items_html), 3):
        row_items = items_html[i:i+3]
        row_html = f'''    <mj-section background-color="#ffffff" padding="0 0 20px">
      {''.join(row_items)}
    </mj-section>'''
        rows.append(row_html)
    
    carousel_html = f'''    <mj-section background-color="#ffffff" padding="0 0 20px">
      <mj-column>
        <mj-text align="center" padding="0 20px 20px" font-size="20px" font-weight="700" color="#1a1a1a">
          Shop the Collection
        </mj-text>
      </mj-column>
    </mj-section>
{''.join(rows)}'''
    
    return carousel_html


def _render_promo_block(promo_block) -> str:
    """Render promo block section as MJML"""
    title_html = "<br/>".join([escape_xml(line) for line in promo_block.title_lines])
    
    return f'''    <mj-section background-color="#f8f8f8" padding="40px 20px">
      <mj-column background-color="#ffffff" border-radius="8px" padding="30px">
        <mj-image src="{promo_block.image_url}" alt="Promo" width="100%" padding="0 0 20px" />
        <mj-text align="center" padding="0 0 15px" css-class="promo-title">
          {title_html}
        </mj-text>
        <mj-text align="center" padding="0 0 20px" css-class="intro-text">
          {escape_xml(promo_block.body)}
        </mj-text>
        <mj-button href="{promo_block.button_url}" align="center">
          {escape_xml(promo_block.button_label)}
        </mj-button>
      </mj-column>
    </mj-section>'''


def _render_rewards_block(rewards_block) -> str:
    """Render rewards block section as MJML"""
    return f'''    <mj-section background-color="#ffffff" padding="40px 20px">
      <mj-column>
        <mj-image src="{rewards_block.image_url}" alt="Rewards" width="100%" padding="0 0 20px" />
        <mj-text align="center" padding="0 0 15px" css-class="rewards-heading">
          {escape_xml(rewards_block.heading)}
        </mj-text>
        <mj-text align="center" padding="0 0 20px" css-class="intro-text">
          {escape_xml(rewards_block.body)}
        </mj-text>
        <mj-button href="{rewards_block.button_url}" align="center">
          {escape_xml(rewards_block.button_label)}
        </mj-button>
      </mj-column>
    </mj-section>'''


def _render_social_links(social_links) -> str:
    """Render social links section as MJML"""
    links = []
    if social_links.facebook:
        links.append(f'<a href="{social_links.facebook}" class="footer-link" style="margin: 0 5px;">Facebook</a>')
    if social_links.instagram:
        links.append(f'<a href="{social_links.instagram}" class="footer-link" style="margin: 0 5px;">Instagram</a>')
    if social_links.youtube:
        links.append(f'<a href="{social_links.youtube}" class="footer-link" style="margin: 0 5px;">YouTube</a>')
    if social_links.twitter:
        links.append(f'<a href="{social_links.twitter}" class="footer-link" style="margin: 0 5px;">Twitter</a>')
    if social_links.linkedin:
        links.append(f'<a href="{social_links.linkedin}" class="footer-link" style="margin: 0 5px;">LinkedIn</a>')
    
    if not links:
        return ""
    
    links_html = " ".join(links)
    return f'''        <mj-text align="center" padding="20px 0 0" css-class="footer-text">
          {links_html}
        </mj-text>'''

