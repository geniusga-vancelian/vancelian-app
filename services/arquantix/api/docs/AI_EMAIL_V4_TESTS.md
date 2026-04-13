# AI Email Builder V4 - Tests Manuels

## Checklist de tests pour Slots Éditoriaux + Éditeur Content-Only

### Test 1: Ajouter une IMAGE optionnelle

**Objectif**: Vérifier qu'on peut ajouter un bloc IMAGE optionnel dans un template.

**Steps**:
1. Ouvrir `/admin/ai/email`
2. Sélectionner template "Newsletter"
3. Mode "AI Copilot": générer un email avec prompt "Create a newsletter"
4. Noter la structure initiale
5. Passer en mode "Manual Edit"
6. Cliquer "Add Optional Block" → sélectionner "Image"
7. Vérifier:
   - Nouveau bloc IMAGE ajouté avant le FOOTER
   - Badge "Optional" visible
   - Bouton "Remove" visible
8. Éditer l'IMAGE: ajouter URL, alt_text, caption
9. Vérifier que le rendu MJML/HTML se met à jour

**Résultat attendu**: ✅ IMAGE ajoutée, éditable, supprimable

---

### Test 2: Ajouter 2 images → 2e refusée + warning

**Objectif**: Vérifier que max_occurrences est respecté.

**Steps**:
1. En mode "Manual Edit", avec une IMAGE déjà présente
2. Cliquer "Add Optional Block" → "Image" (2e fois)
3. Vérifier:
   - 2e IMAGE ajoutée
4. Ajouter une 3e IMAGE
5. Vérifier:
   - 3e IMAGE ajoutée (max=3)
6. Ajouter une 4e IMAGE
7. Vérifier:
   - 4e IMAGE refusée ou warning généré
   - Message: "Ignored extra IMAGE block (max=3)"

**Résultat attendu**: ✅ Max occurrences respecté, warnings générés

---

### Test 3: Supprimer CTA → refusé

**Objectif**: Vérifier qu'on ne peut pas supprimer un bloc core.

**Steps**:
1. En mode "Manual Edit"
2. Localiser le bloc CTA (core block)
3. Vérifier:
   - Badge "Core" visible
   - Pas de bouton "Remove" visible
4. Si bouton "Remove" présent (bug), cliquer
5. Vérifier:
   - Bloc non supprimé
   - Warning: "Cannot remove core block CTA"

**Résultat attendu**: ✅ Core blocks non supprimables

---

### Test 4: Éditer texte manuellement → rendu MJML OK

**Objectif**: Vérifier que l'édition manuelle met à jour le rendu.

**Steps**:
1. Mode "Manual Edit"
2. Localiser un bloc TEXT
3. Cliquer "Edit"
4. Modifier le "Body" text
5. Cliquer "Save"
6. Vérifier:
   - Bloc mis à jour dans la liste
7. Vérifier le rendu (EmailOutput):
   - MJML recompilé
   - HTML mis à jour
   - Nouveau texte visible dans le preview

**Résultat attendu**: ✅ Édition manuelle → rendu OK

---

### Test 5: IA propose une nouvelle section → ignorée

**Objectif**: Vérifier que l'IA ne peut pas ajouter de blocs core non autorisés.

**Steps**:
1. Mode "AI Copilot"
2. Template "Welcome Email" sélectionné
3. Structure locked: ON
4. Envoyer prompt: "Add a new section with a table"
5. Vérifier dans la réponse:
   - Structure reste identique (5 blocs core)
   - Aucun bloc "table" ajouté
   - Warnings présents: "Cannot add core block..." ou "Ignored extra block..."
6. Vérifier que seuls les textes ont été modifiés

**Résultat attendu**: ✅ Structure core verrouillée, IA ne peut pas ajouter

---

### Test 6: IA propose IMAGE optionnelle → acceptée

**Objectif**: Vérifier que l'IA peut ajouter des blocs optionnels.

**Steps**:
1. Mode "AI Copilot"
2. Template "Newsletter" sélectionné
3. Structure locked: ON
4. Envoyer prompt: "Add an image after the title"
5. Vérifier dans la réponse:
   - IMAGE ajoutée (si max_occurrences OK)
   - Structure core préservée
   - Pas de warnings si max respecté
6. Vérifier le rendu:
   - Image visible dans le preview

**Résultat attendu**: ✅ Blocs optionnels peuvent être ajoutés par IA

---

### Test 7: Switch Manual → AI → Manual → spec cohérente

**Objectif**: Vérifier la cohérence lors des changements de mode.

**Steps**:
1. Mode "AI Copilot": générer un email
2. Noter la structure (nombre de blocs)
3. Passer en mode "Manual Edit"
4. Vérifier:
   - Même structure affichée
   - Tous les blocs présents
5. Éditer un bloc TEXT manuellement
6. Passer en mode "AI Copilot"
7. Envoyer prompt: "Make the intro shorter"
8. Vérifier:
   - Structure préservée
   - Texte modifié
9. Revenir en mode "Manual Edit"
10. Vérifier:
    - Structure toujours cohérente
    - Modifications IA visibles

**Résultat attendu**: ✅ Spec cohérente entre modes

---

### Test 8: Ajouter DIVIDER optionnel

**Objectif**: Vérifier l'ajout d'un DIVIDER optionnel.

**Steps**:
1. Mode "Manual Edit"
2. Template "Newsletter" (qui a déjà un DIVIDER core)
3. Cliquer "Add Optional Block" → "Divider"
4. Vérifier:
   - DIVIDER ajouté
   - Badge "Optional"
   - Bouton "Remove" visible
5. Ajouter un 2e DIVIDER
6. Vérifier:
   - 2e DIVIDER ajouté (max=2)
7. Ajouter un 3e DIVIDER
8. Vérifier:
   - 3e refusé ou warning

**Résultat attendu**: ✅ DIVIDER optionnel ajoutable, max respecté

---

### Test 9: Éditeur validation (champs requis)

**Objectif**: Vérifier que les champs requis sont validés.

**Steps**:
1. Mode "Manual Edit"
2. Éditer un bloc HERO
3. Effacer le champ "Title" (requis)
4. Cliquer "Save"
5. Vérifier:
   - Validation côté client (message d'erreur ou champ highlighté)
   - Bloc non sauvegardé si invalide
6. Remplir "Title"
7. Cliquer "Save"
8. Vérifier:
   - Bloc sauvegardé

**Résultat attendu**: ✅ Validation des champs requis

---

### Test 10: Max length validation

**Objectif**: Vérifier que les max lengths sont respectés.

**Steps**:
1. Mode "Manual Edit"
2. Éditer un bloc TEXT
3. Dans "Body", taper plus de 1500 caractères
4. Vérifier:
   - Compteur affiche "1500 / 1500"
   - Input empêche de dépasser (ou tronque)
5. Éditer un bloc HERO
6. Dans "Title", taper plus de 120 caractères
7. Vérifier:
   - Max length respecté

**Résultat attendu**: ✅ Max lengths respectés

---

## Résultats attendus globaux

- ✅ Slots optionnels fonctionnent (ajout/suppression)
- ✅ Core blocks verrouillés (non supprimables)
- ✅ Éditeur manuel fonctionne (édition props)
- ✅ Rendu MJML/HTML mis à jour après édition
- ✅ IA respecte structure core + peut ajouter optionnels
- ✅ Cohérence entre modes AI/Manual
- ✅ Validations côté client (required, max length)
- ✅ Warnings informatifs générés

## Notes

- Les tests peuvent être automatisés plus tard
- Documenter tout comportement inattendu
- Vérifier que les warnings backend sont affichés dans l'UI (toast)









