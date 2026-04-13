# Audit — blocage à l’étape téléphone (« Le service est temporairement indisponible »)

**Contexte** : impossible de se connecter ou de créer un compte ; l’écran reste sur la saisie du numéro avec le message **« Le service est temporairement indisponible »**.

**Périmètre** : client Flutter `PasskeyApi` → `POST /auth/login/sms/start` ou `POST /auth/signup/sms/start` (FastAPI), sans modification backend dans ce rapport.

---

## 1. Origine exacte du texte affiché

La chaîne **« Le service est temporairement indisponible »** est produite **uniquement côté Flutter** dans `mobile/lib/features/security/passkeys/data/passkey_api.dart`, dans les cas suivants :

| Mécanisme | Détail |
|-----------|--------|
| **HTTP 408** | Timeout client (`Duration(seconds: 22)` sur la requête), y compris après un **second essai** automatique (400 ms) en cas de premier timeout. |
| **HTTP 5xx** | 500, 501, 502, 503, 504 — lorsque le corps ne fournit pas un `detail` exploitable par `parseFastApiErrorMessage`. |
| **Erreur réseau « serveur injoignable »** | `PasskeyApiException` avec `statusCode == 0` et corps sentinel `__net_server_unreachable__` ou `__net_generic__` (ex. *connection refused*, *connection reset*, TLS handshake côté « service indisponible »). |
| **Réponse 2xx non JSON ou pas un objet** | Après succès HTTP, échec de décodage JSON → exception synthétique **502** → même libellé via `_httpStatusUserMessage`. |

**Ce que ce message ne couvre pas** (autres libellés) :

- **404** → *« Service d’authentification introuvable… »* (pas le message signalé).
- **Pas de base URL auth** → *« URL du serveur d’authentification non configurée… »* (`No auth backend`).
- **Offline DNS typique** → *« Vérifiez votre connexion internet »* (sentinel `__net_offline__`).

**Conclusion** : le symptôme décrit correspond à **timeout**, **erreur serveur 5xx**, **connexion refusée / reset / TLS** vers l’hôte cible, ou **corps de réponse illisible** — et non à une simple absence de réseau « pur » (souvent).

---

## 2. Chaîne technique (où l’app envoie la requête)

1. **`SecureApiConfig.resolvedAuthApiBaseUrl`** (`mobile/lib/core/secure_api_config.dart`)  
   - Si `AUTH_API_BASE_URL` (dart-define) est **non vide** → utilisé tel quel.  
   - Sinon → dérivé de **`Config.apiBaseUrl`** (BFF Next, défaut `http://localhost:3000`) en **remplaçant le port par 8000** (ex. `http://127.0.0.1:3000` → `http://127.0.0.1:8000`).

2. **`PasskeyApi`** concatène : `{base}/auth/login/sms/start` ou `{base}/auth/signup/sms/start`.

3. **Backend** : routes FastAPI sous préfixe `/auth` (`mobile_otp_login_routes` / `signup_mobile_routes`) — chemins attendus : `/auth/login/sms/start`, `/auth/signup/sms/start`.

**Point critique** : l’auth SMS **ne passe pas par le BFF Next (port 3000)** dans ce client ; elle vise **directement** l’API Python sur **le port 8000** (sauf override `AUTH_API_BASE_URL`). Si seul Next est démarré, **rien n’écoute en général sur 8000** → *connection refused* → classification « serveur injoignable » → **même message utilisateur**.

---

## 3. Causes probables (ordre de fréquence attendu en dev / préprod)

1. **API FastAPI non démarrée ou pas sur le port attendu**  
   - Symptôme réseau : refus de connexion sur `host:8000`.  
   - Message utilisateur : **« Le service est temporairement indisponible »** (pas « joindre le serveur » générique).

2. **`API_BASE_URL` correct pour le téléphone (Next) mais machine sans FastAPI sur 8000**  
   - Très courant : le reste de l’app (bootstrap, etc.) fonctionne via Next, mais **login SMS échoue** car la base auth résolue pointe vers **:8000**.

3. **Appareil physique / émulateur : mauvais hôte**  
   - `localhost` ou `127.0.0.1` sur l’appareil ≠ la machine qui héberge l’API.  
   - Il faut l’**IP LAN** de la machine et `--dart-define=API_BASE_URL=http://<IP>:3000` (auth dérivée → `<IP>:8000`), ou `AUTH_API_BASE_URL=http://<IP>:8000` explicite.

4. **Timeout 22 s**  
   - Réseau lent, pare-feu, ou serveur qui ne répond pas → **408** → même message.

5. **502/503 en amont** (reverse proxy, ECS, etc.)  
   - Réponse 5xx sans `detail.message` utile → même libellé.

6. **Réponse non JSON** (ex. HTML d’erreur) avec statut 200 théorique peu probable ; si statut d’erreur avec HTML, le code HTTP peut être 502/404 selon le cas — **502** ou décodage → encore ce libellé ou autre selon mapping.

---

## 4. Vérifications recommandées (rapides)

### 4.1 Sur la machine qui doit servir l’API

```bash
# Santé
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health

# Même test que le mobile (login SMS start — attendre 200 ou 4xx JSON métier, pas timeout)
curl -s -X POST http://127.0.0.1:8000/auth/login/sms/start \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+33612345678"}' | head -c 500
```

Si **curl ne se connecte pas** → cause n°1–3 ; corriger URL / démarrer uvicorn sur `0.0.0.0:8000` (voir runbooks existants).

### 4.2 Côté Flutter (build)

Vérifier les dart-defines réellement passés au build :

- `API_BASE_URL` (BFF)
- `AUTH_API_BASE_URL` si vous ne voulez **pas** la dérivation automatique `:8000` depuis le BFF.

### 4.3 Logs applicatifs

Les échecs réseau / HTTP sont journalisés dans **`AuthHttp`** (`dart:developer` / `logAuthHttpFailure` dans `lib/core/auth_http_logging.dart`) : **URI**, **méthode**, **status**, extraits de **payload** et **corps**. En debug, filtrer la console sur `AuthHttp` ou `auth_http`.

---

## 5. Problème produit / UX (lié au rapport utilisateur)

La refonte récente des messages a **regroupé** timeout, 5xx et nombre d’échecs transport « serveur injoignable » sous **une seule phrase**. C’est factuellement correct pour l’utilisateur final, mais **masque** la distinction entre :

- « Rien n’écoute sur le port 8000 » (config / dev),
- « Le serveur répond en erreur » (5xx),
- « Délai dépassé » (timeout).

**Recommandation** (hors scope correctif immédiat) : en **debug / dev**, afficher ou logger une sous-cause (code HTTP, `statusCode` Passkey, `operation` dans les logs) pour réduire le temps de diagnostic.

---

## 6. Synthèse

| Question | Réponse |
|----------|---------|
| Le message vient-il du backend ? | **Non** — libellé client ; le backend peut toutefois fournir un `detail` qui **remplace** ce texte si présent et parsé. |
| Pourquoi toujours « indisponible » ? | Plusieurs causes **réelles** différentes tombent dans le **même** libellé. |
| Cause la plus probable en dev | **FastAPI absente ou injoignable sur le port dérivé (8000)** alors que Next répond sur 3000. |
| Action prioritaire | Confirmer `curl` vers `{resolvedAuthApiBaseUrl}/health` depuis la même machine que le téléphone (ou IP LAN), puis `POST .../auth/login/sms/start`. |

---

*Document généré pour investigation du blocage « téléphone » — à jour avec `SecureApiConfig`, `PasskeyApi` et les routes `/auth/login/sms/start` / `/auth/signup/sms/start`.*
