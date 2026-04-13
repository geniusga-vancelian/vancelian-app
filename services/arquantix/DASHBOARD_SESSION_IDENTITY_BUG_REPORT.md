# Rapport — bug session / identité dashboard (client admin par défaut)

## Cause racine

1. **Backend — résolution client « Flutter test »**  
   Les handlers sous `/api/app/*` utilisaient massivement `TestClientService.get_bootstrap()`, qui lit **`app_runtime_settings.current_flutter_test_client_id`** (client de test / admin sélectionné en admin), **sans** tenir compte du JWT Bearer. Toute requête authentifiée continuait donc à charger les données de ce client « courant test », pas celles du `PeClient` lié à la session réelle.

2. **BFF Next.js — proxy sans `Authorization`**  
   Plusieurs routes `/api/mobile/flutter/*` proxifiaient vers Python **sans** repasser l’en-tête **`Authorization`**, donc le backend voyait une requête **sans Bearer** et retombait sur le comportement « dev » = client test courant.

3. **JWT — clé `pid`**  
   Les access tokens peuvent porter **`pid`** pour l’identifiant personne ; le helper `_person_from_jwt` (2FA / sécurité) ne lisait que **`person_id`**, ce qui pouvait empêcher la résolution correcte selon l’émetteur du token.

4. **App Flutter — cash**  
   `CashApi.fetchCashData()` appelait le BFF **sans** Bearer, alors que le bootstrap du home envoyait déjà le token.

## Fichiers / zones impactés

- **Résolution identité mobile** : `api/services/test_clients/mobile_identity.py` (`client_from_access_token`, `resolve_bootstrap_client`, dépendance **`mobile_app_client`** / **`mobile_bearer`**).
- **Service test clients** : `api/services/test_clients/service.py` — `_client_or_bootstrap` et méthodes data avec `client: Optional[Client] = None`.
- **Router principal app** : `api/services/test_clients/router.py` — tous les endpoints `/api/app/*` du module utilisent `Depends(mobile_app_client)` au lieu de `get_bootstrap`.
- **Routers satellites** (même problème `_get_client` → `get_bootstrap`) :  
  `api/services/notifications/router.py`, `api/services/favorites/router.py`,  
  `api/services/price_alerts/router.py`, `api/services/price_alerts/orders_router.py`.
- **2FA / person JWT** : `api/services/security/deps.py` — lecture **`pid`** en plus de **`person_id`**.
- **BFF** : `web/src/lib/api/mobile-upstream-auth.ts` + toutes les routes `web/src/app/api/mobile/flutter/**/route.ts` qui proxifient vers `/api/app/*` — propagation **`upstreamHeadersWithAuth` / `jsonHeadersWithUpstreamAuth`**.
- **Flutter** : `mobile/lib/features/wallet/data/cash_api.dart` — envoi du Bearer via `SessionService`.

## Correctifs appliqués

- **Source de vérité avec Bearer** : si `Authorization: Bearer` est présent et décodable, le **`PeClient`** est résolu via `person_id` / `pid` / e-mail `sub` dans le JWT. **Aucun** fallback vers le client test dans ce cas ; si aucun client n’est lié → **404** explicite (`No client profile linked to this session.`).
- **Sans Bearer (dev / outils)** : comportement inchangé — `current_flutter_test_client_id` via `get_bootstrap` (nécessaire pour les flux sans session).
- **Tous les endpoints `/api/app/*` concernés** (y compris favoris, notifications, alertes prix, ordres déclenchés) passent par la même dépendance **`mobile_app_client`**.
- **BFF** : propagation systématique de l’`Authorization` client vers l’API Python.
- **Flutter** : cash aligné sur le même modèle que bootstrap (token session).

## Pourquoi l’« admin user » / client test apparaissait

Le client affiché n’était pas « l’admin » au sens produit, mais le **`pe_client`** pointé par **`current_flutter_test_client_id`** (souvent le client de seed / test sélectionné dans l’admin). Comme le JWT n’était pas utilisé pour résoudre le client sur la plupart des endpoints, **tous les utilisateurs** voyaient ce même client.

## Validation recommandée (manuelle)

1. Login utilisateur **non admin** → dashboard : soldes / profil / favoris / alertes = ce user.  
2. Fin d’inscription → navigation dashboard : idem.  
3. Cold start avec refresh token / session valide : pas de données d’un autre client.  
4. Bearer invalide ou JWT sans `PeClient` associé : **404** ou message clair, **pas** de données d’un autre utilisateur.  
5. Dev sans JWT : sélection du client test via admin ou `ARQUANTIX_AUTO_SELECT_TEST_CLIENT` inchangée.

## Durcissement session (session hardening)

- **Variable d’environnement** `ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES` : si `true` / `1`, les appels **sans** `Authorization` sur `/api/app/*` peuvent encore utiliser le client Flutter test (`current_flutter_test_client_id`). **Sinon** → **401** (`Authentication required.`). En production, laisser cette variable **désactivée** ; en local, la définir à `1` (voir `.env.arquantix.example`).
- **Bearer invalide** (signature / expiration) → **401** avec `WWW-Authenticate: Bearer` — ne plus confondre avec « pas de client ».
- **Bearer valide mais aucun `PeClient`** → **404** (`No client profile linked to this session.`) — **aucun** fallback test.
- **Wealth** (`/api/app/portfolio/wealth`, `/lending/positions`, `/borrowing/positions`) : le `client_id` en query a été supprimé ; l’identité vient uniquement de **`mobile_app_client`** (JWT).
- **Métriques alertes** (`GET /api/app/alerts/metrics`) : aligné sur la même dépendance **`mobile_app_client`**.
- **Tests** : `tests/test_mobile_identity_security.py` + fixture autouse `ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES=1` dans `conftest.py` pour les tests HTTP existants.

## Risques résiduels

- Toute **nouvelle** route sous `/api/app/*` doit utiliser **`Depends(mobile_app_client)`** (ou équivalent) et ne jamais reprendre `client_id` en paramètre utilisateur sans vérification JWT.
- Tests automatisés `tests/test_test_clients.py` : peuvent échouer si la base de test contient déjà des e-mails de clients (conflit 409) — indépendant de ce correctif.

## Logs

- **`security_mobile:`** (warning / info) : jeton invalide, route bloquée sans auth, fallback client test (dev uniquement), JWT valide sans profil client.
- Des **`logger.debug`** restent pour le résultat nominal (`client_id` résolu).
