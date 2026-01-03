"""
Seed script to create initial data
Run: python scripts/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import SessionLocal, GlobalSettings, Page, News, AdminUser, StatusEnum
from auth import get_password_hash
from datetime import datetime
import bcrypt

def seed():
    db = SessionLocal()
    try:
        # Create or reset admin user
        admin_email = os.getenv("ADMIN_EMAIL", "admin@arquantix.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        existing_admin = db.query(AdminUser).filter(AdminUser.email == admin_email).first()
        
        # Hash password using bcrypt directly (workaround for passlib issue)
        password_bytes = admin_password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
        
        if not existing_admin:
            admin = AdminUser(
                email=admin_email,
                hashed_password=hashed
            )
            db.add(admin)
            print(f"✅ Admin user created: {admin_email}")
        else:
            # Reset password if ADMIN_PASSWORD is set
            if admin_password:
                existing_admin.hashed_password = hashed
                print(f"✅ Admin password reset: {admin_email}")
            else:
                print(f"ℹ️  Admin user already exists: {admin_email}")
        
        # Create global settings if not exists
        global_settings = db.query(GlobalSettings).first()
        if not global_settings:
            global_settings = GlobalSettings(
                site_name="Arquantix",
                tagline="Innovation Technology",
                socials_json={
                    "twitter": "",
                    "linkedin": ""
                },
                seo_json={
                    "defaultTitle": "Arquantix",
                    "defaultDescription": "Arquantix - Innovation Technology"
                }
            )
            db.add(global_settings)
            print("✅ Global settings created")
        else:
            print("ℹ️  Global settings already exist")
        
        # Create home page FR
        page_fr = db.query(Page).filter(
            Page.slug == "home",
            Page.locale == "fr"
        ).first()
        if not page_fr:
            page_fr = Page(
                slug="home",
                locale="fr",
                title="Accueil",
                sections_json={
                    "hero": {
                        "hero_title": "FRACTIONAL REAL ESTATE,\nINSTITUTIONAL RIGOR.",
                        "hero_subtitle": "Premium fractional ownership of luxury real estate\nwith institutional-grade management and transparency.",
                        "hero_cta_label": "Explore Properties",
                        "hero_cta_href": "#properties",
                        "hero_image_url": "",
                        "hero_stats": [
                            {"value": "15", "label": "VILLAS DELIVERED"},
                            {"value": "INSTITUTIONALLY", "label": "MANAGED"},
                            {"value": "GLOBAL", "label": "REAL ESTATE"}
                        ]
                    }
                },
                seo_json={
                    "title": "Arquantix - Accueil",
                    "description": "Page d'accueil Arquantix"
                },
                status=StatusEnum.PUBLISHED,
                published_at=datetime.utcnow()
            )
            db.add(page_fr)
            print("✅ Page FR (home) created with Hero data")
        else:
            # Update existing page with Hero structure if missing
            if not page_fr.sections_json or "hero" not in page_fr.sections_json:
                if not page_fr.sections_json:
                    page_fr.sections_json = {}
                page_fr.sections_json["hero"] = {
                    "hero_title": "FRACTIONAL REAL ESTATE,\nINSTITUTIONAL RIGOR.",
                    "hero_subtitle": "Premium fractional ownership of luxury real estate\nwith institutional-grade management and transparency.",
                    "hero_cta_label": "Explore Properties",
                    "hero_cta_href": "#properties",
                    "hero_image_url": "",
                    "hero_stats": [
                        {"value": "15", "label": "VILLAS DELIVERED"},
                        {"value": "INSTITUTIONALLY", "label": "MANAGED"},
                        {"value": "GLOBAL", "label": "REAL ESTATE"}
                    ]
                }
                print("✅ Page FR (home) updated with Hero data")
            else:
                print("ℹ️  Page FR (home) already exists")
        
        # Create home page EN
        page_en = db.query(Page).filter(
            Page.slug == "home",
            Page.locale == "en"
        ).first()
        if not page_en:
            page_en = Page(
                slug="home",
                locale="en",
                title="Home",
                sections_json={
                    "hero": {
                        "hero_title": "FRACTIONAL REAL ESTATE,\nINSTITUTIONAL RIGOR.",
                        "hero_subtitle": "Premium fractional ownership of luxury real estate\nwith institutional-grade management and transparency.",
                        "hero_cta_label": "Explore Properties",
                        "hero_cta_href": "#properties",
                        "hero_image_url": "",
                        "hero_stats": [
                            {"value": "15", "label": "VILLAS DELIVERED"},
                            {"value": "INSTITUTIONALLY", "label": "MANAGED"},
                            {"value": "GLOBAL", "label": "REAL ESTATE"}
                        ]
                    }
                },
                seo_json={
                    "title": "Arquantix - Home",
                    "description": "Arquantix home page"
                },
                status=StatusEnum.PUBLISHED,
                published_at=datetime.utcnow()
            )
            db.add(page_en)
            print("✅ Page EN (home) created with Hero data")
        else:
            # Update existing page with Hero structure if missing
            if not page_en.sections_json or "hero" not in page_en.sections_json:
                if not page_en.sections_json:
                    page_en.sections_json = {}
                page_en.sections_json["hero"] = {
                    "hero_title": "FRACTIONAL REAL ESTATE,\nINSTITUTIONAL RIGOR.",
                    "hero_subtitle": "Premium fractional ownership of luxury real estate\nwith institutional-grade management and transparency.",
                    "hero_cta_label": "Explore Properties",
                    "hero_cta_href": "#properties",
                    "hero_image_url": "",
                    "hero_stats": [
                        {"value": "15", "label": "VILLAS DELIVERED"},
                        {"value": "INSTITUTIONALLY", "label": "MANAGED"},
                        {"value": "GLOBAL", "label": "REAL ESTATE"}
                    ]
                }
                print("✅ Page EN (home) updated with Hero data")
            else:
                print("ℹ️  Page EN (home) already exists")
        
        # Create sample news FR
        news_fr = db.query(News).filter(
            News.slug == "premiere-news",
            News.locale == "fr"
        ).first()
        if not news_fr:
            news_fr = News(
                slug="premiere-news",
                locale="fr",
                title="Première actualité",
                excerpt="Ceci est notre première actualité en français",
                content_markdown="# Première actualité\n\nBienvenue sur Arquantix!",
                status=StatusEnum.PUBLISHED,
                published_at=datetime.utcnow()
            )
            db.add(news_fr)
            print("✅ News FR created")
        else:
            print("ℹ️  News FR already exists")
        
        # Create sample news EN
        news_en = db.query(News).filter(
            News.slug == "first-news",
            News.locale == "en"
        ).first()
        if not news_en:
            news_en = News(
                slug="first-news",
                locale="en",
                title="First News",
                excerpt="This is our first news in English",
                content_markdown="# First News\n\nWelcome to Arquantix!",
                status=StatusEnum.PUBLISHED,
                published_at=datetime.utcnow()
            )
            db.add(news_en)
            print("✅ News EN created")
        else:
            print("ℹ️  News EN already exists")
        
        db.commit()
        print("\n✅ Seed completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during seed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()

