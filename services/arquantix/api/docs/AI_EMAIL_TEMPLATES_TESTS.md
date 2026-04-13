# AI Email Templates - Tests Manuels

## Checklist de tests

### Test 1: Template selection et génération initiale

**Objectif**: Vérifier qu'un template peut être sélectionné et génère un email avec la structure correcte.

**Steps**:
1. Ouvrir `/admin/ai/email`
2. Sélectionner template "Newsletter" dans le dropdown
3. Envoyer prompt: "Write a January market newsletter"
4. Vérifier que l'email généré contient:
   - SECTION_TITLE (centered)
   - TEXT (body)
   - DIVIDER
   - TEXT (body)
   - FEATURE_CARDS (3up)
   - CTA
   - FOOTER
5. Vérifier que le nombre de blocs correspond au template (7 blocs)
6. Vérifier que l'ordre est correct

**Résultat attendu**: ✅ Email généré avec structure exacte du template newsletter_v1

---

### Test 2: Structure locked - refus d'ajout de blocs

**Objectif**: Vérifier que la structure est verrouillée et que l'IA ne peut pas ajouter de blocs.

**Steps**:
1. Sélectionner template "Welcome Email"
2. Envoyer prompt: "Add a table showing our features"
3. Vérifier dans la réponse:
   - Structure reste identique (5 blocs)
   - Aucun bloc "table" ajouté
   - Warnings présents si bloc ignoré
4. Vérifier que le contenu a été modifié (textes, URLs) mais pas la structure

**Résultat attendu**: ✅ Structure inchangée, warnings si tentatives d'ajout

---

### Test 3: Structure locked - refus de modification de structure

**Objectif**: Vérifier que l'IA ne peut pas modifier les types/variants de blocs.

**Steps**:
1. Sélectionner template "Welcome Email"
2. Envoyer prompt: "Add 2 extra sections and change the hero to have an image"
3. Vérifier:
   - Nombre de blocs reste 5
   - HERO reste variant "text_only" (pas "image_top")
   - Warnings présents
4. Vérifier que seuls les textes/URLs ont été modifiés

**Résultat attendu**: ✅ Structure verrouillée, warnings générés

---

### Test 4: Itération - modification de contenu uniquement

**Objectif**: Vérifier que les itérations modifient uniquement le contenu, pas la structure.

**Steps**:
1. Sélectionner template "Newsletter"
2. Envoyer prompt: "Write a January market newsletter"
3. Noter la structure générée
4. Envoyer second prompt: "Shorten the intro text and make it more concise"
5. Vérifier:
   - Structure identique (même nombre, même ordre, mêmes types/variants)
   - Seulement le texte du premier TEXT block a été modifié
   - Pas de warnings

**Résultat attendu**: ✅ Structure inchangée, contenu modifié uniquement

---

### Test 5: Switch template et reset

**Objectif**: Vérifier que changer de template et reset fonctionne correctement.

**Steps**:
1. Sélectionner template "Welcome Email"
2. Envoyer prompt: "Create a welcome email"
3. Noter la structure (5 blocs)
4. Cliquer "Reset to template"
5. Vérifier:
   - Messages effacés
   - previousSpec remis à null
6. Changer template vers "Project Update"
7. Envoyer prompt: "Announce new dashboard features"
8. Vérifier:
   - Structure correspond au template "Project Update" (7 blocs)
   - HERO avec variant "image_top"
   - BULLETS présent
   - IMAGE présent

**Résultat attendu**: ✅ Reset fonctionne, nouveau template appliqué correctement

---

### Test 6: Template par défaut si non fourni

**Objectif**: Vérifier que si templateId n'est pas fourni, le défaut est utilisé.

**Steps**:
1. Ouvrir `/admin/ai/email`
2. Ne pas sélectionner de template (ou laisser "welcome_v1")
3. Envoyer prompt: "Create an email"
4. Vérifier:
   - Email généré avec structure welcome_v1 (5 blocs)
   - Warnings contient "templateId missing -> defaulted to welcome_v1" (si templateId vraiment absent)

**Résultat attendu**: ✅ Template par défaut utilisé, warning présent

---

### Test 7: Lock structure toggle

**Objectif**: Vérifier que le toggle "Structure locked" fonctionne.

**Steps**:
1. Sélectionner template "Welcome Email"
2. Décocher "Structure locked"
3. Envoyer prompt: "Add a divider and change the hero to image_top"
4. Vérifier:
   - Structure peut être modifiée (blocs ajoutés/modifiés)
   - Pas de warnings de structure lock
5. Recocher "Structure locked"
6. Envoyer prompt: "Add another section"
7. Vérifier:
   - Structure verrouillée à nouveau
   - Warnings si tentatives de modification

**Résultat attendu**: ✅ Toggle fonctionne, lock peut être désactivé

---

### Test 8: Warnings affichés

**Objectif**: Vérifier que les warnings sont correctement affichés dans la réponse.

**Steps**:
1. Sélectionner template "Welcome Email"
2. Envoyer prompt: "Add 3 new sections"
3. Vérifier dans la réponse JSON:
   - `warnings` array présent
   - Contient message sur blocs ignorés
4. Vérifier dans l'UI (si affichage implémenté):
   - Warnings visibles pour l'utilisateur

**Résultat attendu**: ✅ Warnings présents et informatifs

---

### Test 9: Templates list API

**Objectif**: Vérifier que l'API de liste des templates fonctionne.

**Steps**:
1. Appeler `GET /api/ai/email/templates`
2. Vérifier:
   - Retourne array de 4 templates
   - Chaque template a: id, name, description, locked
   - Templates: welcome_v1, newsletter_v1, project_update_v1, investor_update_v1

**Résultat attendu**: ✅ Liste complète et correcte

---

### Test 10: Compatibilité backward

**Objectif**: Vérifier que les appels sans templateId fonctionnent toujours.

**Steps**:
1. Appeler `POST /api/ai/email/compose` sans `templateId`
2. Vérifier:
   - Email généré (utilise welcome_v1 par défaut)
   - Warning présent: "templateId missing -> defaulted to welcome_v1"
   - Pas d'erreur

**Résultat attendu**: ✅ Backward compatible, défaut appliqué

---

## Résultats attendus globaux

- ✅ Tous les templates génèrent des emails avec structure correcte
- ✅ Structure verrouillée empêche modifications non autorisées
- ✅ Itérations modifient uniquement le contenu
- ✅ Reset et switch template fonctionnent
- ✅ Warnings informatifs générés
- ✅ Backward compatible

## Notes

- Les tests peuvent être automatisés plus tard
- Pour l'instant, tests manuels suffisants pour MVP
- Documenter tout comportement inattendu









