"""
Database configuration and models
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import enum
import os

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER', 'arquantix')}:{os.getenv('DB_PASSWORD', 'arquantix')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5433')}/{os.getenv('DB_NAME', 'arquantix')}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class StatusEnum(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class GlobalSettings(Base):
    __tablename__ = "global_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String(255), nullable=False, default="Arquantix")
    tagline = Column(String(500), nullable=True)
    socials_json = Column(JSON, nullable=True, default={})
    seo_json = Column(JSON, nullable=True, default={})
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Page(Base):
    __tablename__ = "pages"
    
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    title = Column(String(500), nullable=False)
    sections_json = Column(JSON, nullable=True, default={})
    seo_json = Column(JSON, nullable=True, default={})
    status = Column(SQLEnum(StatusEnum), nullable=False, default=StatusEnum.DRAFT)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Translation fields
    source_page_id = Column(Integer, nullable=True)
    translation_status = Column(String(50), nullable=False, default="manual")
    translation_meta_json = Column(JSON, nullable=True)
    
    __table_args__ = (
        {"schema": "public"},
    )


class News(Base):
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    title = Column(String(500), nullable=False)
    excerpt = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)
    cover_image_url = Column(String(1000), nullable=True)
    status = Column(SQLEnum(StatusEnum), nullable=False, default=StatusEnum.DRAFT)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"schema": "public"},
    )


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)


# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

