# AI Email Builder - Rigid Templates System

## Vue d'ensemble

Le système de templates rigides permet de créer des emails à partir de structures préconstruites verrouillées. L'IA peut modifier le contenu (textes, URLs, props) mais ne peut pas changer la structure (types de blocs, ordre, nombre).

## Architecture

### 1. Templates Presets

**Dossier**: `api/services/ai_email/templates_presets/`

**Fichiers**:
- `types.py`: Définit `EmailTemplate` dataclass et registry
- `arquantix_v1.py`: Implémente 4 templates rigides

**Templates disponibles**:

1. **welcome_v1** (défaut)
   - Structure: HERO (text_only) → TEXT → FEATURE_CARDS (3up) → CTA → FOOTER
   - Usage: Email de bienvenue pour nouveaux utilisateurs

2. **newsletter_v1**
   - Structure: SECTION_TITLE → TEXT → DIVIDER → TEXT → FEATURE_CARDS → CTA → FOOTER
   - Usage: Newsletter mensuelle avec mises à jour marché

3. **project_update_v1**
   - Structure: HERO (image_top) → SECTION_TITLE → BULLETS → IMAGE → TEXT → CTA → FOOTER
   - Usage: Annonce de nouvelles fonctionnalités

4. **investor_update_v1**
   - Structure: HERO (text_only) → SECTION_TITLE → TEXT → BULLETS → DIVIDER → TEXT → CTA → FOOTER
   - Usage: Résumé de performance trimestriel

### 2. Structure Locking

**Fichier**: `api/services/ai_email/lock.py`

**Fonction principale**: `enforce_locked_structure(base: EmailSpec, proposed: EmailSpec)`

**Règles**:
- La structure (type+variant, ordre, nombre) doit rester identique à `base`
- Si `proposed` diffère, reconstruire en prenant la structure de `base`
- Copier uniquement les props compatibles bloc par bloc
- Toujours revalider via registry
- Retourner warnings si éléments ignorés

**Exemple**:
```python
base_spec = template.get_initial_spec("en")
proposed_spec = # ... généré par OpenAI

final_spec, warnings = enforce_locked_structure(base_spec, proposed_spec)
# final_spec a la même structure que base_spec
# mais avec le contenu modifié de proposed_spec
```

### 3. Agent avec Templates

**Fichier**: `api/services/ai_email/agent.py`

**Signature modifiée**:
```python
def compose_email_spec(
    prompt: str,
    previous_spec: Optional[EmailSpec] = None,
    locale: str = "en",
    template_id: Optional[str] = None,
    lock_structure: bool = True,
) -> Tuple[str, EmailSpec, List[str]]:
```

**Logique**:
1. Si `previous_spec` fourni → `base_spec = previous_spec`
2. Sinon → `base_spec = template.get_initial_spec(locale)` (selon `template_id`)
3. Appeler OpenAI avec prompt incluant structure locked
4. Parser Pydantic
5. Valider registry
6. Si `lock_structure`: appliquer `enforce_locked_structure`
7. Retourner `(assistant_text, spec_final, warnings)`

### 4. System Prompt avec Structure Locked

**Fichier**: `api/services/ai_email/system_prompt.py`

**Fonction**: `get_locked_structure_prompt()`

Le prompt inclut:
- Liste explicite des blocs attendus (type+variant, ordre)
- Instruction stricte: "STRUCTURE IS LOCKED"
- Seulement modifier: text content, URLs, props
- Ne PAS: ajouter/supprimer blocs, changer types/variants, réordonner

### 5. API Routes

**Backend FastAPI**: `api/services/ai_email/routes.py`

**GET `/api/ai/email/templates`**:
```json
[
  {
    "id": "welcome_v1",
    "name": "Welcome Email",
    "description": "Welcome new users...",
    "locked": true
  },
  ...
]
```

**POST `/api/ai/email/compose`** (modifié):
```json
{
  "prompt": "Create a welcome email",
  "locale": "en",
  "templateId": "welcome_v1",
  "lockStructure": true,
  "previous_spec": { ... }
}
```

**Response**:
```json
{
  "assistant_text": "...",
  "spec": { ... },
  "mjml": "...",
  "html": "...",
  "warnings": ["templateId missing -> defaulted to welcome_v1"],
  "templateId": "welcome_v1",
  "locked": true
}
```

**Frontend Next.js**: `web/src/app/api/ai/email/compose/route.ts`

- Proxy vers FastAPI backend
- Fallback si backend indisponible (sans templates)

### 6. Frontend UI

**Composant**: `web/src/components/ai-email/ChatStudio.tsx`

**Ajouts**:
- Sélecteur de template (dropdown)
- Toggle "Structure locked" (read-only visible, ON par défaut)
- Bouton "Reset to template" (remet `previousSpec` à null, clear messages)

**Flux**:
1. Charger templates au mount (`listEmailTemplates()`)
2. Sélectionner template (défaut: `welcome_v1`)
3. Envoyer `templateId` + `lockStructure` dans `composeEmail()`
4. Afficher warnings si présents

## Comment ajouter un nouveau template

### 1. Créer la fonction builder

Dans `api/services/ai_email/templates_presets/arquantix_v1.py`:

```python
def _create_my_template_v1(locale: str = "en") -> EmailSpec:
    """Template: My custom template"""
    return EmailSpec(
        subject="Default Subject",
        preheader="Default preheader",
        locale=locale,
        theme="arquantix_v1",
        blocks=[
            HeroBlock(...),
            TextBlock(...),
            FooterBlock(...),
        ],
    )
```

### 2. Enregistrer le template

```python
register_template(
    EmailTemplate(
        id="my_template_v1",
        name="My Template",
        description="Description of my template",
        locale_defaults=["en", "fr", "it"],
        initial_spec_builder=_create_my_template_v1,
        locked=True,
    )
)
```

### 3. Mettre à jour le frontend (optionnel)

Si besoin, ajouter le template à la liste dans `web/src/app/api/ai/email/templates/route.ts` (pour MVP, la liste est codée en dur).

## Règles "Locked Structure"

### Ce qui est verrouillé:
- Nombre de blocs
- Types de blocs (hero, text, etc.)
- Variants de blocs (text_only, centered, etc.)
- Ordre des blocs

### Ce qui peut être modifié:
- Contenu textuel (title, subtitle, body, heading)
- URLs (cta_url, image_url, etc.)
- Props optionnelles (hint, caption, alt_text, etc.)
- Subject et preheader
- Items dans les arrays (bullets, feature_cards)

### Exemple de modification autorisée:

**Base (template)**:
```json
{
  "blocks": [
    { "type": "hero", "variant": "text_only", "title": "Welcome" },
    { "type": "text", "variant": "body", "body": "Default text" }
  ]
}
```

**Proposé (par IA)**:
```json
{
  "blocks": [
    { "type": "hero", "variant": "text_only", "title": "Welcome to Arquantix" },
    { "type": "text", "variant": "body", "body": "Thank you for joining..." }
  ]
}
```

**Résultat (après lock)**:
```json
{
  "blocks": [
    { "type": "hero", "variant": "text_only", "title": "Welcome to Arquantix" },
    { "type": "text", "variant": "body", "body": "Thank you for joining..." }
  ]
}
```
✅ Structure identique, contenu modifié

### Exemple de modification refusée:

**Proposé (par IA)**:
```json
{
  "blocks": [
    { "type": "hero", "variant": "text_only", "title": "Welcome" },
    { "type": "text", "variant": "body", "body": "Text" },
    { "type": "cta", "variant": "primary", "label": "Click" }  // ❌ Bloc ajouté
  ]
}
```

**Résultat (après lock)**:
```json
{
  "blocks": [
    { "type": "hero", "variant": "text_only", "title": "Welcome" },
    { "type": "text", "variant": "body", "body": "Text" }
  ]
}
```
⚠️ Bloc CTA ignoré, warning généré

## Tests manuels

Voir `api/docs/AI_EMAIL_TEMPLATES_TESTS.md` pour la checklist complète.

**Tests essentiels**:
1. Choisir `newsletter_v1`, prompt "Write a January market newsletter" → structure inchangée
2. Dire "Add a table" → ignore + warnings + structure inchangée
3. Demander "add 2 extra sections" → ignore + warnings
4. Itération: "shorten the intro" → seulement texte modifié
5. Switch template → reset → spec repart du bon template

## Compatibilité

- **Backward compatible**: Si `templateId` absent, utilise `welcome_v1` par défaut + warning
- **Endpoints existants**: Continuent de fonctionner (sans templates)
- **Frontend**: Peut fonctionner sans templates (fallback)

## Variables d'environnement

- `BACKEND_URL` ou `NEXT_PUBLIC_BACKEND_URL`: URL du backend FastAPI (pour proxy)
- Pas de nouvelles variables requises









