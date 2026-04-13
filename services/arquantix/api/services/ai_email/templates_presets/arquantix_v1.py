"""
Arquantix v1 Rigid Email Templates
Pre-built email structures with locked layouts
"""
from ..schemas import (
    EmailSpec,
    HeroBlock,
    SectionTitleBlock,
    TextBlock,
    BulletsBlock,
    FeatureCardsBlock,
    FeatureCardItem,
    ImageBlock,
    CtaBlock,
    DividerBlock,
    SpacerBlock,
    FooterBlock,
)
from .types import EmailTemplate, register_template


def _create_welcome_v1(locale: str = "en") -> EmailSpec:
    """Template: Welcome email"""
    return EmailSpec(
        subject="Welcome to Arquantix",
        preheader="Start your investment journey with us",
        locale=locale,
        theme="arquantix_v1",
        blocks=[
            HeroBlock(
                type="hero",
                variant="text_only",
                title="Welcome to Arquantix",
                subtitle="Your trusted investment platform",
                cta_label="Get Started",
                cta_url="https://arquantix.com/dashboard",
            ),
            TextBlock(
                type="text",
                variant="body",
                heading="Welcome",
                body="Thank you for joining Arquantix. We're excited to help you achieve your financial goals with our innovative investment platform.",
            ),
            FeatureCardsBlock(
                type="feature_cards",
                variant="3up",
                heading="Why Choose Arquantix",
                items=[
                    FeatureCardItem(
                        title="Expert Guidance",
                        body="Access professional investment advice tailored to your goals",
                    ),
                    FeatureCardItem(
                        title="Advanced Analytics",
                        body="Track your portfolio performance with real-time insights",
                    ),
                    FeatureCardItem(
                        title="Secure Platform",
                        body="Your investments are protected with bank-level security",
                    ),
                ],
            ),
            CtaBlock(
                type="cta",
                variant="primary",
                label="Explore Dashboard",
                url="https://arquantix.com/dashboard",
                hint="Start investing today",
            ),
            FooterBlock(
                type="footer",
                variant="default",
                company_name="Arquantix",
                unsubscribe_url_placeholder="{{unsubscribe_url}}",
            ),
        ],
    )


def _create_newsletter_v1(locale: str = "en") -> EmailSpec:
    """Template: Newsletter email"""
    return EmailSpec(
        subject="Monthly Market Update",
        preheader="Stay informed with our latest insights",
        locale=locale,
        theme="arquantix_v1",
        blocks=[
            SectionTitleBlock(
                type="section_title",
                variant="centered",
                title="Monthly Market Update",
                subtitle="January 2025",
            ),
            TextBlock(
                type="text",
                variant="body",
                heading="Market Overview",
                body="This month, we've seen significant movements across global markets. Here's what you need to know about the latest trends and opportunities.",
            ),
            DividerBlock(
                type="divider",
                variant="default",
            ),
            TextBlock(
                type="text",
                variant="body",
                heading="Key Highlights",
                body="Our analysts have identified several key trends that could impact your investment strategy. Stay ahead with our comprehensive market analysis.",
            ),
            FeatureCardsBlock(
                type="feature_cards",
                variant="3up",
                items=[
                    FeatureCardItem(
                        title="Market Trends",
                        body="Discover emerging opportunities in global markets",
                    ),
                    FeatureCardItem(
                        title="Portfolio Insights",
                        body="Optimize your investments with data-driven recommendations",
                    ),
                    FeatureCardItem(
                        title="Expert Analysis",
                        body="Learn from our team of experienced financial advisors",
                    ),
                ],
            ),
            CtaBlock(
                type="cta",
                variant="primary",
                label="Read Full Report",
                url="https://arquantix.com/newsletter",
            ),
            FooterBlock(
                type="footer",
                variant="default",
                company_name="Arquantix",
                unsubscribe_url_placeholder="{{unsubscribe_url}}",
            ),
        ],
    )


def _create_project_update_v1(locale: str = "en") -> EmailSpec:
    """Template: Project update email"""
    return EmailSpec(
        subject="Project Update: New Features Available",
        preheader="Discover what's new on our platform",
        locale=locale,
        theme="arquantix_v1",
        blocks=[
            HeroBlock(
                type="hero",
                variant="image_top",
                title="New Features Available",
                subtitle="We've enhanced your investment experience",
                image_url="{{hero_image_url}}",
                cta_label="Learn More",
                cta_url="https://arquantix.com/features",
            ),
            SectionTitleBlock(
                type="section_title",
                variant="centered",
                title="What's New",
                subtitle="Latest platform updates",
            ),
            BulletsBlock(
                type="bullets",
                variant="default",
                heading="Key Improvements",
                items=[
                    "Enhanced portfolio analytics dashboard",
                    "New risk assessment tools",
                    "Improved mobile app experience",
                    "Advanced reporting features",
                ],
            ),
            ImageBlock(
                type="image",
                variant="contained",
                image_url="{{feature_image_url}}",
                alt_text="New features preview",
                caption="Explore the new dashboard interface",
            ),
            TextBlock(
                type="text",
                variant="body",
                heading="Get Started",
                body="These new features are now available in your dashboard. Log in to explore and take advantage of the latest tools designed to help you make better investment decisions.",
            ),
            CtaBlock(
                type="cta",
                variant="primary",
                label="Access Dashboard",
                url="https://arquantix.com/dashboard",
            ),
            FooterBlock(
                type="footer",
                variant="default",
                company_name="Arquantix",
                unsubscribe_url_placeholder="{{unsubscribe_url}}",
            ),
        ],
    )


def _create_investor_update_v1(locale: str = "en") -> EmailSpec:
    """Template: Investor update email"""
    return EmailSpec(
        subject="Quarterly Investor Update",
        preheader="Your portfolio performance summary",
        locale=locale,
        theme="arquantix_v1",
        blocks=[
            HeroBlock(
                type="hero",
                variant="text_only",
                title="Quarterly Investor Update",
                subtitle="Q1 2025 Performance Summary",
            ),
            SectionTitleBlock(
                type="section_title",
                variant="centered",
                title="Portfolio Performance",
                subtitle="Review your investment results",
            ),
            TextBlock(
                type="text",
                variant="body",
                heading="Overview",
                body="Your portfolio has shown strong performance this quarter. Here's a detailed breakdown of your investments and the key factors driving your returns.",
            ),
            BulletsBlock(
                type="bullets",
                variant="default",
                heading="Performance Highlights",
                items=[
                    "Portfolio value increased by 12.5%",
                    "All asset classes performed well",
                    "Risk-adjusted returns exceeded benchmarks",
                    "Diversification strategy proving effective",
                ],
            ),
            DividerBlock(
                type="divider",
                variant="default",
            ),
            TextBlock(
                type="text",
                variant="body",
                heading="Next Steps",
                body="Based on your current performance and market conditions, we recommend reviewing your investment strategy and considering rebalancing opportunities. Our team is here to help you optimize your portfolio.",
            ),
            CtaBlock(
                type="cta",
                variant="primary",
                label="View Full Report",
                url="https://arquantix.com/reports",
                hint="Access detailed analytics and recommendations",
            ),
            FooterBlock(
                type="footer",
                variant="default",
                company_name="Arquantix",
                address="123 Investment Street, Financial District",
                unsubscribe_url_placeholder="{{unsubscribe_url}}",
            ),
        ],
    )


# Register all templates
register_template(
    EmailTemplate(
        id="welcome_v1",
        name="Welcome Email",
        description="Welcome new users with an introduction and key features",
        locale_defaults=["en", "fr", "it"],
        initial_spec_builder=_create_welcome_v1,
        locked=True,
    )
)

register_template(
    EmailTemplate(
        id="newsletter_v1",
        name="Newsletter",
        description="Monthly newsletter with market updates and insights",
        locale_defaults=["en", "fr", "it"],
        initial_spec_builder=_create_newsletter_v1,
        locked=True,
    )
)

register_template(
    EmailTemplate(
        id="project_update_v1",
        name="Project Update",
        description="Announce new features and platform updates",
        locale_defaults=["en", "fr", "it"],
        initial_spec_builder=_create_project_update_v1,
        locked=True,
    )
)

register_template(
    EmailTemplate(
        id="investor_update_v1",
        name="Investor Update",
        description="Quarterly performance summary for investors",
        locale_defaults=["en", "fr", "it"],
        initial_spec_builder=_create_investor_update_v1,
        locked=True,
    )
)









