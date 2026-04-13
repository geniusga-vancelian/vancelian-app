# Garde produit compte mobile ACTIVE vs PARTIAL — audit (2026)

## Objectif

Vérifier que les fonctionnalités **customer** appliquent une règle cohérente :

- **ACTIVE** (JWT : pas `sec_inc`, `acct_st` absent ou `ACTIVE`) requis quand l’action engage l’argent ou le portefeuille.
- **PARTIAL** : pas d’accès à ces actions côté app sans message clair ; alignement avec la **reprise d’inscription** (PIN → registration).
- **Sécurité réelle** : API + JWT + guards backend ; la colonne SQL `persons.account_state` n’est pas la vérité d’autorisation.

---

## 1. Cartographie des guards existants

### Backend (FastAPI)

| Zone | Mécanisme | Rôle |
|------|-----------|------|
| `services/test_clients/mobile_identity.py` | `_assert_mobile_app_security_complete` sur `/api/app/*` | Refuse si session **partielle** (`should_issue_partial_session_for_mobile_app`) + `NEEDS_SECURITY_SETUP_DETAIL` ; `ensure_pe_client_if_passcode_ack`. |
| Routes exchange / BFF | Dépendent du JWT + résolution client | Les appels sans identité **ACTIVE** échouent côté API si la route est protégée. |

### Flutter — vérité JWT

| Élément | Fichier | Rôle |
|---------|---------|------|
| `isAccessTokenAccountActiveForApp` | `mobile/lib/features/security/passcode/domain/jwt_access_claims.dart` | `sec_inc` → non actif ; `acct_st` ≠ `ACTIVE` → non actif ; JWT sans `acct_st` = legacy → actif si pas `sec_inc`. |
| `SessionService.isLastStoredAccessAccountActive()` | `session_service.dart` | Lecture du dernier access token stocké. |
| `SessionSecuritySnapshot` | `session_security_snapshot.dart` | Persistance `acct_st` / `sec_inc` pour contexte local. |

### Flutter — guards UI

| Guard | Fichier | Comportement |
|-------|---------|--------------|
| `TradingFlowSessionGuard.ensureSessionOrPrompt` | `wallet/presentation/trading_flow_session_guard.dart` | Session présente **+** `isLastStoredAccessAccountActive()` ; sinon SnackBar (connexion / finaliser inscription). |
| `CustomerAccountSessionGuard.ensureActiveAccountOrPrompt` | **même fichier** | Délègue à `TradingFlowSessionGuard` — nom explicite pour investissements / bundles / offres. |

### Appels actuels (recoupement code)

| Fichier | Usage |
|---------|--------|
| `buy_asset_modal_screen.dart`, `buy_flow_controller.dart`, `sell_flow_controller.dart` | `TradingFlowSessionGuard.ensureSessionOrPrompt` avant achat / vente. |
| `bundle_invest_flow_controller.dart` | `CustomerAccountSessionGuard` avant `start` / `startWithoutTarget` (**lot audit**). |
| `exclusive_offer_detail_screen.dart` | `CustomerAccountSessionGuard` avant ouverture `LendingInvestSourceScreen` (**lot audit**). |

---

## 2. Écrans / zones analysées

| Zone | Comportement PARTIAL | Commentaire |
|------|----------------------|---------------|
| **Home** | Accessible avec JWT PARTIAL (session + PIN) | Cohérent : tableau de bord marketing / navigation ; pas d’engagement financier direct. |
| **Profil / Mon compte** | Accessible | Lecture / paramètres ; API profil peut renvoyer 403 sur routes sensibles — géré par le client. |
| **Wallet (vue)** | Accessible | Données peuvent être incomplètes tant que PeClient / setup incomplet ; API garde-fous. |
| **Trading (achat/vente/swap)** | **Bloqué** | `TradingFlowSessionGuard`. |
| **Investissement bundle** | **Bloqué** sans ACTIVE | `BundleInvestFlowController` (**lot audit**). |
| **Offre exclusive — investir** | **Bloqué** sans ACTIVE | `_openInvestFlow` (**lot audit**). |
| **Dépôts / retraits / IBAN** | À traiter comme **sensible** | Pas de garde UI dédiée identifiée dans ce sweep ; à ajouter si des entrées utilisateur dédiées existent sans passer par `exchange` / `bundle` déjà gardés. |
| **Placements** | Détail placement : CTA Invest/Withdraw en **stub** (`onTap: () {}`) | Pas de trou fonctionnel actuel. |
| **Marchés / produits** | Navigation vers bundle invest via `BundleInvestFlowController` | Couvert par garde sur `start`. |

---

## 3. Trous identifiés (réduit après ce lot)

| Écart | Gravité | Statut |
|-------|---------|--------|
| Bundle invest sans `CustomerAccountSessionGuard` | Utilisateur PARTIAL pouvait ouvrir le flux avant erreurs API | **Corrigé** sur `BundleInvestFlowController.start` / `startWithoutTarget`. |
| Offre exclusive — investir sans guard | Idem | **Corrigé** sur `_openInvestFlow`. |
| Dépôts / virements dédiés | Inconnu si écran isolé | **À surveiller** lors de l’implémentation des boutons réels. |
| Message SnackBar « finaliser » | Formulation | Alignée sur : *« Finalisez votre inscription pour continuer. »* |

---

## 4. Corrections minimales (ce dépôt)

1. **`CustomerAccountSessionGuard`** : alias de `TradingFlowSessionGuard` pour documentation et usage investissement.
2. **`BundleInvestFlowController`** : garde avant navigation.
3. **`ExclusiveOfferDetailScreen._openInvestFlow`** : garde async avant `LendingInvestSourceScreen`.
4. **SnackBar** PARTIAL : texte unifié (voir ci-dessus).

---

## 5. Recommandations produit (hors scope obligatoire)

1. **Banner Home** (optionnel) : si `!isLastStoredAccessAccountActive()` et utilisateur sur shell, bandeau discret « Finalisez votre inscription » avec lien vers `RegistrationFlowScreen` — évite la confusion sans bloquer la navigation.
2. **Sweep** : tout nouvel écran « money movement » doit appeler `CustomerAccountSessionGuard` ou `TradingFlowSessionGuard` selon le cas.
3. **Tests** : ajouter un test widget ou intégration « PARTIAL → tap invest → SnackBar » si le pipeline le permet.

---

## 6. Synthèse

- **Backend** : `/api/app/*` et dérivés restent la **source de vérité** pour les sessions incomplètes.
- **Flutter** : **ACTIVE** requis pour **trading** + **investissement bundle** + **investissement offre exclusive** ; message utilisateur unique pour PARTIAL.
- **Pas de refactor** global des routes : extension par **points d’entrée** des flux sensibles.

---

*Document généré dans le cadre du durcissement PARTIAL / ACTIVE — aligné sur `MOBILE_AUTH_REGISTRATION_ROOTING_AUDIT_REPORT.md` §14.*
