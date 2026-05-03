# Tests E2E (Playwright) — site web

## Portée actuelle

- **`multilingual.spec.ts`** : `/` → `/{locale}`, `/{locale}/e2e-smoke`, redirection legacy `/e2e-smoke` → `/fr/e2e-smoke`, canonical, **si** balises `link[rel=alternate][hreflang]` présentes (origine site configurée) alors URLs sans `?locale=`, `html lang`, cookie vs URL sur chemins localisés, footer (seed).

## Prérequis

1. **Base de données** accessible (`DATABASE_URL` dans `.env` / `.env.local` du service web).
2. **Seed** incluant la page CMS `e2e-smoke` et les marqueurs footer E2E (`© E2E-FOOTER-FR` / `© E2E-FOOTER-EN`) : `npm run db:seed` (ou `db:sync`) depuis `services/arquantix/web`.
3. **Navigateurs Playwright** (une fois) : `npx playwright install chromium`

## Lancer

Depuis `services/arquantix/web` :

```bash
# Serveur déjà démarré (recommandé en local)
export PLAYWRIGHT_SKIP_WEBSERVER=1
npm run test:e2e
```

Ou laisser Playwright démarrer `next dev` (sans `PLAYWRIGHT_SKIP_WEBSERVER`) — plus lent, nécessite DB quand même.

Variables utiles :

- `PLAYWRIGHT_BASE_URL` — défaut `http://127.0.0.1:3000`
- `PLAYWRIGHT_SKIP_WEBSERVER=1` — ne pas lancer `npm run dev`

## Non couvert (volontairement)

- Admin footer, login, CMS complet.
- Couverture exhaustive des textes métier (hors marqueurs seed).
- Toutes les routes du site.

## Comportement transitoire (routes non migrées)

Sur les pages **sans** segment `/{fr|en|it}` en tête d’URL (ex. `/e2e-smoke`), le layout/footer suivent encore surtout le **cookie** / défaut — comme avant la phase 2A. Sur **`/fr`**, **`/en`**, **`/it`** (home), le middleware pose `x-arq-locale` : **l’URL prime** sur le cookie pour `html lang` et le footer. Voir `docs/multilingual-web-system.md`.
