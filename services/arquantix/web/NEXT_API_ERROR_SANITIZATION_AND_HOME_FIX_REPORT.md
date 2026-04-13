# NEXT_API_ERROR_SANITIZATION_AND_HOME_FIX_REPORT.md

## Executive Summary

L’écran **Home** Flutter appelle plusieurs endpoints **Next.js** (`API_BASE_URL`, port 3000 par défaut). Lorsqu’une erreur se produisait **en dehors** du `try/catch` d’une route API, ou lorsque le serveur de dev Next ne trouvait pas les composants d’erreur Pages Router, le mobile recevait du **HTML** (message *missing required error components* + script de reload) au lieu de JSON.

Ce travail :

1. **Identifie** les routes consommées par le Home et les chemins les plus exposés.
2. **Uniformise** les réponses d’erreur **500** sous `src/app/api/mobile/flutter/**` au format `{ "error": "Internal server error", "message": "…" }` avec `Content-Type: application/json`.
3. **Renforce** les proxies **bootstrap** et **cash** pour refuser de relayer du HTML en le détectant côté Next.
4. **Aligne** `/api/blog` et `/api/blog/[slug]` sur le même **contrat JSON** (plus de `stack` dans le corps).
5. **Centralise** la logique serveur dans `src/lib/api/mobile-json-error.ts`.
6. **Durcit Flutter** : `userFacingHttpErrorMessage` / `responseBodyLooksLikeNonJsonApi` + message utilisateur fixe **en anglais** pour tout corps type HTML / page Next dev.
7. **Ajoute des tests** (Node + Flutter) sur le contrat JSON et la détection HTML.

## Broken Route Identified

Il n’y a pas **une seule** route statiquement « cassée » : le symptôme HTML apparaît lorsque **Next.js** génère une page d’erreur globale (dev) plutôt qu’une réponse de **Route Handler**. Les appels du Home les plus susceptibles d’être en cause en premier (latence, DB, volumétrie) :

| Priorité | Méthode | URL (relatif à `apiBaseUrl`) | Client Dart |
|----------|---------|------------------------------|-------------|
| 1 | GET | `/api/blog?locale=fr&page=…` | `BlogApi.getFeed` |
| 2 | GET | `/api/mobile/flutter/layouts/dashboard` | `DashboardLayoutApi.getDashboardLayout` |
| 3 | GET | `/api/mobile/flutter/bootstrap` | `home_screen.dart` (`http.get`) |
| 4 | GET | `/api/mobile/flutter/cash` | `CashApi` |
| 5 | GET | `/api/mobile/flutter/crypto-positions` | `CryptoPositionsApi` |
| 6 | GET | `/api/mobile/flutter/lending/earn/positions` | `PlacementsApi` |
| 7 | GET | `/api/mobile/flutter/portfolio/global/history` & `…/statistics` | `GlobalStatisticsApi` |
| 8 | GET | `/api/mobile/flutter/notifications/unread-count` | `NotificationsApi` |
| 9 | GET | `/api/mobile/flutter/vaults/...` ou `…/widgets/...` | `VaultsApi` (via modules dashboard) |

Les logs serveur structurés pour le blog incluent déjà `db`, `locale`, timings Prisma (`[api/blog] GET start`, `… failed` avec `serializeError`).

## Root Cause

1. **Next dev** : absence historique de `src/pages/_error.tsx` → HTML de secours *missing required error components* (corrigé dans un changement précédent ; ce rapport se concentre sur la **couche API + Flutter**).
2. **Handlers** : la plupart des routes mobile attrapaient les erreurs, mais le **corps** `500` n’était pas homogène (`Internal error` vs `Internal server error`, pas de `message`).
3. **Proxies** (`bootstrap`, `cash`, …) : `await res.json()` sur une réponse HTML/texte **amont** provoquait une exception ; selon le contexte, la chaîne d’erreur pouvait remonter différemment.
4. **Flutter** : affichage du **body brut** dans les exceptions / UI.

## Backend Fix

- **`src/lib/api/mobile-json-error.ts`**  
  - `mobileApiJsonError`, `logMobileApiFailure`, `safeApiMessageForClient`, `mobileApiFailureResponse`  
  - `readProxyJsonBody` : lecture `text` → garde anti-HTML → `JSON.parse`  
  - `mobileApiUpstreamInvalidResponse` : **502** JSON si l’amont n’est pas du JSON

- **`scripts/bulk-mobile-500-json.mjs`** (exécuté une fois)  
  - Remplace les `return NextResponse.json({ error: 'Internal server error' }, { status: 500 })` (et variante `Internal error`) par une réponse incluant **`message`** + en-tête **`Content-Type: application/json; charset=utf-8`** pour **59** fichiers sous `api/mobile/flutter`.

- **`bootstrap/route.ts`**, **`cash/route.ts`**  
  - Utilisent `readProxyJsonBody` + `mobileApiFailureResponse` / `mobileApiUpstreamInvalidResponse`.

- **`api/blog/route.ts`**, **`api/blog/[slug]/route.ts`**  
  - Erreurs : `logMobileApiFailure` + `mobileApiJsonError(500, safeApiMessageForClient(error))` — **plus de `stack` dans le JSON** renvoyé au client.

- **`layouts/dashboard/route.ts`**  
  - Catch : `mobileApiFailureResponse` (log + JSON contract).

## JSON Error Contract

Réponse d’erreur standard pour les API consommées par le mobile :

```json
{
  "error": "Internal server error",
  "message": "The request could not be completed."
}
```

- En **développement**, `message` peut contenir un extrait du message d’erreur (voir `safeApiMessageForClient`).
- Les erreurs **502** proxy utilisent un libellé dédié dans `message` (upstream invalide).

## Flutter Protection

- **`lib/core/http_error_display.dart`**  
  - `kContentTemporarilyUnavailable` = `Content temporarily unavailable. Please try again.`  
  - `responseBodyLooksLikeNonJsonApi`  
  - `userFacingHttpErrorMessage` : route les corps HTML / Next dev vers le message fixe ; sinon conserve l’extraction JSON / texte existante.

- **`BlogApiException`** : utilise `userFacingHttpErrorMessage` pour le champ affiché.

- **`DashboardLayoutApi`** : idem sur les erreurs HTTP.

- **`VaultsApi`** : idem + garde sur **200** si le corps ressemble à du HTML avant `jsonDecode`.

- **`home_screen.dart` (bootstrap)** : ignore les corps non-JSON ; `jsonDecode` dans un try/catch avec log debug.

## Tests Added

| Suite | Commande | Rôle |
|--------|----------|------|
| Next (contract) | `npm run test:mobile-json-contract` | Vérifie `mobileApiJsonError` : statut, `Content-Type`, clés `error`/`message`, absence de `<html` dans la sérialisation. |
| Flutter | `flutter test test/http_error_display_test.dart` | Détection Next dev / HTML ; message utilisateur constant ; JSON d’erreur API toujours lisible. |

## Maintenance

- Pour toute **nouvelle** route sous `api/mobile/flutter`, utiliser de préférence `mobileApiFailureResponse` / `mobileApiJsonError` dans le `catch`, ou au minimum le même **shape** JSON + en-tête UTF-8.
- Pour les **proxies** `fetch` + `res.json()`, préférer `readProxyJsonBody`.
- Ré-exécuter le script bulk n’est utile que si d’anciens patterns `Internal error` sans `message` réapparaissent :  
  `node scripts/bulk-mobile-500-json.mjs` (depuis `services/arquantix/web`).
