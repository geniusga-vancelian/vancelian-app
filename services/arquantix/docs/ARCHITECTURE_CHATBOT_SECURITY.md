# Architecture: Chatbot Public Security

## Vue d'ensemble

Le chatbot public (`/api/chatbot/*`) utilise un système de sécurité basé sur **session_id uniquement**, sans authentification JWT. Ceci permet un accès public tout en maintenant une sécurité minimale.

## Sécurité

### 1. Session-based Access

- **Clé d'accès unique** : `session_id` (UUID)
- **Pas de JWT** : Aucun header `Authorization` requis
- **Expiration** : Sessions expirent après 24 heures (configurable via `SESSION_EXPIRY_HOURS`)

### 2. Rate Limiting

- **Limite** : 50 turns par session par heure (configurable via `RATE_LIMIT_TURNS_PER_HOUR`)
- **Window** : Fenêtre glissante de 1 heure
- **Erreur** : `429 Too Many Requests` si limite dépassée

### 3. Anonymisation (No PII)

- **IP Hash** : IP stockée comme SHA256 hash (`ip_hash`)
- **User Agent Hash** : User agent stocké comme SHA256 hash (`user_agent_hash`)
- **Pas de données personnelles** : Aucune PII stockée en clair

### 4. Validation des Sessions

Le guard `validate_session()` vérifie :
1. ✅ Session existe
2. ✅ Session non expirée (`expires_at > now`)
3. ✅ Rate limit OK (turns dans la dernière heure < limite)

## Endpoints Publics

Tous les endpoints `/api/chatbot/*` sont publics :

- `POST /api/chatbot/session` - Créer une session
- `GET /api/chatbot/session/{session_id}` - Obtenir les détails d'une session
- `POST /api/chatbot/conversation/turn` - Envoyer un message
- `GET /api/chatbot/profile?session_id=...` - Obtenir le profil

**Aucun header `Authorization` requis.**

## Endpoints Admin (JWT requis)

Les endpoints `/api/admin/*` conservent l'authentification JWT :

- `GET /api/admin/migrations/status` - État des migrations
- `POST /api/admin/migrations/apply/013` - Appliquer une migration
- Tous les autres endpoints admin

## Frontend

### Stockage de Session

Le frontend stocke `session_id` dans `localStorage` :

```typescript
const SESSION_STORAGE_KEY = 'chatbot_session_id'
localStorage.setItem(SESSION_STORAGE_KEY, session_id)
```

### Pas de Headers Authorization

Les appels API ne doivent **jamais** inclure de header `Authorization` pour le chatbot :

```typescript
// ✅ Correct
fetch('/api/chatbot/session', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({})
})

// ❌ Incorrect (ne pas faire)
fetch('/api/chatbot/session', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ...'  // ❌ Ne pas inclure
  },
  body: JSON.stringify({})
})
```

## Migration Base de Données

Migration `014_add_chatbot_session_security_fields` ajoute :

- `expires_at` (DateTime) - Date d'expiration de la session
- `ip_hash` (String(64)) - Hash SHA256 de l'IP
- `user_agent_hash` (String(64)) - Hash SHA256 du user agent
- Index sur `expires_at` pour les requêtes de nettoyage

## Configuration

Variables configurables dans `api/services/chatbot_epargne/security.py` :

- `RATE_LIMIT_TURNS_PER_HOUR = 50` - Limite de turns par heure
- `RATE_LIMIT_TURNS_WINDOW = timedelta(hours=1)` - Fenêtre de rate limit
- `SESSION_EXPIRY_HOURS = 24` - Durée de vie des sessions

## Tests

Les tests doivent fonctionner **sans JWT** :

```python
# ✅ Test correct
def test_create_session():
    response = client.post("/api/chatbot/session", json={})
    assert response.status_code == 200
    assert "session_id" in response.json()

# ❌ Ne pas utiliser JWT dans les tests chatbot
def test_create_session_with_jwt():
    token = create_jwt_token()  # ❌ Pas nécessaire
    response = client.post(
        "/api/chatbot/session",
        json={},
        headers={"Authorization": f"Bearer {token}"}  # ❌ Pas nécessaire
    )
```

## Sécurité vs Admin

| Aspect | Chatbot Public | Admin |
|--------|----------------|-------|
| Authentification | `session_id` uniquement | JWT Bearer token |
| Expiration | 24 heures | Selon JWT (24h par défaut) |
| Rate Limiting | 50 turns/heure | Pas de limite (admin) |
| PII | Hash uniquement | Email stocké |
| Endpoints | `/api/chatbot/*` | `/api/admin/*` |

## Notes d'Implémentation

1. **Backward Compatibility** : Les sessions existantes sans `expires_at` sont acceptées (vérification leniente)
2. **IP Matching** : Le matching IP est optionnel (pas strict) pour gérer les proxies/CDN
3. **Error Handling** : Les erreurs de session (expirée, non trouvée) retournent des codes HTTP appropriés
4. **Cleanup** : Un job de nettoyage peut supprimer les sessions expirées périodiquement
