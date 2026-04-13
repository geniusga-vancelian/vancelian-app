"""
OpenAI agent for composing jurisdiction configs
"""
import os
import json
import httpx
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from database import FieldDefinition


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Load catalog snapshot and aliases at module level (cached)
_AGENT_DIR = Path(__file__).parent
_CATALOG_SNAPSHOT_PATH = _AGENT_DIR / "catalog_snapshot.json"
_SLUG_ALIASES_PATH = _AGENT_DIR / "slug_aliases.json"

_CATALOG_SNAPSHOT: Dict[str, Any] = {}
_SLUG_ALIASES: Dict[str, str] = {}


def _load_catalog_data():
    """Load catalog snapshot and aliases (reloads on each call to pick up updates)"""
    global _CATALOG_SNAPSHOT, _SLUG_ALIASES
    
    # Always reload to pick up updates (files are small, performance impact is minimal)
    if _CATALOG_SNAPSHOT_PATH.exists():
        try:
            with open(_CATALOG_SNAPSHOT_PATH) as f:
                _CATALOG_SNAPSHOT = json.load(f)
        except Exception:
            # If reload fails, keep existing snapshot
            pass
    
    if _SLUG_ALIASES_PATH.exists():
        try:
            with open(_SLUG_ALIASES_PATH) as f:
                _SLUG_ALIASES = json.load(f)
        except Exception:
            # If reload fails, keep existing aliases
            pass


# Load on import
_load_catalog_data()


def search_field_candidates(db: Session, term: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search field definitions by slug or field_name_en.
    Returns list of {slug, field_type, category, field_name_en}
    """
    term_lower = term.lower()
    search_pattern = f"%{term_lower}%"
    
    query = db.query(FieldDefinition).filter(
        FieldDefinition.is_active == True
    ).filter(
        (FieldDefinition.slug.ilike(search_pattern)) |
        (FieldDefinition.field_name_en.ilike(search_pattern))
    )
    
    fields = query.order_by(FieldDefinition.category, FieldDefinition.slug).limit(limit).all()
    
    return [
        {
            "slug": f.slug,
            "field_type": f.field_type,
            "category": f.category,
            "field_name_en": f.field_name_en,
        }
        for f in fields
    ]


def resolve_slug(db: Session, term: str) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Resolve a field term to canonical slug.
    Uses catalog snapshot and aliases for fast lookup, falls back to DB search.
    Returns (best_slug_or_none, candidates_list)
    """
    term_lower = term.lower().strip()
    
    # Reload catalog data if needed (for hot-reload in dev)
    _load_catalog_data()
    
    # Check alias map first (from loaded JSON)
    if term_lower in _SLUG_ALIASES:
        canonical = _SLUG_ALIASES[term_lower]
        # Verify canonical exists in DB
        field = db.query(FieldDefinition).filter(
            FieldDefinition.slug == canonical,
            FieldDefinition.is_active == True
        ).first()
        if field:
            return canonical, [{"slug": canonical, "field_type": field.field_type, "category": field.category, "field_name_en": field.field_name_en}]
    
    # Normalize term: convert underscores to hyphens for matching
    term_normalized = term_lower.replace("_", "-")
    
    # Check if exact match exists in catalog snapshot
    if _CATALOG_SNAPSHOT and term_normalized in _CATALOG_SNAPSHOT.get("slugs", []):
        field = db.query(FieldDefinition).filter(
            FieldDefinition.slug == term_normalized,
            FieldDefinition.is_active == True
        ).first()
        if field:
            return term_normalized, [{"slug": term_normalized, "field_type": field.field_type, "category": field.category, "field_name_en": field.field_name_en}]
    
    # Try exact match in DB (with normalized term)
    if term_normalized != term_lower:
        field = db.query(FieldDefinition).filter(
            FieldDefinition.slug == term_normalized,
            FieldDefinition.is_active == True
        ).first()
        if field:
            return term_normalized, [{"slug": term_normalized, "field_type": field.field_type, "category": field.category, "field_name_en": field.field_name_en}]
    
    # Search candidates (fallback to DB search)
    candidates = search_field_candidates(db, term, limit=10)
    
    if not candidates:
        # Try searching with normalized term (underscores -> hyphens)
        if term_normalized != term_lower:
            candidates = search_field_candidates(db, term_normalized, limit=10)
    
    if not candidates:
        return None, []
    
    # Score candidates: exact slug match > normalized match > slug contains > field_name_en contains
    term_lower = term.lower()
    scored = []
    for cand in candidates:
        slug_lower = cand["slug"].lower()
        name_lower = cand["field_name_en"].lower() if cand.get("field_name_en") else ""
        
        if slug_lower == term_lower:
            score = 4  # Exact match
        elif slug_lower == term_normalized:
            score = 3  # Normalized match (underscores -> hyphens)
        elif term_lower in slug_lower or term_normalized in slug_lower:
            score = 2  # Contains
        elif term_lower in name_lower or term_normalized in name_lower:
            score = 1  # Name contains
        else:
            score = 0
        
        scored.append((score, cand))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    if scored and scored[0][0] > 0:
        return scored[0][1]["slug"], [c[1] for c in scored if c[0] > 0]
    
    return None, candidates


def list_fields(db: Session, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Internal tool function to load field definitions from DB.
    Returns list of {slug, field_type, category} for available fields.
    """
    query = db.query(FieldDefinition).filter(FieldDefinition.is_active == True)
    
    if category:
        query = query.filter(FieldDefinition.category == category)
    
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.filter(
            (FieldDefinition.slug.ilike(search_pattern)) |
            (FieldDefinition.field_name_en.ilike(search_pattern))
        )
    
    fields = query.order_by(FieldDefinition.category, FieldDefinition.slug).limit(100).all()
    
    return [
        {
            "slug": f.slug,
            "field_type": f.field_type,
            "category": f.category,
            "field_name_en": f.field_name_en,
        }
        for f in fields
    ]


def normalize_spec(spec: Dict[str, Any], purpose: str) -> Dict[str, Any]:
    """
    Normalize AI-generated spec to match backend schema exactly.
    - Remove step.conditions and move to block.conditions
    - Convert condition keys: field_slug->field, operator->op, target->block_id/field based on action
    - Convert conditions: null -> []
    - Map slug aliases to canonical slugs
    - Ensure required top-level fields exist
    - Validate show_block/hide_block references are within same step
    """
    normalized = spec.copy()
    
    # Ensure required top-level fields
    if "jurisdiction" not in normalized:
        normalized["jurisdiction"] = normalized.get("jurisdiction", "")
    if "purpose" not in normalized:
        normalized["purpose"] = purpose
    if "version" not in normalized:
        normalized["version"] = 1
    if "status" not in normalized:
        normalized["status"] = "draft"
    if purpose == "KYC" and "entry_rules" not in normalized:
        normalized["entry_rules"] = None
    
    if purpose == "KYC":
        # Normalize steps -> blocks -> conditions
        for step in normalized.get("steps", []):
            # Remove step-level conditions (if any) - they should be on blocks
            if "conditions" in step:
                step_conditions = step.pop("conditions")
                # Move step conditions to first block if it exists
                if step.get("blocks") and len(step["blocks"]) > 0:
                    first_block = step["blocks"][0]
                    if not first_block.get("conditions"):
                        first_block["conditions"] = []
                    if isinstance(step_conditions, list):
                        first_block["conditions"].extend(step_conditions)
            
            # Get all block_ids in this step for validation
            step_block_ids = set()
            for block in step.get("blocks", []):
                if isinstance(block, dict) and block.get("block_id"):
                    step_block_ids.add(block["block_id"])
            
            for block in step.get("blocks", []):
                # Normalize conditions: null -> []
                if block.get("conditions") is None:
                    block["conditions"] = []
                elif not isinstance(block.get("conditions"), list):
                    block["conditions"] = []
                
                # Normalize each condition
                normalized_conditions = []
                for cond in block.get("conditions", []):
                    if not isinstance(cond, dict) or "when" not in cond or "then" not in cond:
                        continue
                    
                    when = cond["when"].copy()
                    then_list = []
                    
                    # Normalize when clause: field_slug -> field, operator -> op
                    if "field_slug" in when:
                        when["field"] = when.pop("field_slug")
                    if "operator" in when:
                        when["op"] = when.pop("operator")
                    
                    # Normalize then actions: target -> block_id/field based on action
                    for then_item in cond.get("then", []):
                        if not isinstance(then_item, dict) or "action" not in then_item:
                            continue
                        
                        action = then_item["action"]
                        normalized_then = {"action": action}
                        
                        if "target" in then_item:
                            target = then_item["target"]
                            if action in ["show_block", "hide_block"]:
                                # Validate target block_id is in same step
                                if target not in step_block_ids:
                                    # Skip invalid cross-step reference (validation will catch it)
                                    continue
                                normalized_then["block_id"] = target
                            elif action in ["require_field", "optional_field"]:
                                normalized_then["field"] = target
                            else:
                                # Keep target for other actions
                                normalized_then["target"] = target
                        elif "block_id" in then_item:
                            block_id_ref = then_item["block_id"]
                            # Validate block_id is in same step - skip if not found
                            if block_id_ref not in step_block_ids:
                                # Skip invalid cross-step reference (validation will catch it)
                                continue
                            normalized_then["block_id"] = block_id_ref
                        elif "field" in then_item:
                            normalized_then["field"] = then_item["field"]
                        elif "step_id" in then_item:
                            normalized_then["step_id"] = then_item["step_id"]
                        
                        then_list.append(normalized_then)
                    
                    normalized_conditions.append({
                        "when": when,
                        "then": then_list
                    })
                
                block["conditions"] = normalized_conditions
                
                # Map slug aliases in fields array (use loaded aliases)
                _load_catalog_data()
                normalized_fields = []
                for field_slug in block.get("fields", []):
                    if field_slug in _SLUG_ALIASES:
                        normalized_fields.append(_SLUG_ALIASES[field_slug])
                    else:
                        normalized_fields.append(field_slug)
                block["fields"] = normalized_fields
    
    return normalized


def _validate_and_resolve_slugs_in_spec(db: Session, spec: Dict[str, Any], purpose: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Validate and resolve all field slugs in a spec.
    Returns (resolved_spec, questions_list)
    questions_list: [{term: str, suggestions: [slug, ...]}]
    """
    unknown_terms = []
    questions = []
    
    if purpose == "KYC":
        # Traverse steps -> blocks -> fields
        for step in spec.get("steps", []):
            for block in step.get("blocks", []):
                # Resolve fields array
                resolved_fields = []
                for field_term in block.get("fields", []):
                    if isinstance(field_term, str):
                        canonical, candidates = resolve_slug(db, field_term)
                        if canonical:
                            if canonical != field_term:
                                # Replace with canonical
                                resolved_fields.append(canonical)
                            else:
                                resolved_fields.append(canonical)
                        else:
                            # Unknown field
                            if field_term not in unknown_terms:
                                unknown_terms.append(field_term)
                                suggestions = [c["slug"] for c in candidates[:5]]
                                questions.append({
                                    "term": field_term,
                                    "suggestions": suggestions
                                })
                            # Don't add to resolved_fields
                
                block["fields"] = resolved_fields
                
                # Resolve conditions
                if "conditions" in block and block["conditions"]:
                    for cond in block.get("conditions", []):
                        if isinstance(cond, dict) and "when" in cond:
                            when = cond["when"]
                            # Support both "field" and "field_slug" for backward compatibility
                            field_key = "field" if "field" in when else "field_slug"
                            if field_key in when:
                                field_term = when[field_key]
                                canonical, candidates = resolve_slug(db, field_term)
                                if canonical:
                                    when["field"] = canonical
                                    if "field_slug" in when:
                                        del when["field_slug"]
                                else:
                                    if field_term not in unknown_terms:
                                        unknown_terms.append(field_term)
                                        suggestions = [c["slug"] for c in candidates[:5]]
                                        questions.append({
                                            "term": field_term,
                                            "suggestions": suggestions
                                        })
                            # Normalize operator to op
                            if "operator" in when and "op" not in when:
                                when["op"] = when.pop("operator")
                            # Also check then[].field (or block_id for block actions)
                            if "then" in cond:
                                for then_item in cond["then"]:
                                    if isinstance(then_item, dict):
                                        # Resolve field in then actions
                                        if "field" in then_item:
                                            field_term = then_item["field"]
                                            canonical, candidates = resolve_slug(db, field_term)
                                            if canonical:
                                                then_item["field"] = canonical
                                            else:
                                                if field_term not in unknown_terms:
                                                    unknown_terms.append(field_term)
                                                    suggestions = [c["slug"] for c in candidates[:5]]
                                                    questions.append({
                                                        "term": field_term,
                                                        "suggestions": suggestions
                                                    })
    else:  # AML_RISK
        # Resolve rules[].when.field_slug (or field for backward compatibility)
        for rule in spec.get("rules", []):
            if "when" in rule and isinstance(rule["when"], dict):
                when = rule["when"]
                # Support both "field" and "field_slug" for backward compatibility
                field_key = "field_slug" if "field_slug" in when else "field"
                if field_key in when:
                    field_term = when[field_key]
                    canonical, candidates = resolve_slug(db, field_term)
                    if canonical:
                        # Keep field_slug for AML_RISK (schema expects it)
                        when["field_slug"] = canonical
                        if field_key == "field":
                            del when["field"]
                    else:
                        if field_term not in unknown_terms:
                            unknown_terms.append(field_term)
                            suggestions = [c["slug"] for c in candidates[:5]]
                            questions.append({
                                "term": field_term,
                                "suggestions": suggestions
                            })
                # Keep operator for AML_RISK (schema expects it)
                if "op" in when and "operator" not in when:
                    when["operator"] = when.pop("op")
    
    return spec, questions


def compose_jurisdiction_config_spec(
    db: Session,
    jurisdiction: str,
    purpose: str,
    prompt: str,
    previous_spec: Optional[Dict[str, Any]] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, Optional[Dict[str, Any]], List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Compose jurisdiction config spec from user prompt using OpenAI.
    
    Returns:
        (assistant_text, spec_dict_or_none, warnings, questions, value_suggestions)
        questions: [{term: str, suggestions: [slug, ...]}] - blocking (missing field slugs)
        value_suggestions: [{field_slug: str, suggested_values: [...]}] - non-blocking (enum/value choices)
    
    Raises:
        ValueError: If OpenAI returns invalid JSON or missing required fields
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    warnings: List[str] = []
    questions: List[Dict[str, Any]] = []  # Blocking: missing field slugs
    value_suggestions: List[Dict[str, Any]] = []  # Non-blocking: enum/value suggestions
    
    # Reload catalog data
    _load_catalog_data()
    
    # Get top slugs by category from catalog snapshot (instead of querying DB)
    # For KYC: identity, contact, address, tax, employment, financial
    # For AML_RISK: aml, identity, financial, employment
    if purpose == "KYC":
        categories = ["identity", "contact", "address", "tax", "employment", "financial"]
    else:  # AML_RISK
        categories = ["aml", "identity", "financial", "employment"]
    
    # Get slugs from catalog snapshot, then fetch field details from DB
    catalog_slugs = _CATALOG_SNAPSHOT.get("slugs", [])
    by_category = _CATALOG_SNAPSHOT.get("by_category", {})
    
    # Collect top slugs per category (up to 10 per category)
    selected_slugs = []
    for cat in categories:
        cat_count = by_category.get(cat, 0)
        if cat_count > 0:
            # Get slugs for this category from DB (limited)
            cat_fields = list_fields(db, category=cat)
            selected_slugs.extend([f["slug"] for f in cat_fields[:10]])  # Top 10 per category
    
    # Deduplicate
    selected_slugs = list(dict.fromkeys(selected_slugs))  # Preserve order
    
    # Limit to 50 fields to avoid token bloat
    if len(selected_slugs) > 50:
        selected_slugs = selected_slugs[:50]
        warnings.append(f"Showing first 50 of {len(selected_slugs)} available fields in prompt")
    
    # Fetch full field details from DB for selected slugs
    unique_fields = []
    for slug in selected_slugs:
        field = db.query(FieldDefinition).filter(
            FieldDefinition.slug == slug,
            FieldDefinition.is_active == True
        ).first()
        if field:
            unique_fields.append({
                "slug": field.slug,
                "field_type": field.field_type,
                "category": field.category,
                "field_name_en": field.field_name_en,
            })
    
    # Build system prompt with strict JSON schema requirements
    if purpose == "KYC":
        # Build example skeleton JSON
        example_skeleton = {
            "jurisdiction": jurisdiction,
            "purpose": "KYC",
            "version": 1,
            "status": "draft",
            "steps": [
                {
                    "step_id": "step1",
                    "title_en": "Step Title",
                    "description_en": "Step description",
                    "blocks": [
                        {
                            "block_id": "block1",
                            "fields": ["field-slug-1", "field-slug-2"],
                            "layout": "single_column",
                            "required": True,
                            "conditions": []
                        }
                    ]
                }
            ],
            "entry_rules": None
        }
        
        example_condition = {
            "when": {
                "field": "<slug>",
                "op": "equals",
                "value": "<value>"
            },
            "then": [{
                "action": "show_block",
                "block_id": "<block_id>"
            }]
        }
        
        system_prompt = f"""You are an expert in KYC (Know Your Customer) compliance and onboarding flows.

You generate STRICT JSON configurations for multi-step onboarding forms that comply with regulatory requirements.

Available field slugs (you MUST only use these - never invent slugs):
{json.dumps(unique_fields, indent=2)}

Jurisdiction: {jurisdiction}

CRITICAL RULES:
1. NEVER invent or guess field slugs. Use ONLY slugs from the catalog above.
2. If a field is not in the catalog, ask a clarifying question with suggestions.
3. Generate a COMPLETE KYC onboarding config object with ALL required fields.
4. Each step MUST have: step_id (string), title_en (string), description_en (string, optional), blocks (array)
5. Each block MUST have: block_id (string), fields (array of slugs), layout (single_column|two_columns|cards), required (bool), conditions (array, default [])
6. Conditions MUST be on Block.conditions ONLY. Steps MUST NOT have a "conditions" key.
7. Conditions MUST have this exact structure:
{json.dumps(example_condition, indent=2)}
   - Use "field" (not "field_slug") in when clause
   - Use "op" (not "operator") in when clause
   - Use "block_id" for show_block/hide_block actions, "field" for require_field/optional_field actions
8. show_block/hide_block actions MUST reference block_id within the SAME step. Cross-step block references are not supported.
9. Start with a minimal valid config (1-2 steps, 2-3 fields per step)

OUTPUT FORMAT - CRITICAL:
- Return ONLY valid JSON. No markdown. No commentary. No code blocks.
- The JSON MUST match this exact skeleton structure:
{json.dumps(example_skeleton, indent=2)}
- The JSON MUST include: jurisdiction, purpose, version, status, steps (array)
- Each step MUST include: step_id, title_en, blocks (array)
- Each block MUST include: block_id, fields (array), layout, required, conditions (array)
- If a field is missing from catalog, include questions[] array with term and suggestions
- Do NOT wrap the JSON in markdown code blocks or add any text before/after it"""
    else:  # AML_RISK
        # Build example skeleton JSON
        example_skeleton = {
            "jurisdiction": jurisdiction,
            "purpose": "AML_RISK",
            "version": 1,
            "status": "draft",
            "rules": [
                {
                    "rule_id": "rule1",
                    "description_en": "Rule description",
                    "when": {
                        "field_slug": "<slug>",
                        "operator": "equals",
                        "value": "<value>"
                    },
                    "effect": {
                        "add_score": 20
                    }
                }
            ],
            "outputs": {
                "min_score": 0,
                "max_score": 100,
                "tiers": [
                    {"tier": "low", "min": 0, "max": 30}
                ]
            }
        }
        
        system_prompt = f"""You are an expert in AML (Anti-Money Laundering) risk scoring and compliance rules.

You generate STRICT JSON configurations for rules-based AML risk scoring engines.

Available field slugs (you MUST only use these - never invent slugs):
{json.dumps(unique_fields, indent=2)}

Jurisdiction: {jurisdiction}

CRITICAL RULES:
1. NEVER invent or guess field slugs. Use ONLY slugs from the catalog above.
2. If a field is not in the catalog, ask a clarifying question with suggestions.
3. Generate a valid AML_RISK config with rules[] and outputs object.
4. Each rule MUST have this exact structure:
   - rule_id (string)
   - description_en (string)
   - when: {{ field_slug (string), operator (equals|not_equals|in|not_in|exists|not_exists), value (any) }}
   - effect: {{ add_score (number) | set_flag (string) | require_action (string) | stop (bool) | weight (number) }}
5. Outputs MUST have: min_score (number, default 0), max_score (number, default 100), tiers[] (array)
6. Tiers must cover full range [min_score, max_score] without gaps or overlaps
7. Start with a minimal valid config (2-3 rules, 2-3 tiers)
8. If unsure about a field slug, ask a question instead of guessing

OUTPUT FORMAT - CRITICAL:
- Return ONLY valid JSON. No markdown. No commentary. No code blocks.
- The JSON MUST match this exact skeleton structure:
{json.dumps(example_skeleton, indent=2)}
- The JSON MUST include: jurisdiction, purpose, version, status, rules (array), outputs (object)
- If a field is missing from catalog, include questions[] array with term and suggestions
- Do NOT wrap the JSON in markdown code blocks or add any text before/after it"""
    
    # Build user prompt
    user_prompt = f"User request: {prompt}\n\n"
    
    if previous_spec:
        user_prompt += f"Previous config (for iterative refinement):\n{json.dumps(previous_spec, indent=2)}\n\n"
    
    if messages:
        user_prompt += "Conversation history:\n"
        for msg in messages[-5:]:  # Last 5 messages for context
            user_prompt += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
        user_prompt += "\n"
    
    user_prompt += "Generate the configuration JSON now. Return ONLY valid JSON, no markdown, no commentary."
    
    # Call OpenAI
    try:
        response_text = _call_openai(system_prompt, user_prompt)
        result = _parse_response(response_text, purpose)
        
        # Validate parsed result has required structure
        if not isinstance(result, dict):
            raise ValueError(f"OpenAI returned non-dict response: {type(result).__name__}")
        
        # Extract spec and assistant_text
        spec = result.get("spec") or result
        assistant_text = result.get("assistant_text", "Configuration generated successfully.")
        extracted_questions = result.get("questions", [])
        if extracted_questions:
            questions.extend(extracted_questions)
        # Extract value_suggestions (non-blocking enum/value choices)
        extracted_value_suggestions = result.get("value_suggestions", [])
        if extracted_value_suggestions:
            value_suggestions.extend(extracted_value_suggestions)
        
        # Validate spec has required fields based on purpose
        if purpose == "KYC":
            if not isinstance(spec, dict):
                raise ValueError(f"KYC spec must be a dict, got {type(spec).__name__}")
            if "steps" not in spec or not isinstance(spec.get("steps"), list):
                raise ValueError("KYC config must have 'steps' array")
        else:  # AML_RISK
            if not isinstance(spec, dict):
                raise ValueError(f"AML_RISK spec must be a dict, got {type(spec).__name__}")
            if "rules" not in spec or not isinstance(spec.get("rules"), list):
                raise ValueError("AML_RISK config must have 'rules' array")
        
        # Validate and resolve all slugs first
        resolved_spec, slug_questions = _validate_and_resolve_slugs_in_spec(db, spec, purpose)
        questions.extend(slug_questions)
        
        # If unknown slugs exist, return questions instead of spec
        if slug_questions:
            unknown_list = [q["term"] for q in slug_questions]
            assistant_text = f"I could not find these fields in the catalog: {', '.join(unknown_list)}. Please choose one of the suggested slugs below for each."
            return assistant_text, None, warnings, questions, value_suggestions
        
        # Normalize spec structure for KYC
        if purpose == "KYC":
            # Normalize to backend format
            normalized_spec = normalize_spec(resolved_spec, purpose)
            
            # Ensure required top-level fields
            if "jurisdiction" not in normalized_spec:
                normalized_spec["jurisdiction"] = jurisdiction
            if "purpose" not in normalized_spec:
                normalized_spec["purpose"] = "KYC"
            if "version" not in normalized_spec:
                normalized_spec["version"] = 1
            if "status" not in normalized_spec:
                normalized_spec["status"] = "draft"
            if "entry_rules" not in normalized_spec:
                normalized_spec["entry_rules"] = None
            
            return assistant_text, normalized_spec, warnings, questions, value_suggestions
        else:  # AML_RISK
            # Ensure required top-level fields
            if "jurisdiction" not in resolved_spec:
                resolved_spec["jurisdiction"] = jurisdiction
            if "purpose" not in resolved_spec:
                resolved_spec["purpose"] = "AML_RISK"
            if "version" not in resolved_spec:
                resolved_spec["version"] = 1
            if "status" not in resolved_spec:
                resolved_spec["status"] = "draft"
            
            return assistant_text, resolved_spec, warnings, questions, value_suggestions
        
    except ValueError as e:
        # Re-raise ValueError with clear message
        raise ValueError(f"OpenAI response parsing failed: {str(e)}")
    except Exception as e:
        # Wrap other exceptions
        raise ValueError(f"OpenAI call failed: {str(e)}")


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI API and return response text"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"} if OPENAI_MODEL.startswith("gpt-4") or OPENAI_MODEL.startswith("o1") else None,
    }
    
    # Remove response_format if None
    if payload["response_format"] is None:
        del payload["response_format"]
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _parse_response(response_text: str, purpose: str) -> Dict[str, Any]:
    """
    Parse OpenAI response, extracting JSON with robust fallback extraction.
    
    Strategy:
    1. Try parsing entire response as JSON (preferred for structured outputs)
    2. Extract JSON from markdown code blocks (```json or ```)
    3. Extract first JSON object substring using regex
    4. Validate extracted object has required fields
    
    Raises:
        ValueError: If no valid JSON can be extracted or required fields are missing
    """
    if not response_text or not response_text.strip():
        raise ValueError("OpenAI returned empty response")
    
    # Strategy 1: Try parsing entire response as JSON (preferred for structured outputs)
    try:
        parsed = json.loads(response_text.strip())
        if isinstance(parsed, dict):
            # Validate has required fields
            if purpose == "KYC":
                if "spec" in parsed or ("steps" in parsed and isinstance(parsed.get("steps"), list)):
                    return parsed
            else:  # AML_RISK
                if "spec" in parsed or ("rules" in parsed and isinstance(parsed.get("rules"), list)):
                    return parsed
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract JSON from markdown code blocks
    # Look for ```json or ``` code blocks
    json_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    matches = re.findall(json_block_pattern, response_text, re.DOTALL)
    if matches:
        for match in matches:
            try:
                parsed = json.loads(match.strip())
                if isinstance(parsed, dict):
                    # Validate has required fields
                    if purpose == "KYC":
                        if "spec" in parsed or ("steps" in parsed and isinstance(parsed.get("steps"), list)):
                            return parsed
                    else:  # AML_RISK
                        if "spec" in parsed or ("rules" in parsed and isinstance(parsed.get("rules"), list)):
                            return parsed
            except json.JSONDecodeError:
                continue
    
    # Strategy 3: Extract first JSON object substring using regex
    # Find first { ... } that looks like JSON
    json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_object_pattern, response_text, re.DOTALL)
    if matches:
        for match in matches:
            try:
                parsed = json.loads(match.strip())
                if isinstance(parsed, dict):
                    # Validate has required fields
                    if purpose == "KYC":
                        if "spec" in parsed or ("steps" in parsed and isinstance(parsed.get("steps"), list)):
                            return parsed
                    else:  # AML_RISK
                        if "spec" in parsed or ("rules" in parsed and isinstance(parsed.get("rules"), list)):
                            return parsed
            except json.JSONDecodeError:
                continue
    
    # Strategy 4: Try to find JSON object boundaries manually
    start = response_text.find("{")
    if start >= 0:
        # Find matching closing brace
        brace_count = 0
        end = start
        for i in range(start, len(response_text)):
            if response_text[i] == "{":
                brace_count += 1
            elif response_text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        if end > start:
            try:
                parsed = json.loads(response_text[start:end])
                if isinstance(parsed, dict):
                    # Validate has required fields
                    if purpose == "KYC":
                        if "spec" in parsed or ("steps" in parsed and isinstance(parsed.get("steps"), list)):
                            return parsed
                    else:  # AML_RISK
                        if "spec" in parsed or ("rules" in parsed and isinstance(parsed.get("rules"), list)):
                            return parsed
            except json.JSONDecodeError:
                pass
    
    # All strategies failed
    raise ValueError(
        f"Could not extract valid JSON from OpenAI response. "
        f"Response preview: {response_text[:200]}..."
    )
