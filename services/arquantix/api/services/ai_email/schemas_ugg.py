"""
EmailSpecUGG - Strict JSON schema for arquantix_ugg_v1 template
AI generates ONLY this JSON, never MJML/HTML
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Literal


def validate_url(v: Optional[str]) -> Optional[str]:
    """Validate URL is https:// or placeholder"""
    if v and not (v.startswith("https://") or (v.startswith("{{") and v.endswith("}}"))):
        raise ValueError("URLs must be https:// or placeholders like {{...}}")
    return v


class CarouselItem(BaseModel):
    image_url: str = Field(..., min_length=1)
    thumb_url: Optional[str] = None
    alt: str = Field(..., min_length=1, max_length=200)
    href: str = Field(..., min_length=1)
    
    @field_validator("image_url", "thumb_url", "href")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_url(v)
        return v
    
    model_config = {"extra": "forbid"}


class Carousel(BaseModel):
    items: List[CarouselItem] = Field(..., min_length=1, max_length=6)
    
    model_config = {"extra": "forbid"}


class CtaButton(BaseModel):
    label: str = Field(..., min_length=1, max_length=50)
    url: str = Field(..., min_length=1)
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_url(v)
    
    model_config = {"extra": "forbid"}


class Ctas(BaseModel):
    primary: CtaButton
    secondary: Optional[CtaButton] = None
    
    model_config = {"extra": "forbid"}


class PromoBlock(BaseModel):
    image_url: str = Field(..., min_length=1)
    title_lines: List[str] = Field(..., min_length=1, max_length=4)
    body: str = Field(..., min_length=1, max_length=500)
    button_label: str = Field(..., min_length=1, max_length=50)
    button_url: str = Field(..., min_length=1)
    
    @field_validator("image_url", "button_url")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        return validate_url(v)
    
    model_config = {"extra": "forbid"}


class RewardsBlock(BaseModel):
    image_url: str = Field(..., min_length=1)
    heading: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1, max_length=500)
    button_label: str = Field(..., min_length=1, max_length=50)
    button_url: str = Field(..., min_length=1)
    
    @field_validator("image_url", "button_url")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        return validate_url(v)
    
    model_config = {"extra": "forbid"}


class SocialLinks(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    
    @field_validator("facebook", "instagram", "youtube", "twitter", "linkedin")
    @classmethod
    def validate_social_urls(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_url(v)
        return v
    
    model_config = {"extra": "forbid"}


class Footer(BaseModel):
    company_name: str = Field(default="Arquantix", min_length=1, max_length=100)
    legal_lines: List[str] = Field(default_factory=list, max_length=5)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    privacy_policy_url_placeholder: str = Field(default="{{privacy_policy_url}}", pattern=r"\{\{privacy_policy_url\}\}")
    unsubscribe_url_placeholder: str = Field(default="{{unsubscribe_url}}", pattern=r"\{\{unsubscribe_url\}\}")
    view_in_browser_url_placeholder: str = Field(default="{{view_in_browser_url}}", pattern=r"\{\{view_in_browser_url\}\}")
    social_links: Optional[SocialLinks] = None
    
    model_config = {"extra": "forbid"}


class EmailSpecUGG(BaseModel):
    """Strict JSON schema for arquantix_ugg_v1 template - AI generates ONLY this"""
    subject: str = Field(..., min_length=1, max_length=120)
    preheader: str = Field(..., min_length=1, max_length=100)
    locale: str = Field(default="en", pattern=r"^[a-z]{2}$")
    offer_line: str = Field(..., min_length=1, max_length=100)
    headline_lines: List[str] = Field(..., min_length=2, max_length=4)
    intro_text: str = Field(..., min_length=1, max_length=1000)
    hero_image_url: str = Field(..., min_length=1)
    hero_image_alt: str = Field(..., min_length=1, max_length=200)
    carousel: Carousel
    ctas: Ctas
    promo_block: Optional[PromoBlock] = None
    rewards_block: Optional[RewardsBlock] = None
    footer: Footer = Field(default_factory=lambda: Footer())
    
    @field_validator("hero_image_url")
    @classmethod
    def validate_hero_url(cls, v: str) -> str:
        return validate_url(v)
    
    @field_validator("subject", "preheader", "offer_line", "intro_text")
    @classmethod
    def trim_strings(cls, v: str) -> str:
        return v.strip()
    
    model_config = {"extra": "forbid"}


class ComposeEmailUGGRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    locale: Optional[str] = Field(default="en", pattern=r"^[a-z]{2}$")
    previous_spec: Optional[EmailSpecUGG] = None


class ComposeEmailUGGResponse(BaseModel):
    assistant_text: str
    templateId: str = "arquantix_ugg_v1"
    mjml: str
    html: str
    spec: EmailSpecUGG
    warnings: Optional[List[str]] = None






