"""
OpenAI agent for composing emails with arquantix_ugg_v1 template
MUST output ONLY EmailSpecUGG JSON, never MJML/HTML
"""
import os
import json
import httpx
from typing import Optional, Tuple, List
from .schemas_ugg import EmailSpecUGG
from .templates_mjml.render_ugg import render_ugg_mjml


# Use same env vars as translate.py
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


SYSTEM_PROMPT_UGG = """You are an expert email marketing copywriter specializing in creating engaging, conversion-focused email content.

Your task is to generate ONLY a JSON object that matches the EmailSpecUGG schema. You MUST NEVER generate MJML or HTML code.

EmailSpecUGG Schema:
{
  "subject": "string (1-120 chars, email subject line)",
  "preheader": "string (1-100 chars, preview text shown in email clients)",
  "locale": "string (2-letter ISO code, default: 'en')",
  "offer_line": "string (1-100 chars, uppercase offer/promo line)",
  "headline_lines": ["string", ...] (2-4 lines, uppercase, impactful headlines),
  "intro_text": "string (1-1000 chars, introductory paragraph)",
  "hero_image_url": "string (https:// URL or {{placeholder}})",
  "hero_image_alt": "string (1-200 chars, alt text for hero image)",
  "carousel": {
    "items": [
      {
        "image_url": "string (https:// URL or {{placeholder}})",
        "thumb_url": "string (optional, https:// URL or {{placeholder}})",
        "alt": "string (1-200 chars, product/item description)",
        "href": "string (https:// URL or {{placeholder}})"
      }
    ] (1-6 items)
  },
  "ctas": {
    "primary": {
      "label": "string (1-50 chars, button text)",
      "url": "string (https:// URL or {{placeholder}})"
    },
    "secondary": {
      "label": "string (1-50 chars, optional button text)",
      "url": "string (https:// URL or {{placeholder}})"
    } (optional)
  },
  "promo_block": {
    "image_url": "string (https:// URL or {{placeholder}})",
    "title_lines": ["string", ...] (1-4 lines),
    "body": "string (1-500 chars, promotional text)",
    "button_label": "string (1-50 chars)",
    "button_url": "string (https:// URL or {{placeholder}})"
  } (optional),
  "rewards_block": {
    "image_url": "string (https:// URL or {{placeholder}})",
    "heading": "string (1-100 chars)",
    "body": "string (1-500 chars)",
    "button_label": "string (1-50 chars)",
    "button_url": "string (https:// URL or {{placeholder}})"
  } (optional),
  "footer": {
    "company_name": "string (default: 'Arquantix')",
    "legal_lines": ["string", ...] (max 5 lines, optional),
    "phone": "string (optional, max 50 chars)",
    "address": "string (optional, max 300 chars)",
    "privacy_policy_url_placeholder": "string (default: '{{privacy_policy_url}}')",
    "unsubscribe_url_placeholder": "string (default: '{{unsubscribe_url}}')",
    "view_in_browser_url_placeholder": "string (default: '{{view_in_browser_url}}')",
    "social_links": {
      "facebook": "string (optional, https:// URL or {{placeholder}})",
      "instagram": "string (optional)",
      "youtube": "string (optional)",
      "twitter": "string (optional)",
      "linkedin": "string (optional)"
    } (optional)
  }
}

CRITICAL RULES:
1. Output ONLY valid JSON matching EmailSpecUGG schema
2. NEVER output MJML, HTML, or any markup language
3. URLs must be https:// or placeholders like {{logo_url}}
4. All text fields must be properly escaped for JSON
5. headline_lines must have 2-4 items
6. carousel.items must have 1-6 items
7. Use placeholders for dynamic content ({{logo_url}}, {{unsubscribe_url}}, etc.)
8. Keep subject and preheader concise and compelling
9. Make headlines uppercase and impactful
10. Ensure all required fields are present

Output format:
```json
{
  "subject": "...",
  "preheader": "...",
  ...
}
```"""


def compose_email_spec_ugg(
    prompt: str,
    previous_spec: Optional[EmailSpecUGG] = None,
    locale: str = "en",
) -> Tuple[str, EmailSpecUGG, List[str]]:
    """
    Compose EmailSpecUGG from user prompt using OpenAI
    MUST output ONLY JSON, never MJML/HTML
    
    Returns:
        (assistant_text, EmailSpecUGG, warnings)
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    warnings: List[str] = []
    
    # Build user prompt
    user_prompt = f"""Create an email following the EmailSpecUGG schema based on this request:

{prompt}

"""
    
    if previous_spec:
        user_prompt += f"""Previous email spec (for reference/refinement):
{json.dumps(previous_spec.model_dump(), indent=2)}

"""
    
    user_prompt += """Generate ONLY the JSON EmailSpecUGG object. Do not include any explanation, MJML, or HTML."""

    # First attempt
    try:
        response = _call_openai(user_prompt)
        spec, assistant_text = _parse_response(response)
        return assistant_text, spec, warnings
    except (ValueError, json.JSONDecodeError) as e:
        # Retry once with error feedback
        retry_prompt = user_prompt + f"\n\nPrevious attempt failed with error: {str(e)}\nPlease fix the JSON structure and return valid EmailSpecUGG JSON."
        try:
            response = _call_openai(retry_prompt)
            spec, assistant_text = _parse_response(response)
            return assistant_text, spec, warnings
        except (ValueError, json.JSONDecodeError) as e2:
            # Create fallback spec
            warnings.append(f"Failed to generate valid EmailSpecUGG: {str(e2)}. Using fallback.")
            fallback_spec = _create_fallback_spec(prompt, locale)
            return "I've created a basic email structure. Please refine your request.", fallback_spec, warnings


def _call_openai(user_prompt: str) -> str:
    """Call OpenAI API and return response text"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_UGG},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _parse_response(response_text: str) -> Tuple[EmailSpecUGG, str]:
    """
    Parse OpenAI response to extract EmailSpecUGG JSON
    Returns (EmailSpecUGG, assistant_text)
    """
    # Try to extract JSON from response
    # Look for ```json ... ``` or just {...}
    text = response_text.strip()
    
    # Find JSON block
    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    
    if json_start >= 0 and json_end > json_start:
        json_str = text[json_start:json_end]
        spec_dict = json.loads(json_str)
        spec = EmailSpecUGG(**spec_dict)
        
        # Extract assistant text (everything before JSON or after)
        assistant_text = "I've created a professional email with the requested content."
        if json_start > 0:
            assistant_text = text[:json_start].strip()
        elif json_end < len(text):
            assistant_text = text[json_end:].strip()
        
        return spec, assistant_text
    else:
        raise ValueError("No valid JSON found in response")


def _create_fallback_spec(prompt: str, locale: str) -> EmailSpecUGG:
    """Create a minimal fallback EmailSpecUGG"""
    from .schemas_ugg import Carousel, CarouselItem, Ctas, CtaButton, Footer
    
    return EmailSpecUGG(
        subject="Email from Arquantix",
        preheader="Discover our latest updates",
        locale=locale,
        offer_line="SPECIAL OFFER",
        headline_lines=["WELCOME TO", "ARQUANTIX"],
        intro_text="Thank you for your interest in Arquantix. We're excited to share our latest updates with you.",
        hero_image_url="{{hero_image_url}}",
        hero_image_alt="Arquantix",
        carousel=Carousel(
            items=[
                CarouselItem(
                    image_url="{{product_image_url}}",
                    alt="Product",
                    href="{{product_url}}"
                )
            ]
        ),
        ctas=Ctas(
            primary=CtaButton(
                label="Learn More",
                url="{{learn_more_url}}"
            )
        ),
        footer=Footer()
    )






