"""
Translation service using OpenAI
Translates page content while preserving JSON structure
"""
import os
import json
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def translate_page_payload(source_page: Dict[str, Any], target_locale: str) -> Dict[str, Any]:
    """
    Translate page payload from source locale to target locale.
    Preserves JSON structure, only translates string values.
    
    Args:
        source_page: Page dict with title, sections_json, seo_json, etc.
        target_locale: Target locale (e.g., 'fr', 'en')
    
    Returns:
        Translated page payload (same structure, translated strings)
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    source_locale = source_page.get("locale", "en")
    
    # Extract fields to translate
    fields_to_translate = {
        "title": source_page.get("title", ""),
    }
    
    # Extract hero fields from sections_json
    sections = source_page.get("sections_json", {}) or {}
    hero = sections.get("hero", {}) or {}
    
    if hero:
        hero_fields = {}
        if "hero_title" in hero:
            hero_fields["hero_title"] = hero["hero_title"]
        if "hero_subtitle" in hero:
            hero_fields["hero_subtitle"] = hero["hero_subtitle"]
        if "hero_cta_label" in hero:
            hero_fields["hero_cta_label"] = hero["hero_cta_label"]
        if hero_fields:
            fields_to_translate["hero"] = hero_fields
    
    # Extract SEO fields
    seo = source_page.get("seo_json", {}) or {}
    if seo:
        seo_fields = {}
        if "title" in seo:
            seo_fields["title"] = seo["title"]
        if "description" in seo:
            seo_fields["description"] = seo["description"]
        if seo_fields:
            fields_to_translate["seo"] = seo_fields
    
    # Build prompt
    prompt = f"""Translate the following content from {source_locale.upper()} to {target_locale.upper()}.

Tone: Luxury institutional (Arquantix brand - premium fractional real estate, institutional rigor).

Rules:
- Preserve all JSON keys exactly as they are
- Only translate string values
- Preserve line breaks (\\n)
- Preserve numbers, URLs, and technical terms
- Output valid JSON only, no markdown, no explanations

Content to translate:
{json.dumps(fields_to_translate, indent=2, ensure_ascii=False)}

Output the translated JSON with the same structure:"""

    # Call OpenAI API
    try:
        response = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional translator specializing in luxury real estate and institutional finance. Translate content while preserving JSON structure exactly."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            },
            timeout=30.0
        )
        response.raise_for_status()
        
        result = response.json()
        translated_text = result["choices"][0]["message"]["content"]
        
        # Parse translated JSON
        translated_fields = json.loads(translated_text)
        
    except httpx.HTTPError as e:
        raise ValueError(f"OpenAI API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse OpenAI response: {str(e)}")
    
    # Build translated page payload
    translated_payload = {
        "slug": source_page["slug"],  # Keep slug unchanged
        "locale": target_locale,
        "title": translated_fields.get("title", source_page.get("title", "")),
    }
    
    # Reconstruct sections_json with translated hero
    translated_sections = sections.copy()
    if "hero" in translated_fields and hero:
        translated_hero = hero.copy()
        translated_hero.update(translated_fields["hero"])
        translated_sections["hero"] = translated_hero
    translated_payload["sections_json"] = translated_sections
    
    # Reconstruct seo_json with translated SEO
    translated_seo = seo.copy()
    if "seo" in translated_fields:
        translated_seo.update(translated_fields["seo"])
    translated_payload["seo_json"] = translated_seo
    
    # Preserve other fields
    translated_payload["status"] = source_page.get("status", "draft")
    
    return translated_payload


