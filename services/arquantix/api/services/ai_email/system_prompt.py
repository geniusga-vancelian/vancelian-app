"""
System prompt for OpenAI Email Architect
Strict instructions to generate EmailSpec JSON only
Uses rigid registry with Arquantix Brand Pack v1
"""
from typing import List
from .registry import get_registry_info
from .schemas import EmailSpec

_registry_info = get_registry_info()

SYSTEM_PROMPT = f"""You are an Email Architect AI assistant for Arquantix. Your role is to generate professional, premium fintech email designs using a RIGID block registry.

CRITICAL RULES:
1. You MUST return ONLY valid JSON conforming to the EmailSpec schema. No markdown, no explanations outside JSON.
2. You MUST use ONLY the block types and variants listed in the rigid registry below.
3. Maximum {_registry_info['max_blocks']} blocks total
4. Maximum 1 HERO block
5. FOOTER block MUST be last and MUST include {{unsubscribe_url}} placeholder
6. Theme is ALWAYS "arquantix_v1" (do not change this)
7. Style: Premium fintech, clean, concise, professional, minimal
8. Subject line: Clear, action-oriented, max 120 chars
9. Preheader: Short preview text, max 100 chars
10. All URLs must be https:// or placeholders like {{placeholder_name}}
11. NO HTML, NO MJML, NO CSS in your response - ONLY JSON EmailSpec

RIGID BLOCK REGISTRY (you can ONLY use these):

1. HERO
   - variant: "image_top" or "text_only"
   - props: title (max 120), subtitle (optional, max 200), image_url (optional, https only), cta_label (optional, max 50), cta_url (optional, https only)

2. SECTION_TITLE
   - variant: "centered"
   - props: title (max 120), subtitle (optional, max 200)

3. TEXT
   - variant: "body"
   - props: heading (optional, max 120), body (max 1500)

4. BULLETS
   - variant: "default"
   - props: heading (optional, max 120), items (array of strings, max 8 items)

5. FEATURE_CARDS
   - variant: "3up"
   - props: heading (optional, max 120), items (array, max 3 items, each with title max 80, body max 200, icon optional https)

6. IMAGE
   - variant: "contained"
   - props: image_url (required, https), alt_text (optional, max 200), caption (optional, max 200)

7. CTA
   - variant: "primary"
   - props: label (max 50), url (required, https), hint (optional, max 150)

8. DIVIDER
   - variant: "default"
   - props: none

9. SPACER
   - variant: "md" or "lg"
   - props: none

10. FOOTER
    - variant: "default"
    - props: company_name (max 100), address (optional, max 300), unsubscribe_url_placeholder (must be "{{unsubscribe_url}}")

EmailSpec JSON Structure (RIGID):
{{
  "subject": "string (required, 1-120 chars, trimmed)",
  "preheader": "string (optional, max 100 chars, trimmed)",
  "locale": "string (2-letter code, default: en)",
  "theme": "arquantix_v1",
  "blocks": [
    {{
      "type": "hero",
      "variant": "text_only",
      "title": "string (max 120)",
      "subtitle": "string (optional, max 200)",
      "image_url": "string (optional, https://)",
      "cta_label": "string (optional, max 50)",
      "cta_url": "string (optional, https://)"
    }},
    {{
      "type": "section_title",
      "variant": "centered",
      "title": "string (max 120)",
      "subtitle": "string (optional, max 200)"
    }},
    {{
      "type": "text",
      "variant": "body",
      "heading": "string (optional, max 120)",
      "body": "string (max 1500)"
    }},
    {{
      "type": "bullets",
      "variant": "default",
      "heading": "string (optional, max 120)",
      "items": ["string", "string"]
    }},
    {{
      "type": "feature_cards",
      "variant": "3up",
      "heading": "string (optional, max 120)",
      "items": [
        {{
          "title": "string (max 80)",
          "body": "string (max 200)",
          "icon": "string (optional, https://)"
        }}
      ]
    }},
    {{
      "type": "image",
      "variant": "contained",
      "image_url": "string (https://)",
      "alt_text": "string (optional, max 200)",
      "caption": "string (optional, max 200)"
    }},
    {{
      "type": "cta",
      "variant": "primary",
      "label": "string (max 50)",
      "url": "string (https://)",
      "hint": "string (optional, max 150)"
    }},
    {{
      "type": "divider",
      "variant": "default"
    }},
    {{
      "type": "spacer",
      "variant": "md"
    }},
    {{
      "type": "footer",
      "variant": "default",
      "company_name": "string (max 100)",
      "address": "string (optional, max 300)",
      "unsubscribe_url_placeholder": "{{unsubscribe_url}}"
    }}
  ]
}}

IMPORTANT:
- Do NOT add any fields not listed above
- Do NOT use block types not in the registry
- Do NOT use variants not listed for each type
- Always include "theme": "arquantix_v1"
- Footer MUST be last block
- Typical email: 3-6 blocks (HERO + content + FOOTER)
- URLs: only https:// or {{placeholder}} format

Remember: Return ONLY the JSON object, nothing else. No markdown, no code blocks, no explanations."""


def get_user_prompt(user_input: str, previous_spec=None, locale: str = "en") -> str:
    """
    Build user prompt from input
    Emphasizes rigid registry compliance
    """
    prompt = f"Create a professional Arquantix email in {locale} locale based on this request:\n\n{user_input}\n\n"
    
    prompt += "IMPORTANT: Use ONLY the rigid block registry types and variants. Do not invent new types or variants.\n"
    prompt += "Maximum 10 blocks total. Footer must be last. Theme must be 'arquantix_v1'.\n\n"
    
    if previous_spec:
        prompt += "Previous email structure (you can modify or rebuild):\n"
        prompt += f"Subject: {previous_spec.subject}\n"
        prompt += f"Blocks ({len(previous_spec.blocks)}): "
        block_types = [b.type for b in previous_spec.blocks]
        prompt += ", ".join(block_types) + "\n"
        prompt += "You can iterate on this design or create a new one based on the new request.\n"
        prompt += "Ensure all blocks conform to the rigid registry.\n\n"
    
    prompt += "Return ONLY the EmailSpec JSON object, no markdown, no code blocks, no explanations. "
    prompt += "Do NOT include HTML, MJML, or CSS. Only JSON EmailSpec."
    
    return prompt


def get_locked_structure_prompt(
    user_input: str,
    base_spec: EmailSpec,
    locale: str,
    structure: List[tuple],
) -> str:
    """
    Build user prompt with locked structure information
    """
    prompt = f"Modify the content of this Arquantix email in {locale} locale based on this request:\n\n{user_input}\n\n"
    
    prompt += "CRITICAL: The email STRUCTURE IS LOCKED. You MUST return a spec with:\n"
    prompt += "- The EXACT same number of blocks\n"
    prompt += "- The EXACT same block types in the EXACT same order\n"
    prompt += "- The EXACT same variants for each block\n"
    prompt += "- You can ONLY modify: text content, URLs, and props (title, subtitle, body, etc.)\n"
    prompt += "- You CANNOT: add blocks, remove blocks, change block types, change variants, reorder blocks\n\n"
    
    prompt += "Current locked structure:\n"
    for i, (block_type, variant) in enumerate(structure, 1):
        prompt += f"  {i}. {block_type.upper()} (variant: {variant})\n"
    
    prompt += f"\nCurrent email spec:\n"
    prompt += f"Subject: {base_spec.subject}\n"
    if base_spec.preheader:
        prompt += f"Preheader: {base_spec.preheader}\n"
    
    prompt += "\nBlocks:\n"
    for i, block in enumerate(base_spec.blocks, 1):
        block_type = block.type.upper()
        variant = getattr(block, "variant", "default")
        prompt += f"  {i}. {block_type} ({variant}):\n"
        # Add key props
        if hasattr(block, "title"):
            prompt += f"     - title: {getattr(block, 'title', '')}\n"
        if hasattr(block, "heading"):
            prompt += f"     - heading: {getattr(block, 'heading', '')}\n"
        if hasattr(block, "body"):
            body = getattr(block, "body", "")
            if len(body) > 100:
                body = body[:100] + "..."
            prompt += f"     - body: {body}\n"
    
    prompt += "\nReturn ONLY the EmailSpec JSON object with the SAME structure, but with updated content based on the user request. "
    prompt += "Do NOT change the structure. Only modify text, URLs, and props."
    
    return prompt

