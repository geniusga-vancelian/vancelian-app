# Système email MJML — Arquantix

> Pipeline de rendu HTML e-mail **strict, in-process et compatible IA**, basé sur MJML 5
> + composants Mustache + variables typées Zod. Coexiste avec le système IA historique
> (`src/lib/ai-email/`) qui sera migré progressivement (voir Phase 6).

## TL;DR

```bash
npm run emails:build      # compile tous les templates × locales dans emails/rendered/
npm run emails:preview    # serveur local http://localhost:5757/
npm run emails:validate   # validation MJML strict + Zod sur tous les templates
npm run test:email-mjml   # tests unitaires (node:test + tsx)
```

Admin UI : `/admin/email/design` (onglet « MJML templates »)
Preview chrome-free : `/preview/email/<templateId>?locale=fr|en`

---

## Architecture

```
emails/
├── mjml/
│   ├── tokens/           # source unique (JSON) consommée par MJML + DS React
│   │   ├── colors.json
│   │   ├── typography.json
│   │   ├── layout.json
│   │   └── index.ts
│   ├── partials/         # fragments Mustache utilisés via {{> name}}
│   │   ├── head.mjml
│   │   └── preheader.mjml
│   ├── components/       # briques réutilisables (sections autonomes ou inline)
│   │   ├── Button.mjml          # inline (mj-button)
│   │   ├── SecondaryButton.mjml # inline
│   │   ├── Eyebrow.mjml
│   │   ├── Divider.mjml
│   │   ├── Spacer.mjml
│   │   ├── HeaderL1.mjml        # hero pleine largeur (image + titre)
│   │   ├── HeaderL2.mjml        # standard (logo + nav)
│   │   ├── HeaderL3.mjml        # minimal (logo centré)
│   │   ├── Footer.mjml
│   │   ├── Card.mjml
│   │   ├── TwoColumns.mjml
│   │   ├── CTASection.mjml
│   │   ├── AlertBox.mjml
│   │   ├── OTPCode.mjml
│   │   ├── TransactionSummary.mjml
│   │   ├── LegalDisclaimer.mjml
│   │   ├── Signature.mjml
│   │   ├── ProductHighlight.mjml
│   │   └── TextBlock.mjml
│   ├── layouts/          # vide pour l’instant (pattern Mustache, pas mj-include)
│   └── templates/        # templates de bout-en-bout (1 fichier = 1 e-mail type)
│       ├── newsletter-quarterly.mjml
│       ├── otp-login.mjml
│       ├── transaction-confirmation.mjml
│       └── welcome.mjml
├── fixtures/             # variables d’exemple par template (preview/build/tests)
│   ├── newsletter-quarterly.json
│   ├── otp-login.json
│   ├── transaction-confirmation.json
│   └── welcome.json
└── rendered/             # SORTIE git-ignored — produite par emails:build
    ├── newsletter-quarterly.fr.html
    ├── newsletter-quarterly.en.html
    └── ...

src/lib/email/
├── index.ts              # façade publique
├── mjmlRender.ts         # mjml2html (CJS via createRequire), in-process, strict
├── interpolate.ts        # Mustache + validation Zod (EmailTemplateVarsError)
├── loadPartials.ts       # charge auto components/ + partials/ comme partials Mustache
├── templateRegistry.ts   # registry { id → { mjmlPath, varsSchema, subject(locale) } }
├── renderTemplate.ts     # pipeline complet : validate → interpolate → MJML → HTML + text
├── sendAdapter.ts        # interface { send(payload) } — noop / console (futur SES/Resend)
├── types.ts              # EmailTemplateId, EmailLocale, *VarsSchema, RenderedEmail
└── __tests__/            # node:test + tsx

src/app/
├── api/admin/email/preview/route.ts   # GET ?templateId&locale&inline ; POST { templateId, vars }
└── preview/email/[template]/page.tsx  # iframe chrome-free, sélecteur locale
```

---

## Pipeline de rendu (1 schéma)

```
caller (admin UI / IA chat / business code)
        │
        ▼
renderTemplate({ templateId, locale, vars })
        │
        ├── 1. lookup template dans EMAIL_TEMPLATES (registry)
        ├── 2. validateVars(template.varsSchema, vars)   ← Zod strict (refuse l’input IA invalide)
        ├── 3. lecture du fichier emails/mjml/templates/<id>.mjml
        ├── 4. loadEmailPartials() ← charge components/ + partials/ comme partials Mustache
        ├── 5. interpolate(mjmlSource, vars, partials)   ← Mustache (escape HTML par défaut)
        ├── 6. renderMjmlString(interpolated, { strict }) ← MJML 5 in-process
        └── 7. retourne { subject (localisé), html, text, locale, templateId }
        │
        ▼
sendAdapter.send({ to, subject, html, text, ... })
        │
        ▼
provider (noop / console / futur SES / Resend)
```

---

## Comment ajouter un nouveau template

### 1. Créer le fichier MJML

`emails/mjml/templates/<id>.mjml` :

```mjml
<mjml>
  {{> head}}
  <mj-body background-color="#F4F4F4" width="600px">
    {{> preheader}}
    {{> HeaderL3}}

    <mj-section padding="32px" background-color="#FFFFFF">
      <mj-column>
        <mj-text font-size="22px" font-weight="500">{{title}}</mj-text>
        <mj-text>{{body}}</mj-text>
      </mj-column>
    </mj-section>

    {{#cta}}{{> CTASection}}{{/cta}}
    {{> Footer}}
  </mj-body>
</mjml>
```

> **Conventions Mustache** :
>
> - `{{var}}` substitue avec **escape HTML** (sécurisé par défaut).
> - `{{{var}}}` substitue **sans** escape (à n’utiliser qu’avec des valeurs validées par schéma).
> - `{{#section}}…{{/section}}` rend uniquement si `section` est truthy ; pour un array, itère.
> - `{{> Partial}}` inline le composant `emails/mjml/components/Partial.mjml` (auto-chargé).
> - Les partials voient le **scope Mustache courant** : passer leurs « props » via une section.

### 2. Définir le schéma Zod

`src/lib/email/types.ts` :

```typescript
export const myTemplateVarsSchema = z.object({
  locale: z.enum(SUPPORTED_EMAIL_LOCALES),
  preheader: z.string().max(140),
  assetOrigin: z.string().url(),
  title: z.string().max(120),
  body: z.string().max(700),
  cta: z.object({
    eyebrow: z.string().max(40).optional(),
    title: z.string().max(80),
    body: z.string().max(280),
    cta: z.object({
      label: z.string().max(40),
      href: z.string().url(),
    }),
  }).optional(),
  footer: footerSchema,
})

export type MyTemplateVars = z.infer<typeof myTemplateVarsSchema>
```

Puis ajouter l’ID dans `EMAIL_TEMPLATE_IDS`.

### 3. Enregistrer dans le registry

`src/lib/email/templateRegistry.ts` :

```typescript
'my-template': {
  id: 'my-template',
  mjmlPath: 'templates/my-template.mjml',
  varsSchema: myTemplateVarsSchema,
  subject: (vars, locale) => locale === 'fr' ? `Mon sujet · ${vars.title}` : `My subject · ${vars.title}`,
  description: 'Description courte (utilisée par la sidebar admin).',
},
```

### 4. Ajouter une fixture

`emails/fixtures/my-template.json` :

```json
{
  "vars": {
    "preheader": "…",
    "assetOrigin": "https://www.arquantix.com",
    "title": "…",
    "body": "…",
    "footer": { "...": "..." }
  }
}
```

### 5. Tester

```bash
npm run emails:validate   # valide le template + sa fixture en MJML strict
npm run emails:build      # produit le HTML
npm run emails:preview    # serveur local pour inspection visuelle
```

Le template apparaît automatiquement dans `/admin/email/design` (onglet MJML).

---

## Comment réutiliser les composants

### Composants top-level (sections)

À placer **directement dans `<mj-body>`**, encapsulés dans une section Mustache pour passer
les variables :

```mjml
{{#hero}}{{> HeaderL1}}{{/hero}}        <!-- vars : { eyebrow, title, kicker, imageUrl, cta?, assetOrigin? } -->
{{#intro}}{{> TextBlock}}{{/intro}}     <!-- vars : { eyebrow?, heading?, paragraphs[], cta? } -->
{{#summary}}{{> TransactionSummary}}{{/summary}}  <!-- vars : { title?, rows: [{ label, value }] } -->
```

### Composants inline (boutons)

À placer **dans une `<mj-column>`**, depuis un autre composant ou directement :

```mjml
<mj-section><mj-column>
  ...
  {{#cta}}{{> Button}}{{/cta}}            <!-- vars : { label, href, dark?, align? } -->
  {{#cta}}{{> SecondaryButton}}{{/cta}}   <!-- vars : { label, href, onDark?, align? } -->
</mj-column></mj-section>
```

---

## Variables dynamiques pour l’IA chat

L’IA produit un objet JSON conforme au schéma Zod du template ciblé. Le pipeline :

1. Reçoit `{ templateId, locale, vars }` via `POST /api/admin/email/preview`.
2. Valide `vars` strictement avec Zod (refuse toute clé manquante / type incorrect).
3. Rend en HTML via le pipeline MJML strict.

Les schémas Zod sont **explicitement bornés** (longueurs max, regex OTP, URLs valides) pour
éviter qu’un prompt malicieux n’injecte du contenu trop long ou cassé.

> En cas d’erreur d’interpolation/validation, l’API retourne un statut `400` avec
> `{ error, code: 'INVALID_VARS' | 'MJML_INVALID', issues: [...] }` exploitable côté UI.

---

## Bonnes pratiques email respectées

| Bonne pratique | Comment c’est garanti |
|---|---|
| Largeur max 600 px | `mj-body width="600px"` (template-level) |
| Tables (pas flex/grid) | Output natif MJML (juice + table layout) |
| CSS inline | MJML inline les styles automatiquement |
| Outlook compat (boutons VML) | MJML émet les conditional comments + VML automatiquement |
| Mobile-first responsive | `mj-section`/`mj-column` natifs MJML |
| Fallback fonts | `mj-attributes` global avec stack système |
| Images alt | `mj-image alt="…"` (à respecter dans les composants) |
| Dark mode meta | `@media (prefers-color-scheme: dark)` dans `partials/head.mjml` |
| Pas de SVG inline | Wordmark fourni en **PNG** (`logo-wordmark-{black,white}.png`, 7 KB chacun) |
| Pas de runtime npx | `mjml` installé en local, `mjml2html` appelé in-process |

---

## Migration progressive depuis le système historique

Le module `src/lib/ai-email/` (spec JSON → `buildMjml` string concat → `compileMjml` via
`npx mjml`) **reste opérationnel**. Voir Phase 6 du plan pour la convergence (bridge
`buildMjmlV2` qui réutilisera les composants MJML, et migration de `compileMjml` vers
`mjml2html` in-process).

Les pages admin `/admin/email-modules`, `/admin/email-templates`, `/admin/emails` sont
**inchangées** par cette refonte.

---

## Envoi réel (futur)

`src/lib/email/sendAdapter.ts` expose une interface `EmailSendAdapter` avec deux
implémentations actuelles :

- `noopSendAdapter` (défaut) : ne fait rien.
- `consoleSendAdapter` : log structuré sur stdout.

Pour brancher un provider (SES, Resend, Postmark…) :

1. Créer un fichier `sendAdapters/<provider>.ts` qui implémente `EmailSendAdapter`.
2. L’enregistrer dans `getEmailSendAdapter()` (sélection via `EMAIL_SEND_ADAPTER` env var).
3. Documenter la config (`SES_FROM_EMAIL`, `RESEND_API_KEY`, etc.) dans `.env.example`.

> Aucun envoi n’est branché aujourd’hui — c’est volontaire. Voir
> `docs/EMAIL_WORKFLOW.md` pour le statut produit (Export/Send marqué *future*).

---

## Tests

```bash
npm run test:email-mjml
```

Couvre :

- `interpolate.test.ts` : escape HTML, sections, partials, validation Zod.
- `mjmlRender.test.ts` : rendu MJML, exception strict.
- `renderTemplate.test.ts` : E2E pour chaque template × locale (avec sa fixture).

> Le test E2E vérifie aussi qu’**aucun placeholder Mustache `{{ }}` ne subsiste** dans le
> HTML final — tout var manquante est immédiatement détectée.

---

## Convention de typage Vitest / node:test

Ce repo utilise `node --import tsx --test` (test runner natif Node) avec `tsx` pour
TypeScript. **Pas de Vitest**. Les tests email suivent ce pattern et sont enregistrés
via `npm run test:email-mjml`.
