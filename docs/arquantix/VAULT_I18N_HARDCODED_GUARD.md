# Garde-fou i18n — Vault public (`components/exclusive-offer/**`)

## Convention

Aucun texte user-facing ne doit être hardcodé dans les composants du Vault public.

| Type de texte | Solution |
|---|---|
| Contenu spécifique au module (titres, CTA éditoriaux, etc.) | Prop CMS traduisible (ex. `moduleTitle`, `ctaLabel`) — gérée dans Vault Builder, scannée par l'intégrité i18n, auto-traduisible |
| Libellé générique d'UI (Download, Map, Watch video, empty state, etc.) | `vaultCommonCta(locale, key)` — défini dans `src/lib/i18n/vaultCommonCta.ts`, mutualisé FR / EN / IT |

## Filet de sécurité automatisé

Un test Node.js scanne en continu le périmètre `services/arquantix/web/src/components/exclusive-offer/**` :

```bash
cd services/arquantix/web
npm run test:vault-no-hardcoded-strings
```

Sources :

- Scanner : `src/lib/i18n/vaultHardcodedStringsScanner.ts`
- Tests : `src/lib/i18n/vaultHardcodedStringsScanner.test.ts`

## Ce qui est détecté

- Texte JSX visible (mono-ligne et multi-ligne) : `<button>Download</button>`, ou bloc `<p>\n  Texte\n</p>`
- Attributs sensibles avec valeur littérale : `aria-label="..."`, `title="..."`, `alt="..."`, `placeholder="..."`

## Ce qui est ignoré (faux positifs évités)

- Interpolations JSX : `<button>{label}</button>`, `<button aria-label={label} />`
- Valeurs vides : `<img alt="" />`
- Chaînes non textuelles : classes Tailwind, paths, ponctuation seule, symboles
- Logs dev, commentaires, types/enums techniques
- Valeurs venant déjà de props CMS (interpolation pure)

## Allowlist (exceptions justifiées)

Deux mécanismes au choix.

### Ligne par ligne (préféré)

Ajouter un commentaire juste au-dessus de la ligne à exempter.

Format JSX (recommandé dans un .tsx) :

```tsx
{/* i18n-allow-next-line: fallback admin/debug — module inconnu */}
<p className="font-medium">Module « {mod.type} »</p>
```

Format JS standard (hors JSX) :

```ts
// i18n-allow-next-line: cas justifié, voir TICKET-123
const label = 'Hardcoded string'
```

### Fichier entier (à éviter)

À réserver aux fichiers internes admin/debug non rendus en production publique.

```ts
// i18n-allow-file: composant interne admin/debug
```

Toute exception doit indiquer une **raison explicite** après le `:`.

## Ajout d'une nouvelle clé commune

Pour ajouter un libellé générique d'UI dans `vaultCommonCta` :

1. Ouvrir `src/lib/i18n/vaultCommonCta.ts`.
2. Ajouter la clé dans `FR`, `EN`, `IT` (les trois locales sont obligatoires).
3. L'ajouter à `VAULT_COMMON_CTA_KEYS` (registre exposé pour audits).
4. Utiliser `vaultCommonCta(locale, 'ma_cle')` dans le composant.

## Ajout d'une nouvelle prop CMS traduisible

Pour ajouter un libellé éditable par module :

1. Étendre les props du module concerné (`VaultBuilder` admin + composant de rendu web).
2. Ajouter le champ à `vaultAllowlistedTextFields.ts` (intégrité i18n).
3. Si auto-traduction souhaitée : ajouter la logique dans `vaultAutoTranslateModules.ts`.
4. Côté rendu : `module.maProp?.trim() || vaultCommonCta(locale, 'cle_de_secours')`.

## Intégration CI / dev flow

Lancer le filet localement avant push :

```bash
npm run test:vault-no-hardcoded-strings
```

Le test échoue avec un rapport pointant fichier, ligne et type de violation, ainsi que la marche à suivre. Aucune dépendance supplémentaire requise — utilise uniquement `node --test` + `tsx`, déjà présents dans le repo.
