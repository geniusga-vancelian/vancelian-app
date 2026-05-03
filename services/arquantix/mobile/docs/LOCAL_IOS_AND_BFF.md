# iOS local — simulateur, iPhone, BFF et API

Doc courte. Ports officiels : **Next (BFF) 3000**, **FastAPI 8000** (aligné Lot 1).

---

## Modèle officiel

| Cible | BFF (`API_BASE_URL`) | Auth / API sécurisée (`AUTH_API_BASE_URL`) |
|--------|----------------------|-------------------------------------------|
| **Simulateur iOS** | `http://127.0.0.1:3000` | `http://127.0.0.1:8000` |
| **iPhone physique** | `http://<IP_LAN_DU_MAC>:3000` | `http://<IP_LAN_DU_MAC>:8000` |

Sur un **iPhone réel**, ne jamais utiliser `localhost` ni `127.0.0.1` pour joindre le Mac : ces adresses désignent **le téléphone lui-même**.

Le Mac et l’iPhone doivent être sur le **même réseau** (Wi‑Fi typiquement), sauf configuration avancée (tunnel USB, etc.).

---

## Rôle des deux URLs

| Variable | Pointe vers | Rôle |
|----------|-------------|------|
| **`API_BASE_URL`** | **Next.js** (port **3000**) | BFF : routes `/api/mobile/flutter/*`, CMS proxy, bootstrap, etc. |
| **`AUTH_API_BASE_URL`** | **FastAPI** (port **8000**) | Auth (OTP, passkeys, refresh, endpoints sécurisés côté Python). |

Pourquoi deux URLs : le mobile parle au **BFF** pour la plupart des flux produit, et à **FastAPI** pour l’auth et les API qui ne passent pas par Next.

En dev local, **même hôte**, **ports différents** (3000 vs 8000). Les scripts dérivent `AUTH_*` depuis `API_*` en remplaçant le port si vous ne définissez que `API_BASE_URL`.

**À éviter** : même port pour les deux ; pointer les deux vers un seul service en oubliant l’autre ; `localhost` sur iPhone physique.

---

## Commandes minimales

**Stack locale (Docker)** — racine du dépôt :

```bash
make -f Makefile.arquantix arquantix-up   # ou make setup
```

**Simulateur iOS** (`services/arquantix/mobile`) :

```bash
./run-ios.sh
```

**iPhone physique** (IP LAN détectée automatiquement si possible) :

```bash
./run-ios-device.sh
```

Forcer l’IP (ex. Wi‑Fi partagé ou plusieurs interfaces) :

```bash
export API_BASE_URL=http://192.168.1.42:3000
export AUTH_API_BASE_URL=http://192.168.1.42:8000
./run-ios-device.sh
```

---

## Checklist diagnostic (réseau simple)

1. **IP du Mac** : `ipconfig getifaddr en0` (ou `en1`). C’est l’hôte à utiliser depuis l’iPhone.
2. **Next** : `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000` → `200` (ou 30x) depuis le Mac.
3. **API** : `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health` → `200`.
4. **Depuis l’iPhone (Safari)** : ouvrir `http://<IP_LAN>:3000` — si ça ne charge pas, Flutter ne pourra pas non plus (pare-feu / réseau / mauvaise IP).
5. **Pas de localhost sur iPhone** : si les `--dart-define` contiennent `127.0.0.1` ou `localhost`, c’est incorrect pour un appareil physique.

Alignement DB / Prisma (API OK ≠ web OK) : voir `docs/arquantix/LOCAL_DB_ALIGNMENT.md` et `make -f Makefile.arquantix local-db-doctor`.

---

## Erreurs fréquentes

| Symptôme | Cause probable |
|----------|----------------|
| Timeout / connection refused sur iPhone | `localhost` ou mauvaise IP ; Mac et iPhone pas sur le même LAN ; pare-feu macOS bloquant 3000/8000. |
| OK sur simulateur, KO sur iPhone | Normal si vous utilisiez `127.0.0.1` : passer à `http://<IP_LAN>:3000` et `:8000`. |
| 404 sur le blog mais le reste marche | Next pas démarré ou mauvaise URL BFF (vérifier port **3000**). |

---

## Automatisé vs manuel

- **Scripts** : ports 3000/8000, garde-fou localhost sur `run-ios-device.sh`, suggestion d’IP dans les messages d’erreur.
- **Manuel** : choix de l’interface réseau, pare-feu, confiance USB/Xcode, alignement avec une stack non standard.

Limite : la détection d’IP via `en0`/`en1` peut être fausse si le Mac utilise une autre interface ; dans ce cas, export explicite de `API_BASE_URL` / `AUTH_API_BASE_URL`.
