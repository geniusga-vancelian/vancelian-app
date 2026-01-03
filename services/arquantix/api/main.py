"""
Arquantix API - FastAPI REST API with PostgreSQL
Public endpoints for site vitrine + Admin endpoints with JWT auth
"""
from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import os
import uuid
import shutil
from pathlib import Path

from database import (
    get_db, GlobalSettings, Page, News, ContactSubmission, AdminUser,
    StatusEnum, init_db
)
from schemas import (
    Token, LoginRequest, GlobalSettingsResponse, GlobalSettingsUpdate,
    PageCreate, PageUpdate, PageResponse,
    NewsCreate, NewsUpdate, NewsResponse,
    ContactSubmissionCreate, ContactSubmissionResponse
)
from auth import (
    get_current_user, create_access_token, verify_password, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from services.translate import translate_page_payload
from datetime import timedelta
from pydantic import BaseModel

app = FastAPI(
    title="Arquantix API",
    version="2.0.0",
    description="REST API for Arquantix site vitrine + admin"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3001,http://localhost:3000,http://localhost:3011").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Media storage configuration
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "http://localhost:8011")
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Mount static files for media
app.mount("/media", StaticFiles(directory=str(UPLOADS_DIR)), name="media")


# ============================================================================
# Health & Root
# ============================================================================

@app.get("/")
def root():
    return {"ok": True, "service": "arquantix-api", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "arquantix-api"}


# ============================================================================
# Auth
# ============================================================================

@app.post("/auth/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token"""
    user = db.query(AdminUser).filter(AdminUser.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============================================================================
# Public Endpoints (Site Vitrine)
# ============================================================================

@app.get("/public/global", response_model=GlobalSettingsResponse)
def get_global_public(db: Session = Depends(get_db)):
    """Get global settings (public)"""
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        # Return defaults if not set
        return GlobalSettingsResponse(
            id=0,
            site_name="Arquantix",
            tagline="Innovation Technology",
            socials_json={},
            seo_json={},
            updated_at=datetime.utcnow()
        )
    return global_settings


@app.get("/public/pages/{locale}/{slug}", response_model=PageResponse)
def get_page_public(locale: str, slug: str, db: Session = Depends(get_db)):
    """Get a published page by locale and slug (public)"""
    page = db.query(Page).filter(
        and_(
            Page.slug == slug,
            Page.locale == locale,
            Page.status == StatusEnum.PUBLISHED
        )
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@app.get("/public/news/{locale}", response_model=List[NewsResponse])
def get_news_list_public(locale: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get published news list by locale (public)"""
    news = db.query(News).filter(
        and_(
            News.locale == locale,
            News.status == StatusEnum.PUBLISHED
        )
    ).order_by(News.published_at.desc()).limit(limit).all()
    return news


@app.get("/public/news/{locale}/{slug}", response_model=NewsResponse)
def get_news_public(locale: str, slug: str, db: Session = Depends(get_db)):
    """Get a published news item by locale and slug (public)"""
    news = db.query(News).filter(
        and_(
            News.slug == slug,
            News.locale == locale,
            News.status == StatusEnum.PUBLISHED
        )
    ).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@app.post("/public/contact", response_model=ContactSubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_contact_submission(
    submission: ContactSubmissionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a contact submission (public)"""
    # Get IP and user agent if available
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    db_submission = ContactSubmission(
        name=submission.name,
        email=submission.email,
        message=submission.message,
        ip=ip,
        user_agent=user_agent
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


# ============================================================================
# Admin Endpoints (Protected)
# ============================================================================

@app.get("/admin/global", response_model=GlobalSettingsResponse)
def get_global_admin(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get global settings (admin)"""
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        # Create default if not exists
        global_settings = GlobalSettings(
            site_name="Arquantix",
            tagline="Innovation Technology",
            socials_json={},
            seo_json={}
        )
        db.add(global_settings)
        db.commit()
        db.refresh(global_settings)
    return global_settings


@app.put("/admin/global", response_model=GlobalSettingsResponse)
def update_global_admin(
    update: GlobalSettingsUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update global settings (admin)"""
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        global_settings = GlobalSettings()
        db.add(global_settings)
    
    if update.site_name is not None:
        global_settings.site_name = update.site_name
    if update.tagline is not None:
        global_settings.tagline = update.tagline
    if update.socials_json is not None:
        global_settings.socials_json = update.socials_json
    if update.seo_json is not None:
        global_settings.seo_json = update.seo_json
    
    db.commit()
    db.refresh(global_settings)
    return global_settings


@app.get("/admin/pages")
def list_pages_admin(
    locale: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pages (admin) - React Admin format: {data: [...], total: n}"""
    query = db.query(Page)
    if locale:
        query = query.filter(Page.locale == locale)
    pages = query.order_by(Page.updated_at.desc()).all()
    # Convert to dict format for React Admin
    pages_data = [
        {
            "id": p.id,
            "slug": p.slug,
            "locale": p.locale,
            "title": p.title,
            "sections_json": p.sections_json or {},
            "seo_json": p.seo_json or {},
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "source_page_id": p.source_page_id,
            "translation_status": p.translation_status,
            "translation_meta_json": p.translation_meta_json,
        }
        for p in pages
    ]
    return {
        "data": pages_data,
        "total": len(pages_data)
    }


@app.post("/admin/pages", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
def create_page_admin(
    page: PageCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a page (admin)"""
    # Check if page with same slug+locale exists
    existing = db.query(Page).filter(
        and_(Page.slug == page.slug, Page.locale == page.locale)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Page with this slug and locale already exists")
    
    db_page = Page(**page.dict())
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page


@app.get("/admin/pages/{page_id}", response_model=PageResponse)
def get_page_admin(
    page_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a page by ID (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@app.put("/admin/pages/{page_id}", response_model=PageResponse)
def update_page_admin(
    page_id: int,
    update: PageUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a page (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    update_dict = update.dict(exclude_unset=True)
    if "status" in update_dict:
        update_dict["status"] = StatusEnum(update_dict["status"])
    if update_dict.get("status") == StatusEnum.PUBLISHED and not page.published_at:
        update_dict["published_at"] = datetime.utcnow()
    
    for key, value in update_dict.items():
        setattr(page, key, value)
    
    db.commit()
    db.refresh(page)
    return page


@app.delete("/admin/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page_admin(
    page_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a page (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    db.delete(page)
    db.commit()
    return None


@app.get("/admin/news")
def list_news_admin(
    locale: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all news (admin) - React Admin format: {data: [...], total: n}"""
    query = db.query(News)
    if locale:
        query = query.filter(News.locale == locale)
    news_list = query.order_by(News.updated_at.desc()).all()
    # Convert to dict format for React Admin
    news_data = [
        {
            "id": n.id,
            "slug": n.slug,
            "locale": n.locale,
            "title": n.title,
            "excerpt": n.excerpt,
            "content_markdown": n.content_markdown,
            "cover_image_url": n.cover_image_url,
            "status": n.status.value if hasattr(n.status, 'value') else str(n.status),
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        }
        for n in news_list
    ]
    return {
        "data": news_data,
        "total": len(news_data)
    }


@app.post("/admin/news", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
def create_news_admin(
    news: NewsCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a news item (admin)"""
    existing = db.query(News).filter(
        and_(News.slug == news.slug, News.locale == news.locale)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="News with this slug and locale already exists")
    
    db_news = News(**news.dict())
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news


@app.get("/admin/news/{news_id}", response_model=NewsResponse)
def get_news_admin(
    news_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a news item by ID (admin)"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@app.put("/admin/news/{news_id}", response_model=NewsResponse)
def update_news_admin(
    news_id: int,
    update: NewsUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a news item (admin)"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    
    update_dict = update.dict(exclude_unset=True)
    if "status" in update_dict:
        update_dict["status"] = StatusEnum(update_dict["status"])
    if update_dict.get("status") == StatusEnum.PUBLISHED and not news.published_at:
        update_dict["published_at"] = datetime.utcnow()
    
    for key, value in update_dict.items():
        setattr(news, key, value)
    
    db.commit()
    db.refresh(news)
    return news


@app.delete("/admin/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news_admin(
    news_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a news item (admin)"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    db.delete(news)
    db.commit()
    return None


@app.get("/admin/contact-submissions")
def list_contact_submissions_admin(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all contact submissions (admin) - React Admin format: {data: [...], total: n}"""
    submissions = db.query(ContactSubmission).order_by(ContactSubmission.created_at.desc()).all()
    # Convert to dict format for React Admin
    submissions_data = [
        {
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "message": s.message,
            "ip": s.ip,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in submissions
    ]
    return {
        "data": submissions_data,
        "total": len(submissions_data)
    }


# ============================================================================
# Media Upload (Admin)
# ============================================================================

@app.post("/admin/uploads")
async def upload_file(
    file: UploadFile = File(...),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Upload a file (admin only)
    Returns: { url: "http://..." }
    """
    if STORAGE_BACKEND != "local":
        raise HTTPException(status_code=501, detail="Only local storage is supported in MVP")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else ".bin"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOADS_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Return URL
    file_url = f"{MEDIA_BASE_URL}/media/{unique_filename}"
    return {"url": file_url, "filename": unique_filename}


# ============================================================================
# Translation Endpoints (Admin)
# ============================================================================

class TranslateRequest(BaseModel):
    target_locale: str


@app.post("/admin/pages/{page_id}/translate")
def translate_page(
    page_id: int,
    request: TranslateRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Translate a page to target locale using OpenAI.
    Creates or updates the translated page.
    """
    # Get source page
    source_page = db.query(Page).filter(Page.id == page_id).first()
    if not source_page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set")
    
    # Convert source page to dict
    source_dict = {
        "id": source_page.id,
        "slug": source_page.slug,
        "locale": source_page.locale,
        "title": source_page.title,
        "sections_json": source_page.sections_json or {},
        "seo_json": source_page.seo_json or {},
        "status": source_page.status.value if hasattr(source_page.status, 'value') else str(source_page.status),
    }
    
    # Translate
    try:
        translated_payload = translate_page_payload(source_dict, request.target_locale)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Check if translated page already exists
    existing_page = db.query(Page).filter(
        and_(
            Page.slug == source_page.slug,
            Page.locale == request.target_locale
        )
    ).first()
    
    action = "updated"
    if existing_page:
        # Update existing page
        existing_page.title = translated_payload["title"]
        existing_page.sections_json = translated_payload["sections_json"]
        existing_page.seo_json = translated_payload["seo_json"]
        existing_page.source_page_id = source_page.id
        existing_page.translation_status = "auto"
        existing_page.translation_meta_json = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "created_at": datetime.utcnow().isoformat(),
            "from": source_page.locale,
            "to": request.target_locale,
        }
        translated_page = existing_page
    else:
        # Create new page
        translated_page = Page(
            slug=translated_payload["slug"],
            locale=translated_payload["locale"],
            title=translated_payload["title"],
            sections_json=translated_payload["sections_json"],
            seo_json=translated_payload["seo_json"],
            status=StatusEnum(translated_payload["status"]),
            source_page_id=source_page.id,
            translation_status="auto",
            translation_meta_json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "created_at": datetime.utcnow().isoformat(),
                "from": source_page.locale,
                "to": request.target_locale,
            }
        )
        db.add(translated_page)
        action = "created"
    
    db.commit()
    db.refresh(translated_page)
    
    return {
        "ok": True,
        "translated_page_id": translated_page.id,
        "action": action
    }


@app.patch("/admin/pages/{page_id}/mark-reviewed")
def mark_page_reviewed(
    page_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a page translation as reviewed (admin)"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    page.translation_status = "reviewed"
    db.commit()
    db.refresh(page)
    return page


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
