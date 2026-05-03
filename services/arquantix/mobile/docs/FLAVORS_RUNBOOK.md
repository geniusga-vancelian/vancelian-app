# Runbook — flavors iOS / Android (dev, staging, prod)

**Réseau local (simulateur = `127.0.0.1:3000` / `:8000` ; iPhone = IP LAN ; deux URLs BFF vs auth)** : [LOCAL_IOS_AND_BFF.md](./LOCAL_IOS_AND_BFF.md).

## Correspondance des environnements

| Environnement | iOS (Xcode) | Bundle ID | Nom affiché | Android `--flavor` | `applicationId` |
|----------------|-------------|-----------|-------------|-------------------|-----------------|
| dev | **Debug** + schéma `dev` ou `Runner` | `com.vancelian.app.dev` | Vancelian Dev | `dev` | `com.vancelian.app.dev` |
| staging | **Profile** + schéma `staging` | `com.vancelian.app.staging` | Vancelian Staging | `staging` | `com.vancelian.app.staging` |
| prod | **Release** + schéma `prod` | `com.vancelian.app` | Vancelian | `prod` | `com.vancelian.app` |

`FLAVOR` est injecté en **dart-define** (base64 dans `DART_DEFINES`) via les fichiers `ios/Flutter/*-Flutter.xcconfig` pour les builds iOS. Sur Android, le défaut Dart est `dev` ; pour aligner `Config.flavor` sur le flavor Gradle, ajoutez `--dart-define=FLAVOR=staging` ou `FLAVOR=prod` (voir ci-dessous).

## Commandes — développement local (iPhone sur le Wi‑Fi)

1. Sur le Mac, lancez le BFF Next (port 3000) et l’API FastAPI (port 8000) en écoute sur `0.0.0.0` (pas seulement `127.0.0.1`).
2. Récupérez l’IP LAN du Mac : `ipconfig getifaddr en0` (ou l’interface Wi‑Fi active).
3. Depuis la racine `mobile/` :

```bash
flutter pub get
cd ios && pod install && cd ..
flutter run --flavor dev -d <id_iphone> \
  --dart-define=API_BASE_URL=http://<IP_LAN>:3000 \
  --dart-define=MARKET_DATA_BASE_URL=http://<IP_LAN>:8000
```

Simulateur iOS (`127.0.0.1:3000` BFF, `:8000` API — voir [LOCAL_IOS_AND_BFF.md](./LOCAL_IOS_AND_BFF.md)) :

```bash
flutter run --flavor dev -d iPhone
```

Les `dart-define` complètent ceux du xcconfig ; en cas de conflit sur une même clé, privilégiez une seule source (recommandé : variables CI ou script).

## Commandes — staging / prod

**Staging** (profil, proche prod) :

```bash
flutter run --profile --flavor staging -d <device> \
  --dart-define=FLAVOR=staging \
  --dart-define=API_BASE_URL=https://<hôte-staging> \
  --dart-define=MARKET_DATA_BASE_URL=https://<hôte-staging-api>
```

**Production** (release) :

```bash
flutter run --release --flavor prod -d <device> \
  --dart-define=FLAVOR=prod \
  --dart-define=API_BASE_URL=https://<hôte-prod> \
  --dart-define=MARKET_DATA_BASE_URL=https://<hôte-prod-api>
```

**Android** — toujours passer `--flavor` (`dev` | `staging` | `prod`) **et** `--dart-define=FLAVOR=...` pour que `Config.flavor` reflète l’APK installé.

## Builds CI / archive

- IPA staging : schéma `staging`, configuration **Profile**, ou `flutter build ipa --profile --flavor staging` (avec dart-defines d’URL).
- IPA / App Store prod : schéma `prod`, configuration **Release**, ou `flutter build ipa --release --flavor prod`.

Après modification des dépendances CocoaPods : `cd ios && pod install`.

## Fichiers clés

- Flutter : `lib/core/config.dart` (`API_BASE_URL`, `MARKET_DATA_BASE_URL`, `FLAVOR`, `marketDataBaseUrl`, WebSocket).
- iOS : `ios/Flutter/Debug-Flutter.xcconfig`, `Profile-Flutter.xcconfig`, `Release-Flutter.xcconfig`, `Profile.xcconfig`, `ios/Runner/Info.plist`.
- Schémas : `ios/Runner.xcodeproj/xcshareddata/xcschemes/{dev,staging,prod}.xcscheme`.
- Android : `android/app/build.gradle.kts`, `android/app/src/dev/AndroidManifest.xml` (HTTP LAN pour le flavor dev uniquement).
