"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Global Settings
class GlobalSettingsResponse(BaseModel):
    id: int
    site_name: str
    tagline: Optional[str]
    socials_json: Dict[str, Any]
    seo_json: Dict[str, Any]
    updated_at: datetime

    class Config:
        from_attributes = True


class GlobalSettingsUpdate(BaseModel):
    site_name: Optional[str] = None
    tagline: Optional[str] = None
    socials_json: Optional[Dict[str, Any]] = None
    seo_json: Optional[Dict[str, Any]] = None


# Pages
class PageBase(BaseModel):
    slug: str
    locale: str = "fr"
    title: str
    sections_json: Optional[Dict[str, Any]] = {}
    seo_json: Optional[Dict[str, Any]] = {}


class PageCreate(PageBase):
    pass


class PageUpdate(BaseModel):
    slug: Optional[str] = None
    locale: Optional[str] = None
    title: Optional[str] = None
    sections_json: Optional[Dict[str, Any]] = None
    seo_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    translation_status: Optional[str] = None


class PageResponse(PageBase):
    id: int
    status: str
    published_at: Optional[datetime]
    updated_at: datetime
    source_page_id: Optional[int] = None
    translation_status: str = "manual"
    translation_meta_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# News
class NewsBase(BaseModel):
    slug: str
    locale: str = "fr"
    title: str
    excerpt: Optional[str] = None
    content_markdown: Optional[str] = None
    cover_image_url: Optional[str] = None


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    slug: Optional[str] = None
    locale: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content_markdown: Optional[str] = None
    cover_image_url: Optional[str] = None
    status: Optional[str] = None


class NewsResponse(NewsBase):
    id: int
    status: str
    published_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


# Contact Submissions
class ContactSubmissionCreate(BaseModel):
    name: str
    email: EmailStr
    message: str


class ContactSubmissionResponse(BaseModel):
    id: int
    name: str
    email: str
    message: str
    ip: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

