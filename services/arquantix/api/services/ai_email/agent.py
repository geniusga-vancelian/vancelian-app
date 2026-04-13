"""
OpenAI agent for composing emails
Handles JSON parsing, validation, and retries
Uses rigid registry validation and template locking
"""
import os
import json
import httpx
from typing import Optional, Tuple, List
from .schemas import EmailSpec
from .system_prompt import SYSTEM_PROMPT, get_user_prompt, get_locked_structure_prompt
from .registry import validate_spec_with_registry
from .templates_presets import get_template, get_default_template_id
from .lock import enforce_locked_structure, extract_structure


# Use same env vars as translate.py
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def compose_email_spec(
    prompt: str,
    previous_spec: Optional[EmailSpec] = None,
    locale: str = "en",
    template_id: Optional[str] = None,
    lock_structure: bool = True,
) -> Tuple[str, EmailSpec, List[str]]:
    """
    Compose EmailSpec from user prompt using OpenAI
    Uses template if provided, enforces structure lock if enabled
    
    Returns:
        (assistant_text, EmailSpec, warnings)
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    warnings: List[str] = []
    
    # Determine base spec
    base_spec: Optional[EmailSpec] = None
    if previous_spec:
        base_spec = previous_spec
    elif template_id:
        try:
            template = get_template(template_id)
            base_spec = template.get_initial_spec(locale)
        except KeyError:
            # Fallback to default template
            default_id = get_default_template_id()
            warnings.append(f"Template '{template_id}' not found, using default '{default_id}'")
            template = get_template(default_id)
            base_spec = template.get_initial_spec(locale)
    else:
        # No template, use default
        default_id = get_default_template_id()
        warnings.append(f"No templateId provided, using default '{default_id}'")
        template = get_template(default_id)
        base_spec = template.get_initial_spec(locale)
    
    # Build user prompt with structure lock info
    if lock_structure and base_spec:
        structure = extract_structure(base_spec)
        user_prompt = get_locked_structure_prompt(
            prompt, base_spec, locale, structure
        )
    else:
        user_prompt = get_user_prompt(prompt, base_spec, locale)
    
    # First attempt
    try:
        response = _call_openai(user_prompt, lock_structure and base_spec is not None)
        spec, assistant_text = _parse_response(response)
        # Validate against registry
        try:
            validate_spec_with_registry(spec)
        except ValueError as registry_error:
            # Retry with registry validation error
            retry_prompt = user_prompt + f"\n\nPrevious attempt failed registry validation:\n{str(registry_error)}\nPlease fix the EmailSpec to match the rigid registry requirements."
            try:
                response = _call_openai(retry_prompt, lock_structure and base_spec is not None)
                spec, assistant_text = _parse_response(response)
                validate_spec_with_registry(spec)  # Validate again
            except (ValueError, json.JSONDecodeError) as e2:
                # Fallback to base spec
                return _create_fallback_from_base(base_spec, prompt, locale, warnings)
        
        # Apply structure lock if enabled
        if lock_structure and base_spec:
            final_spec, lock_warnings = enforce_locked_structure(base_spec, spec)
            warnings.extend(lock_warnings)
            spec = final_spec
        
        return assistant_text, spec, warnings
    except (ValueError, json.JSONDecodeError) as e:
        # Retry once with error feedback
        retry_prompt = user_prompt + f"\n\nPrevious attempt failed with error: {str(e)}\nPlease fix the JSON structure and return valid EmailSpec JSON."
        try:
            response = _call_openai(retry_prompt, lock_structure and base_spec is not None)
            spec, assistant_text = _parse_response(response)
            # Validate against registry
            validate_spec_with_registry(spec)
            # Apply structure lock if enabled
            if lock_structure and base_spec:
                final_spec, lock_warnings = enforce_locked_structure(base_spec, spec)
                warnings.extend(lock_warnings)
                spec = final_spec
            return assistant_text, spec, warnings
        except (ValueError, json.JSONDecodeError) as e2:
            # Fallback to base spec
            return _create_fallback_from_base(base_spec, prompt, locale, warnings)
    except Exception as e:
        # Fallback on any other error
        return _create_fallback_from_base(base_spec, prompt, locale, warnings)


def _call_openai(user_prompt: str, structure_locked: bool = False) -> str:
    """Call OpenAI API and return response text"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Use locked structure prompt if enabled
    system_prompt = SYSTEM_PROMPT
    if structure_locked:
        system_prompt = SYSTEM_PROMPT + "\n\nIMPORTANT: The email structure is LOCKED. You must return a spec with the EXACT same blocks, in the EXACT same order, with the EXACT same types and variants. Only modify the content (text, URLs, props), never change the structure."
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }
    
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _parse_response(response_text: str) -> Tuple[EmailSpec, str]:
    """Parse OpenAI response and extract EmailSpec"""
    # Try to extract JSON from response (might be wrapped in markdown)
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Try to find JSON object
    try:
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            spec_dict = json.loads(json_str)
            
            # Ensure footer is present (required by EmailSpec validation)
            blocks = spec_dict.get("blocks", [])
            if not blocks or blocks[-1].get("type") != "footer":
                # Add footer if missing or not last
                from .schemas import FooterBlock
                footer_dict = {
                    "type": "footer",
                    "variant": "default",
                    "company_name": "Arquantix",
                    "unsubscribe_url_placeholder": "{{unsubscribe_url}}"
                }
                # Remove any existing footer blocks first
                blocks = [b for b in blocks if b.get("type") != "footer"]
                blocks.append(footer_dict)
                spec_dict["blocks"] = blocks
            
            spec = EmailSpec(**spec_dict)
            assistant_text = "I've created a professional email with the requested content."
            return spec, assistant_text
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Failed to parse JSON from response: {str(e)}")
    
    raise ValueError("No valid JSON found in response")


def _create_fallback_from_base(
    base_spec: Optional[EmailSpec],
    prompt: str,
    locale: str,
    warnings: List[str],
) -> Tuple[str, EmailSpec, List[str]]:
    """Create fallback EmailSpec from base spec or minimal"""
    if base_spec:
        # Use base spec as fallback
        warnings.append("Using base template spec as fallback due to generation error")
        assistant_text = "I've used the base template structure. Please refine your request."
        return assistant_text, base_spec, warnings
    
    # Fallback to minimal spec
    from .templates_presets import get_template, get_default_template_id
    try:
        template = get_template(get_default_template_id())
        spec = template.get_initial_spec(locale)
        warnings.append("Using default template as fallback")
        assistant_text = "I've created a basic email structure. Please refine your request."
        return assistant_text, spec, warnings
    except Exception:
        # Absolute minimal fallback
        from .schemas import HeroBlock, FooterBlock
        spec = EmailSpec(
            subject="New Email",
            locale=locale,
            theme="arquantix_v1",
            blocks=[
                HeroBlock(
                    type="hero",
                    variant="text_only",
                    title="Welcome",
                ),
                FooterBlock(
                    type="footer",
                    variant="default",
                    company_name="Arquantix",
                    unsubscribe_url_placeholder="{{unsubscribe_url}}"
                )
            ]
        )
        warnings.append("Using minimal fallback spec")
        assistant_text = "I've created a minimal email structure. Please refine your request."
        return assistant_text, spec, warnings

