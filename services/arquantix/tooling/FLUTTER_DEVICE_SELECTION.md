# Détection des devices iOS — Dev Toolkit

## Problème initial

- La logique s’appuyait sur `flutter devices --machine` et ne distinguait pas **USB / wireless**.
- Les appareils **wireless** sont souvent absents du JSON `--machine` ou y figurent sans champ `connectionInterface` fiable.
- En cas d’absence d’iPhone physique, le script **échouait** sans guider vers Xcode ou les réglages device.
- Un `DEVICE_ID` par défaut **codé en dur** pouvait masquer une sélection plus claire.

## Stratégie retenue

1. **Source principale** : `flutter devices --machine` (liste structurée, filtrage `targetPlatform == ios`, exclusion simulateurs via `emulator` + heuristiques sur `id` / `name`).
2. **Wireless** : lecture complémentaire de **`flutter devices`** (sortie texte) — les lignes contenant `wireless` et un UDID entre `•` sont indexées.
3. **Interface USB / Wi‑Fi** : optionnellement, **`xcrun xcdevice list`** (JSON Apple) pour `interface` = `usb` ou `wifi` sur `com.apple.platform.iphoneos`.
4. **Classification** : trois seaux — **iPhone USB**, **iPhone wireless**, **simulateur iOS**. Exclusion explicite de macOS, Chrome, web, etc.

## Algorithme de sélection

| Condition | Comportement |
|-----------|----------------|
| `SKIP_AUTO_DEVICE=1` | Utilise uniquement `DEVICE_ID` (sans vérifier Flutter). |
| `DEVICE_ID` exporté et présent dans la liste | Lancement direct sur cet UDID. |
| `DEVICE_ID` exporté mais **absent** | Menu interactif + message ; possibilité de choisir un autre device. |
| Aucun `DEVICE_ID` (ou vide), un seul iPhone physique | Sélection automatique. |
| Plusieurs iPhones physiques, `DEVICE_ID_DEFAULT` présent dans la liste | Préférence pour cet UDID (tie-break). |
| Plusieurs iPhones, `PREFER_WIRELESS=1` ou `PREFER_USB=1` | Premier device dans la catégorie choisie. |
| Aucun physique, un seul simulateur | Sélection automatique du simulateur. |
| Sinon | Menu numéroté (USB / wireless / simulateur) + **Ouvrir Xcode** + **Annuler**. |
| Aucun device utilisable | Sous-menu d’aide (Xcode, `flutter devices`, annuler). |

## Cas gérés

- iPhone **USB** seul, **wireless** seul, ou **les deux** (menu).
- **Simulateur** seul ou avec physiques (menu).
- **Aucun** device : assistance Xcode + rappels (câble, confiance, mode développeur, Devices and Simulators).

## Limites

- `flutter devices --machine` peut **ne pas** exposer tous les champs (ex. interface) : dépend de la version Flutter / Xcode.
- **Wireless** : détection renforcée par le **texte** `flutter devices` ; si Apple change le format des lignes, ajuster le parseur.
- **`xcrun xcdevice list`** peut être lent (~quelques secondes) ; en cas d’échec, le script retombe sur les heuristiques Flutter seules.
- Très gros JSON d’environnement : `_TK_MACHINE_JSON` est passé par variable d’environnement (limite rare de taille).

## Préférences optionnelles

- `PREFER_WIRELESS=1` — en cas d’ambiguïté entre plusieurs physiques, privilégier un iPhone wireless.
- `PREFER_USB=1` — idem pour USB.
- `DEVICE_ID_DEFAULT` — UDID utilisé comme **tie-break** quand plusieurs devices sont listés (pas un forçage silencieux si l’UDID n’est pas connecté).
