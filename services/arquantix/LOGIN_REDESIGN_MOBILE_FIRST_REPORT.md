# Refonte login mobile — rapport (mobile-first, alignement DS registration)

## Executive summary

Le flux de connexion a été restructuré en **parcours mobile-first** (téléphone en premier, e-mail et passkey en secondaire), avec **réutilisation du Design System** déjà employé sur l’inscription (`AppPhoneInput`, `AppTextInput`, `AppPrimaryButton`, `AppTopNavBar`, `AppPageTitle`, `AppOtpInput`, marges `AppSpacing.pageEdge`). Les appels réseau restent ceux de **`PasskeyApi`** (passkey + OTP e-mail admin) et **`PasskeyLoginCoordinator`** / **`SessionService`** — aucune couche auth parallèle.

**Limite produit actuelle (documentée)** : il n’existe pas encore d’endpoint de **connexion par OTP SMS** sur le seul numéro (les `admin_users` n’ont pas de champ téléphone). L’étape téléphone sert à **cadrer l’UX**, mémoriser l’E.164 pour le confort, puis **enchaîne vers l’e-mail** pour OTP / passkey. Une évolution backend dédiée supprimera cette étape de pont.

---

## 1. Audit de l’existant (avant)

| Élément | Constat |
|--------|---------|
| **Écran principal** | `ApiSessionLoginScreen` : e-mail en premier, texte long, `TextField` / `FilledButton` Material bruts, libellés en anglais (“Continue with Passkey”). |
| **OTP** | `AdminEmailOtpLoginScreen` : même écart DS, pas de `AppOtpInput`, pas de timer resend unifié, flux manuel “Envoyer le code”. |
| **Registration** | `RegistrationFlowScreen` + `AppPhoneInput`, `AppPageTitle`, typo Inter, `AppSpacing.pageEdge`, bottom CTA — **référence visuelle**. |
| **Friction UX** | Passkey présentée comme action principale du premier écran ; pas d’entrée “hub” claire ; pas de hiérarchie téléphone → e-mail. |

---

## 2. Écarts DS (corrigés dans la refonte)

- Remplacement des champs Material génériques par **`AppTextInput`** / **`AppPhoneInput`**.
- Boutons **`AppPrimaryButton`** (tailles `large` / `medium`, variantes primary / secondary / ghost).
- Barres **`AppTopNavBar`** (mode dashboard / retour).
- Titres **`AppPageTitle`** + sous-titres Inter 15px / `AppColors.textSecondary` comme en registration.
- OTP : **`AppOtpInput`** (6 cases, auto-soumission, états erreur / verrouillage).
- Fond **`AppColors.pageBackground`**.

---

## 3. Nouvelle architecture (fichiers)

| Fichier | Rôle |
|---------|------|
| `lib/features/auth/presentation/screens/welcome_landing_screen.dart` | **Login0** (fond héro) : **Me connecter** → téléphone ; **Créer un compte** → registration (plus d’écran « Bienvenue » séparé). |
| `login_phone_screen.dart` | Mobile + pays, CTA **Continuer**, lien **Autres options** (sheet). |
| `login_method_sheet.dart` | Bottom sheet : e-mail, passkey, “plus d’accès au numéro”. |
| `login_email_screen.dart` | E-mail, CTA principal **code e-mail**, secondaire **passkey**, bannière si numéro issu de l’étape précédente. |
| `login_otp_screen.dart` | Envoi auto au montage, `AppOtpInput`, renvoi + compte à rebours. |
| `api_session_login_screen.dart` | **Wrapper** vers `LoginPhoneScreen` (connexion directe depuis profil, etc.). |

**Navigation / résultat `bool`** : succès remonte `pop(true)` (e-mail → téléphone → **Login0** / welcome) puis `pushReplacement` vers `MainShellScreen`.

---

## 4. Composants réutilisés (liste)

- `AppTopNavBar`, `AppPageTitle`, `AppPrimaryButton`, `AppPhoneInput`, `AppTextInput`, `AppOtpInput`, `SheetTitleBar` / `SheetCircleButton`, `AppSpacing`, `AppColors`, `GoogleFonts.inter` (sous-titres comme registration).

---

## 5. Hiérarchie des méthodes (implémentée)

1. **Principal** : numéro mobile (écran dédié, CTA principal).  
2. **Secondaire** : e-mail (écran suivant ou sheet).  
3. **Premium / avancé** : passkey (bouton secondaire sur l’écran e-mail, ou sheet).  
4. **Récupération** : “Je n’ai plus accès à mon numéro” → écran e-mail en mode récupération.  
5. **Apple / Google** : non implémentés (placeholder dans ce rapport pour itération ultérieure).

---

## 6. Utilisateur récurrent (“Heureux de vous revoir”)

- **`SessionService.rememberLoginIdentifiers`** : stocke le dernier e-mail et le dernier mobile (E.164) après succès (OTP ou passkey).  
- **`readLastLoginEmail`** : titre / préremplissage sur `LoginPhoneScreen` et `LoginEmailScreen`.  
- **Passkey** : option `openPasskeyOnAppear` (sheet) pour tenter la passkey une fois si l’e-mail est déjà valide.

---

## 7. Intégration sécurité (inchangée côté API)

- `PasskeyApi.adminEmailOtpStart` / `adminEmailOtpVerify`  
- `PasskeyLoginCoordinator.signInWithPasskey`  
- `DeviceIdService` (en-têtes device / empreinte)  
- `SessionService.storeTokens`  

`AdminEmailOtpLoginScreen` reste dans le repo mais **n’est plus référencée** ; logique OTP portée par `LoginOtpScreen`.

---

## 8. Copywriting

- Formulations en français, ton **fintech / rassurant**, moins techniques.  
- Anti-énumération conservée sur le message OTP (aligné backend).

---

## 9. Tests

- `test/features/security/login/login_flow_navigation_test.dart` : entrée (2 CTA), téléphone (`hydrateLastSession: false` pour tests), sheet méthodes.  
- `LoginPhoneScreen` / `LoginEmailScreen` : paramètre **`hydrateLastSession`** pour éviter `FlutterSecureStorage` + indicateurs indéterminés dans les tests widget.

**À ajouter plus tard** : tests d’intégration avec mock HTTP pour OTP / passkey ; tests d’états loading sur `LoginOtpScreen`.

---

## 10. Captures / validation manuelle (checklist)

- [ ] Welcome → Me connecter → Hub → Téléphone → E-mail → OTP (e-mail reçu en environnement configuré).  
- [ ] Passkey secondaire : échec → snackbar, possibilité de repasser par le code.  
- [ ] Sheet : e-mail / passkey / perte de numéro.  
- [ ] Retour arrière cohérent à chaque étape.  
- [ ] Profil → Connexion compte → [LoginPhoneScreen] (sans écran intermédiaire).

---

## 11. Lacunes & prochaine itération

| Sujet | Action recommandée |
|--------|-------------------|
| **OTP SMS login sans e-mail** | Endpoints dédiés + modèle (ex. téléphone sur compte admin ou table identité) + réutilisation `TwoFactorService` avec purpose `login`. |
| **Apple / Google** | OAuth / Sign in with Apple, derrière feature flag. |
| **Validation téléphone** | Réutiliser les mêmes règles que `registration_phone_format_validation` côté client. |
| **AdminEmailOtpLoginScreen** | Supprimer ou marquer `@Deprecated` après gel de la refonte. |
| **Internationalisation** | Extraire les chaînes en ARB si l’app i18n est activée sur ces flux. |

---

*Document généré dans le cadre de la refonte login mobile Arquantix.*
