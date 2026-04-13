"""
EmailSpec Pydantic schemas for AI Email Builder
Strict validation for email structure with rigid registry
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List, Union, Dict
import re


class HeroBlock(BaseModel):
    type: Literal["hero"] = "hero"
    variant: Literal["image_top", "text_only"] = "text_only"
    title: str = Field(..., min_length=1, max_length=120)
    subtitle: Optional[str] = Field(None, max_length=200)
    image_url: Optional[str] = None
    cta_label: Optional[str] = Field(None, max_length=50)
    cta_url: Optional[str] = None
    
    @field_validator("cta_url", "image_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith("https://") or v.startswith("{{") and v.endswith("}}")):
            raise ValueError("URLs must be https:// or placeholders like {{...}}")
        return v
    
    model_config = {"extra": "forbid"}


class SectionTitleBlock(BaseModel):
    type: Literal["section_title"] = "section_title"
    variant: Literal["centered"] = "centered"
    title: str = Field(..., min_length=1, max_length=120)
    subtitle: Optional[str] = Field(None, max_length=200)
    
    model_config = {"extra": "forbid"}


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    variant: Literal["body"] = "body"
    heading: Optional[str] = Field(None, max_length=120)
    body: str = Field(..., min_length=1, max_length=1500)
    
    model_config = {"extra": "forbid"}


class BulletsBlock(BaseModel):
    type: Literal["bullets"] = "bullets"
    variant: Literal["default"] = "default"
    heading: Optional[str] = Field(None, max_length=120)
    items: List[str] = Field(..., min_length=1, max_length=8)
    
    model_config = {"extra": "forbid"}


class FeatureCardItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)
    body: str = Field(..., min_length=1, max_length=200)
    icon: Optional[str] = None
    
    @field_validator("icon")
    @classmethod
    def validate_icon_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith("https://") or v.startswith("{{") and v.endswith("}}")):
            raise ValueError("Icon URLs must be https:// or placeholders like {{...}}")
        return v


class FeatureCardsBlock(BaseModel):
    type: Literal["feature_cards"] = "feature_cards"
    variant: Literal["3up"] = "3up"
    heading: Optional[str] = Field(None, max_length=120)
    items: List[FeatureCardItem] = Field(..., min_length=1, max_length=3)
    
    model_config = {"extra": "forbid"}


class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    variant: Literal["contained"] = "contained"
    image_url: str = Field(..., min_length=1)
    alt_text: Optional[str] = Field(None, max_length=200)
    caption: Optional[str] = Field(None, max_length=200)
    
    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        if not (v.startswith("https://") or (v.startswith("{{") and v.endswith("}}"))):
            raise ValueError("Image URLs must be https:// or placeholders like {{...}}")
        return v
    
    model_config = {"extra": "forbid"}


class CtaBlock(BaseModel):
    type: Literal["cta"] = "cta"
    variant: Literal["primary"] = "primary"
    label: str = Field(..., min_length=1, max_length=50)
    url: str = Field(..., min_length=1)
    hint: Optional[str] = Field(None, max_length=150)
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not (v.startswith("https://") or (v.startswith("{{") and v.endswith("}}"))):
            raise ValueError("URLs must be https:// or placeholders like {{...}}")
        return v
    
    model_config = {"extra": "forbid"}


class DividerBlock(BaseModel):
    type: Literal["divider"] = "divider"
    variant: Literal["default"] = "default"
    
    model_config = {"extra": "forbid"}


class SpacerBlock(BaseModel):
    type: Literal["spacer"] = "spacer"
    variant: Literal["md", "lg"] = "md"
    
    model_config = {"extra": "forbid"}


class SocialIconsBlock(BaseModel):
    type: Literal["social_icons"] = "social_icons"
    variant: Literal["default"] = "default"
    links: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Social media links: twitter, facebook, youtube, instagram, linkedin, telegram"
    )
    size: Literal["sm", "md"] = Field(default="sm")
    
    @field_validator("links")
    @classmethod
    def validate_links(cls, v: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        allowed_keys = {"twitter", "facebook", "youtube", "instagram", "linkedin", "telegram"}
        # Filter out None values and validate keys
        cleaned = {k: v for k, v in v.items() if k in allowed_keys and v is not None}
        # Validate URLs
        for key, url in cleaned.items():
            if url and not (url.startswith("https://") or (url.startswith("{{") and url.endswith("}}"))):
                raise ValueError(f"Invalid URL for {key}: {url}")
        return cleaned
    
    model_config = {"extra": "forbid"}


class HeaderBlock(BaseModel):
    type: Literal["header"] = "header"
    variant: Literal["default"] = "default"
    logo_url: Optional[str] = None
    company_name: str = Field(..., min_length=1, max_length=100)
    
    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith("https://") or (v.startswith("{{") and v.endswith("}}"))):
            raise ValueError("Logo URLs must be https:// or placeholders like {{...}}")
        return v
    
    model_config = {"extra": "forbid"}


class FooterBlock(BaseModel):
    type: Literal["footer"] = "footer"
    variant: Literal["default"] = "default"
    company_name: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    unsubscribe_url_placeholder: str = Field(
        default="{{unsubscribe_url}}",
        pattern=r"\{\{unsubscribe_url\}\}"
    )
    
    model_config = {"extra": "forbid"}


Block = Union[
    HeaderBlock,
    HeroBlock,
    SectionTitleBlock,
    TextBlock,
    BulletsBlock,
    FeatureCardsBlock,
    ImageBlock,
    CtaBlock,
    DividerBlock,
    SpacerBlock,
    SocialIconsBlock,
    FooterBlock,
]


class EmailSpec(BaseModel):
    subject: str = Field(..., min_length=1, max_length=120)
    preheader: Optional[str] = Field(None, max_length=100)
    locale: str = Field(default="en", pattern=r"^[a-z]{2}$")
    theme: Literal["arquantix_v1"] = "arquantix_v1"
    blocks: List[Block] = Field(..., min_length=2, max_length=10)
    
    @field_validator("subject", "preheader")
    @classmethod
    def trim_strings(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip()
        return v
    
    @model_validator(mode="after")
    def validate_spec(self):
        """Basic validation - registry validation happens in render.py"""
        if not self.blocks:
            raise ValueError("blocks cannot be empty")
        
        # Check footer is last
        if self.blocks[-1].type != "footer":
            raise ValueError("Last block must be a footer")
        
        return self


class ComposeEmailRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    locale: Optional[str] = Field(default="en", pattern=r"^[a-z]{2}$")
    previous_spec: Optional[EmailSpec] = None
    theme: Optional[Literal["arquantix_v1"]] = "arquantix_v1"
    templateId: Optional[str] = None
    templateSource: Optional[Literal["hardcoded", "db"]] = "hardcoded"
    lockStructure: Optional[bool] = True


class ComposeEmailResponse(BaseModel):
    assistant_text: str
    spec: EmailSpec
    mjml: str
    html: str
    warnings: Optional[List[str]] = None
    templateId: Optional[str] = None
    locked: Optional[bool] = None


class TranscribeAudioResponse(BaseModel):
    transcript: str

