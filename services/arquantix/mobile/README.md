# Arquantix News — Application Flutter

Application mobile Flutter affichant les articles de news du blog Arquantix.

**Dev iOS local (simulateur vs iPhone, BFF :3000, API :8000)** : voir **[docs/LOCAL_IOS_AND_BFF.md](docs/LOCAL_IOS_AND_BFF.md)**.

## Prérequis

- [Flutter](https://flutter.dev/docs/get-started/install) (SDK >= 3.2.0)
- Le serveur Next.js Arquantix doit être démarré (pour l’API blog)

## Installation

```bash
cd services/arquantix/mobile
flutter pub get
```

## Configuration de l’API

Par défaut, l’app appelle `http://localhost:3000`. Pour un émulateur Android, utilisez `10.0.2.2` à la place de `localhost` :

```bash
# Émulateur Android
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:3000

# iOS Simulator (localhost fonctionne)
flutter run

# Production
flutter run --dart-define=API_BASE_URL=https://votre-domaine.com
```

## Génération du projet (première fois)

Si le dossier `mobile` a été créé manuellement, exécutez une fois :

```bash
cd services/arquantix/mobile
flutter create . --project-name arquantix_news
```

Cela ajoutera les dossiers `android/`, `ios/`, etc.

## Lancement

### Raccourcis (aliases dans ~/.zshrc — à utiliser depuis n’importe quel dossier)

| Commande   | Action |
|-----------|--------|
| **`arq`** | Lance l’émulateur (si besoin) + l’app Flutter sur Android |
| **`arq-emu`** | Démarre uniquement l’émulateur Android |
| **`arq-chrome`** | Lance l’app dans Chrome (web) |
| **`arq-app`** | Lance l'app sur l'émulateur Android (émulateur déjà démarré) |
| **`arq-ios`** | Lance l'app sur le simulateur iOS (nécessite Xcode) | Lance l’app sur l’émulateur (émulateur déjà démarré) |

Après ajout des aliases, exécuter `source ~/.zshrc` ou rouvrir le terminal.

### Depuis le dossier mobile

```bash
cd services/arquantix/mobile

# Tout-en-un (émulateur + app)
./go.sh

# iOS — simulateur (BFF 127.0.0.1:3000, API :8000 par défaut)
./run-ios.sh

# iOS — iPhone physique (IP LAN automatique ou API_BASE_URL / AUTH_API_BASE_URL)
./run-ios-device.sh

# Android — avec variable d’environnement
API_BASE_URL=http://10.0.2.2:3000 ./run-android.sh

# Chrome
./run.sh -d chrome
```

## Structure

- `lib/main.dart` — Point d’entrée
- `lib/config.dart` — URL de l’API
- `lib/models/` — Modèles Article, ArticleDetail, etc.
- `lib/services/blog_api.dart` — Client HTTP pour l’API blog
- `lib/screens/` — Écrans liste et détail des articles

## API utilisée

- `GET /api/blog` — Feed (featured, highlighted, articles, categories, pagination)
- `GET /api/blog/[slug]?locale=fr` — Détail d’un article
