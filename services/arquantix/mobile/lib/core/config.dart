import 'dart:io';

/// Configuration de l'application
class Config {
  /// Environnement cible : `dev` | `staging` | `prod`.
  /// - iOS : injecté via `DART_DEFINES` dans les xcconfig (`Debug-Flutter`, `Profile-Flutter`, `Release-Flutter`).
  /// - Android : passer explicitement `--dart-define=FLAVOR=staging` (ou `dev` / `prod`) avec `--flavor`.
  static const String flavor = String.fromEnvironment(
    'FLAVOR',
    defaultValue: 'dev',
  );

  static const String _apiBaseUrlEnv = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:3000',
  );

  /// Base URL du **serveur Next.js** qui expose `/api/mobile/flutter/*` (BFF mobile).
  /// Ce n’est pas l’API Python seule : vaults, widgets, bootstrap, etc. passent par Next.
  /// Défaut dev : port 3000. Émulateur Android : `--dart-define=API_BASE_URL=http://10.0.2.2:3000`.
  /// Appareil physique : IP LAN de la machine (ex. http://192.168.1.10:3000).
  /// iOS simulateur : localhost → 127.0.0.1 automatiquement si vous gardez le défaut.
  static String get apiBaseUrl {
    if (Platform.isIOS && _apiBaseUrlEnv == 'http://localhost:3000') {
      return 'http://127.0.0.1:3000';
    }
    return _apiBaseUrlEnv;
  }

  static String get cashUrl => '$apiBaseUrl/api/mobile/flutter/cash';

  static String get euroAccountUrl => '$apiBaseUrl/api/mobile/flutter/euro-account';

  /// Relevé IBAN PDF (proxy Next → API Python `GET /api/app/euro-account/statement.pdf`).
  static String get euroAccountStatementPdfUrl =>
      '$apiBaseUrl/api/mobile/flutter/euro-account/statement.pdf';

  static String get ibanDetailsUrl => '$apiBaseUrl/api/mobile/flutter/iban-details';

  static String get cryptoPositionsUrl => '$apiBaseUrl/api/mobile/flutter/crypto-positions';

  static String get directCryptoPositionsUrl => '$apiBaseUrl/api/mobile/flutter/crypto-positions/direct';

  static String cryptoWalletDetailUrl(String asset) =>
      '$apiBaseUrl/api/mobile/flutter/crypto-positions/$asset';

  static String cryptoTransactionsUrl(String asset) =>
      '$apiBaseUrl/api/mobile/flutter/crypto-positions/$asset/transactions';

  static String transactionDetailUrl(String id) =>
      '$apiBaseUrl/api/mobile/flutter/transactions/$id';

  /// Relevé PDF d’une seule opération (`GET .../operation-statement.pdf`).
  static String transactionOperationStatementPdfUrl(String transactionId) =>
      '$apiBaseUrl/api/mobile/flutter/transactions/$transactionId/operation-statement.pdf';

  static String get bootstrapUrl => '$apiBaseUrl/api/mobile/flutter/bootstrap';

  /// Config écran welcome (URL image héro depuis R2 / CDN via le BFF Next).
  static String get welcomeConfigUrl => '$apiBaseUrl/api/mobile/flutter/welcome';

  /// URL directe du visuel welcome (sans BFF). Build :
  /// `--dart-define=WELCOME_HERO_DIRECT_URL=https://…/hero.png`
  static const String _welcomeHeroDirectUrl = String.fromEnvironment(
    'WELCOME_HERO_DIRECT_URL',
    defaultValue: '',
  );

  static String? get welcomeHeroDirectUrl {
    final s = _welcomeHeroDirectUrl.trim();
    return s.isEmpty ? null : s;
  }

  /// URL arrière-plan Login0 (surcharge build). Si vide, voir [kLogin0DefaultHeroImageUrl].
  static const String _login0HeroBackgroundUrl = String.fromEnvironment(
    'LOGIN0_HERO_BACKGROUND_URL',
    defaultValue: '',
  );

  static String? get login0HeroBackgroundUrl {
    final s = _login0HeroBackgroundUrl.trim();
    return s.isEmpty ? null : s;
  }

  /// Fond Login0 par défaut (image) — repli si la vidéo ne charge pas.
  /// Si le bucket est privé, passer une URL signée ou publique via
  /// [login0HeroBackgroundUrl] ou `WELCOME_HERO_DIRECT_URL`.
  static const String kLogin0DefaultHeroImageUrl =
      'https://arquantix-media.c5bf9aa04c0f3a5c13ba03e78ac187d0.r2.cloudflarestorage.com/media/1775206317914-mtsym61mcto.png';

  /// Vidéo Login0 par défaut (après splash, utilisateur non connecté) — `1775486404852-dnxu9hiheeo.mp4`.
  /// Priorité : `--dart-define=LOGIN0_HERO_VIDEO_URL` → BFF `heroVideoUrl` → cette URL.
  /// Si l’accès direct échoue (bucket privé), configurer le BFF ou `LOGIN0_HERO_VIDEO_URL` (URL signée).
  static const String kLogin0DefaultHeroVideoUrl =
      'https://arquantix-media.c5bf9aa04c0f3a5c13ba03e78ac187d0.r2.cloudflarestorage.com/media/1775486404852-dnxu9hiheeo.mp4';

  /// Illustration hero header activation (dashboard avant premier dépôt), média R2.
  /// Surcharge : `--dart-define=ACTIVATION_HEADER_HERO_URL=https://…` (ex. URL signée si bucket privé).
  static const String kActivationHeaderHeroMediaUrl =
      'https://arquantix-media.c5bf9aa04c0f3a5c13ba03e78ac187d0.r2.cloudflarestorage.com/media/1775573342872-8mhm6xmm30m.png';

  static const String _activationHeaderHeroUrlOverride = String.fromEnvironment(
    'ACTIVATION_HEADER_HERO_URL',
    defaultValue: '',
  );

  /// BFF Next : dernière image média admin (GET JSON `{ imageUrl }`).
  static String get activationHeroLatestMediaUrl =>
      '$apiBaseUrl/api/mobile/flutter/activation-hero-image';

  /// URL effective pour l'image au-dessus du dégradé (activation home).
  static String get activationHeaderHeroUrl {
    final o = _activationHeaderHeroUrlOverride.trim();
    return o.isNotEmpty ? o : kActivationHeaderHeroMediaUrl;
  }


  /// Vidéo de fond Login0 à la place de l’image — tests / builds :
  /// `--dart-define=LOGIN0_USE_HERO_VIDEO=true`
  /// `--dart-define=LOGIN0_HERO_VIDEO_ASSET=assets/videos/login0.mp4` (optionnel)
  /// `--dart-define=LOGIN0_HERO_VIDEO_URL=https://…/hero.mp4` (optionnel, priorité asset si les deux)
  static const bool login0UseHeroVideo = bool.fromEnvironment(
    'LOGIN0_USE_HERO_VIDEO',
    defaultValue: false,
  );

  static const String _login0HeroVideoAsset = String.fromEnvironment(
    'LOGIN0_HERO_VIDEO_ASSET',
    defaultValue: '',
  );

  /// Chemin asset pubspec (ex. `assets/videos/login0.mp4`).
  static String? get login0HeroVideoAssetPath {
    final s = _login0HeroVideoAsset.trim();
    return s.isEmpty ? null : s;
  }

  static const String _login0HeroVideoUrl = String.fromEnvironment(
    'LOGIN0_HERO_VIDEO_URL',
    defaultValue: '',
  );

  /// URL HTTPS de la vidéo hero si pas d’asset.
  static String? get login0HeroVideoUrl {
    final s = _login0HeroVideoUrl.trim();
    return s.isEmpty ? null : s;
  }

  /// Profil Mon compte (PII agrégé depuis person.profile_json, même client que bootstrap).
  static String get mobileAppProfileUrl => '$apiBaseUrl/api/mobile/flutter/profile';

  /// Préférences ``profile_json.security`` (biométrie, notifications).
  static String get mobileSecurityPreferencesUrl =>
      '$apiBaseUrl/api/mobile/flutter/profile/security-preferences';

  static String get referenceCurrencyUrl =>
      '$apiBaseUrl/api/mobile/flutter/profile/reference-currency';

  static String walletHistoryUrl(
    String period, {
    String? asset,
    String? mode,
    String? scope,
    String? portfolioScope,
    String? portfolioId,
  }) {
    final buf = StringBuffer('$apiBaseUrl/api/mobile/flutter/wallet/history?period=${Uri.encodeComponent(period)}');
    if (asset != null && asset.isNotEmpty) {
      buf.write('&asset=${Uri.encodeComponent(asset)}');
    }
    if (mode != null && mode.isNotEmpty) {
      buf.write('&mode=${Uri.encodeComponent(mode)}');
    }
    if (scope != null && scope.isNotEmpty) {
      buf.write('&scope=${Uri.encodeComponent(scope)}');
    }
    if (portfolioScope != null && portfolioScope.isNotEmpty) {
      buf.write('&portfolio_scope=${Uri.encodeComponent(portfolioScope)}');
    }
    if (portfolioId != null && portfolioId.isNotEmpty) {
      buf.write('&portfolio_id=${Uri.encodeComponent(portfolioId)}');
    }
    return buf.toString();
  }

  static String get exchangeBuyPreviewUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/buy/preview';

  static String get exchangeBuyUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/buy';

  static String get exchangeSellPreviewUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/sell/preview';

  static String get exchangeSellUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/sell';

  static String get exchangeSwapPreviewUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/swap/preview';

  static String get exchangeSwapUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/swap';

  static String get exchangeSellAllPreviewUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/sell-all/preview';

  static String get exchangeSellAllUrl =>
      '$apiBaseUrl/api/mobile/flutter/exchange/sell-all';

  static String get bundleCatalogUrl =>
      '$apiBaseUrl/api/mobile/flutter/bundle/catalog';

  static String get bundleInvestUrl =>
      '$apiBaseUrl/api/mobile/flutter/bundle/invest';

  static String get bundleInvestPreviewUrl =>
      '$apiBaseUrl/api/mobile/flutter/bundle/invest/preview';

  static String bundleStatusUrl(String portfolioId) =>
      '$apiBaseUrl/api/mobile/flutter/bundle/$portfolioId/status';

  static String get myBundlesUrl =>
      '$apiBaseUrl/api/mobile/flutter/bundle/my-bundles';

  static String walletStatisticsUrl(
    String asset, {
    String? portfolioScope,
    String? portfolioId,
  }) {
    final buf = StringBuffer(
      '$apiBaseUrl/api/mobile/flutter/wallet/statistics/${Uri.encodeComponent(asset)}',
    );
    final params = <String>[];
    if (portfolioScope != null && portfolioScope.isNotEmpty) {
      params.add('portfolio_scope=${Uri.encodeComponent(portfolioScope)}');
    }
    if (portfolioId != null && portfolioId.isNotEmpty) {
      params.add('portfolio_id=${Uri.encodeComponent(portfolioId)}');
    }
    if (params.isNotEmpty) {
      buf.write('?${params.join('&')}');
    }
    return buf.toString();
  }

  static String bundleHistoryUrl(String portfolioId, String period, {String? asset, String? mode}) {
    final buf = StringBuffer(
      '$apiBaseUrl/api/mobile/flutter/bundle/$portfolioId/history?period=${Uri.encodeComponent(period)}',
    );
    if (asset != null && asset.isNotEmpty) {
      buf.write('&asset=${Uri.encodeComponent(asset)}');
    }
    if (mode != null && mode.isNotEmpty) {
      buf.write('&mode=${Uri.encodeComponent(mode)}');
    }
    return buf.toString();
  }

  static String bundleStatisticsUrl(String portfolioId) =>
      '$apiBaseUrl/api/mobile/flutter/bundle/$portfolioId/statistics';

  static String bundleTransactionsUrl(String portfolioId) =>
      '$apiBaseUrl/api/mobile/flutter/bundle/$portfolioId/transactions';

  static String bundleRebalancePreviewUrl(String portfolioId) =>
      '$apiBaseUrl/api/mobile/flutter/bundle/$portfolioId/rebalance/preview';

  static String bundleRebalanceExecuteUrl(String portfolioId) =>
      '$apiBaseUrl/api/mobile/flutter/bundle/$portfolioId/rebalance';

  // ---- Lending / Placements ----
  static String get lendingEarnPositionsUrl =>
      '$apiBaseUrl/api/mobile/flutter/lending/earn/positions';

  static String get lendingDashboardUrl =>
      '$apiBaseUrl/api/mobile/flutter/lending/dashboard';

  static String lendingInvestPreviewUrl(String productId) =>
      '$apiBaseUrl/api/mobile/flutter/lending/products/$productId/invest/preview';

  static String lendingInvestUrl(String productId) =>
      '$apiBaseUrl/api/mobile/flutter/lending/products/$productId/invest';

  static String get portfolioStatisticsUrl =>
      '$apiBaseUrl/api/mobile/flutter/portfolio/statistics';

  static String get globalStatisticsUrl =>
      '$apiBaseUrl/api/mobile/flutter/portfolio/global/statistics';

  static String globalHistoryUrl(String period) =>
      '$apiBaseUrl/api/mobile/flutter/portfolio/global/history?period=$period';

  // ---- Price Alerts ----
  static String get alertsUrl => '$apiBaseUrl/api/mobile/flutter/alerts';
  static String alertDeleteUrl(String alertId) =>
      '$apiBaseUrl/api/mobile/flutter/alerts/$alertId';

  // ---- Favorites ----
  static String get favoritesUrl => '$apiBaseUrl/api/mobile/flutter/favorites';
  static String favoriteDeleteUrl(String favoriteId) =>
      '$apiBaseUrl/api/mobile/flutter/favorites/$favoriteId';

  // ---- Trigger Orders ----
  static String get ordersUrl => '$apiBaseUrl/api/mobile/flutter/orders';
  static String orderDeleteUrl(String orderId) =>
      '$apiBaseUrl/api/mobile/flutter/orders/$orderId';

  // ---- Notifications ----
  static String get notificationsUrl =>
      '$apiBaseUrl/api/mobile/flutter/notifications';
  static String get notificationsUnreadCountUrl =>
      '$apiBaseUrl/api/mobile/flutter/notifications/unread-count';
  static String notificationReadUrl(String notificationId) =>
      '$apiBaseUrl/api/mobile/flutter/notifications/$notificationId/read';
  static String get notificationsReadAllUrl =>
      '$apiBaseUrl/api/mobile/flutter/notifications/read-all';

  static String get blogFeedUrl => '$apiBaseUrl/api/blog';
  static String blogArticleUrl(String slug) => '$apiBaseUrl/api/blog/$slug';

  /// Liste des projets publiés (offres exclusives).
  static String get projectsUrl => '$apiBaseUrl/api/projects';

  /// Catalogue unifié (Product Registry) — liste produits packagés.
  static String get catalogProductsUrl => '$apiBaseUrl/api/mobile/flutter/catalog/products';

  /// Détail catalogue par slug packagé (registry).
  static String catalogProductDetailUrl(String slug) {
    final s = slug.trim();
    return '$apiBaseUrl/api/mobile/flutter/catalog/products/${Uri.encodeComponent(s)}';
  }

  /// Phase 7–8 : source **canonique** des Exclusive Offers = [catalogProductsUrl].
  /// `false` force encore [projectsUrl] (legacy / rollback).
  /// `--dart-define=USE_CATALOG_FOR_EXCLUSIVE_OFFERS=false`
  static const bool useCatalogForExclusiveOffers = bool.fromEnvironment(
    'USE_CATALOG_FOR_EXCLUSIVE_OFFERS',
    defaultValue: true,
  );

  /// Filtre registre pour la liste (GET [catalogProductsUrl]) — aligné backend
  /// (`commercialStatus` : draft | published | archived). Vide = défaut serveur (**published**).
  ///
  /// Phase 8Bis : les EO créées depuis Vault Builder sont **draft** jusqu’à publication dans
  /// l’admin. Pour les voir dans l’app en QA : `--dart-define=CATALOG_LIST_COMMERCIAL_STATUS=draft`
  static const String catalogListCommercialStatus = String.fromEnvironment(
    'CATALOG_LIST_COMMERCIAL_STATUS',
    defaultValue: '',
  );

  /// Filtre visibilité catalogue (public | private | hidden). Vide = défaut serveur (**public**).
  static const String catalogListVisibility = String.fromEnvironment(
    'CATALOG_LIST_VISIBILITY',
    defaultValue: '',
  );

  /// Repli **transitoire** (Phase 8) : si le catalogue échoue, liste via GET /api/projects.
  /// Pour couper le repli une fois la prod stable : `false` + valider hors ligne creuse.
  /// `--dart-define=FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE=false`
  static const bool fallbackLegacyProjectsOnCatalogFailure = bool.fromEnvironment(
    'FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE',
    defaultValue: true,
  );

  /// Layout Dashboard stocké en base (Design System).
  static String get dashboardLayoutUrl =>
      flutterLayoutUrl('dashboard');

  /// Layout page Offers stocké en base (Design System).
  static String get offersLayoutUrl =>
      flutterLayoutUrl('offers');

  /// Layout All transactions stocke en base (Design System).
  static String get allTransactionsLayoutUrl =>
      flutterLayoutUrl('all-transactions');

  /// Layout Transaction detail stocke en base (Design System).
  static String get transactionDetailLayoutUrl =>
      flutterLayoutUrl('transaction-detail');

  /// Layout page projet (offre exclusive) stocke en base (Design System).
  static String get exclusiveOfferDetailLayoutUrl =>
      flutterLayoutUrl('exclusive-offer-detail');

  /// Layout Compte Euro stocke en base (Design System).
  static String get euroAccountLayoutUrl =>
      flutterLayoutUrl('euro-account');

  /// URL générique des layouts Flutter DS via slug.
  static String flutterLayoutUrl(String slug) {
    final normalized = slug.trim();
    return '$apiBaseUrl/api/mobile/flutter/layouts/$normalized';
  }

  /// Runtime landing page Flutter via slug (builder admin).
  static String flutterLandingPageUrl(String slug) {
    final normalized = slug.trim();
    return '$apiBaseUrl/api/mobile/flutter/landing-pages/$normalized';
  }

  /// Runtime widget Flutter (Widget Builder) via slug.
  static String flutterWidgetUrl(String slug) {
    final normalized = slug.trim();
    return '$apiBaseUrl/api/mobile/flutter/widgets/$normalized';
  }

  /// Liste des vaults (Vault Builder).
  static String get vaultsUrl => '$apiBaseUrl/api/mobile/flutter/vaults';

  /// Détail d'un vault Flutter via slug.
  static String vaultUrl(String slug) {
    final normalized = slug.trim();
    return '$apiBaseUrl/api/mobile/flutter/vaults/$normalized';
  }

  /// Config d'un produit Portfolio Engine (modules du builder).
  static String portfolioProductUrl(String productCode) {
    final normalized = productCode.trim();
    return '$apiBaseUrl/api/mobile/flutter/portfolio-products/$normalized';
  }

  /// Chart history pondéré d'un produit bundle (performance composite).
  static String portfolioProductChartUrl(String productCode, String period) {
    final normalized = productCode.trim();
    return '$apiBaseUrl/api/mobile/flutter/portfolio-products/$normalized/chart-history?period=$period';
  }

  /// Feed des modules Marketing Cards Sliding depuis les vaults (optionnel: investmentTypeSlug).
  static String vaultsMarketingCardsFeedUrl({String? investmentTypeSlug}) {
    final base = '$apiBaseUrl/api/mobile/flutter/vaults/marketing-cards-feed';
    if (investmentTypeSlug != null && investmentTypeSlug.trim().isNotEmpty) {
      return '$base?investmentTypeSlug=${Uri.encodeComponent(investmentTypeSlug.trim())}';
    }
    return base;
  }

  /// Articles liés à un projet (section « related project », table article_projects).
  static String projectArticlesUrl(String projectId) =>
      '$apiBaseUrl/api/projects/$projectId/articles';

  /// Catégories d'investissement (page Offres).
  static String get investmentCategoriesUrl => '$apiBaseUrl/api/investment-categories';

  /// Recherche Help Center / FAQ.
  static String get helpSearchUrl => '$apiBaseUrl/api/help/search';

  /// Collections Help Center.
  static String get helpCollectionsUrl => '$apiBaseUrl/api/help/collections';

  /// Categories d'une collection Help.
  static String helpCollectionCategoriesUrl(String collectionSlug) =>
      '$apiBaseUrl/api/help/collections/$collectionSlug/categories';

  /// Hub Help (tags dérivés des articles + mode liste plate si un seul groupe).
  static String helpCollectionBrowseUrl(String collectionSlug) =>
      '$apiBaseUrl/api/help/collections/$collectionSlug/browse';

  /// Tous les articles Help d'une collection (liste plate).
  static String helpCollectionAllArticlesUrl(String collectionSlug) =>
      '$apiBaseUrl/api/help/collections/$collectionSlug/articles';

  /// Articles d'une category Help.
  static String helpCategoryArticlesUrl(String collectionSlug, String categorySlug) =>
      '$apiBaseUrl/api/help/collections/$collectionSlug/categories/$categorySlug/articles';

  /// Detail d'un article Help.
  static String helpArticleDetailUrl(
    String collectionSlug,
    String categorySlug,
    String articleSlug,
  ) =>
      '$apiBaseUrl/api/help/collections/$collectionSlug/categories/$categorySlug/articles/$articleSlug';

  /// Liste d'articles Help filtrée par tag (ex. projet EXCLUSIVE_OFFER).
  static String get helpArticlesByTagUrl => '$apiBaseUrl/api/help/articles/by-tag';

  /// Article Help par slug unique (FAQ, premier trouvé).
  static String get helpArticleBySlugUrl => '$apiBaseUrl/api/help/articles/by-slug';

  // ─────────────────────────────────────────────────────────────────────────
  //  ACADEMY — endpoints symétriques à Help (Phase 4 — pédagogie produit)
  // ─────────────────────────────────────────────────────────────────────────

  /// Recherche Academy.
  static String get academySearchUrl => '$apiBaseUrl/api/academy/search';

  /// Collections Academy.
  static String get academyCollectionsUrl => '$apiBaseUrl/api/academy/collections';

  /// Categories d'une collection Academy.
  static String academyCollectionCategoriesUrl(String collectionSlug) =>
      '$apiBaseUrl/api/academy/collections/$collectionSlug/categories';

  /// Articles d'une category Academy.
  static String academyCategoryArticlesUrl(String collectionSlug, String categorySlug) =>
      '$apiBaseUrl/api/academy/collections/$collectionSlug/categories/$categorySlug/articles';

  /// Detail d'un article Academy.
  static String academyArticleDetailUrl(
    String collectionSlug,
    String categorySlug,
    String articleSlug,
  ) =>
      '$apiBaseUrl/api/academy/collections/$collectionSlug/categories/$categorySlug/articles/$articleSlug';

  /// Liste d'articles Academy filtrée par tag (ex. projet EXCLUSIVE_OFFER).
  static String get academyArticlesByTagUrl => '$apiBaseUrl/api/academy/articles/by-tag';

  /// Article Academy par slug unique (premier trouvé).
  static String get academyArticleBySlugUrl => '$apiBaseUrl/api/academy/articles/by-slug';

  /// Chat conversationnel (réponses Markdown via OpenAI).
  ///
  /// **Legacy / non authentifié** — gardé pour compat le temps que toutes les
  /// builds passent à [mobileAssistanceChatTurnUrl] (MVP D.0.1, persistance
  /// per-client + rate-limit côté Python). À retirer après validation prod.
  static String get chatUrl => '$apiBaseUrl/api/chat';

  /// Assistance « sur mesure » mobile (Search Screen) — proxy BFF Next →
  /// FastAPI Python `/api/app/assistance/chat/turn`. Authentifié par Bearer JWT
  /// (cf. [SessionBearerHttp]), retourne `{ conversationId, messageId, content }`.
  static String get mobileAssistanceChatTurnUrl =>
      '$apiBaseUrl/api/mobile/flutter/assistance/chat/turn';

  /// Historique d'une conversation d'assistance (MVP D.1.6 — reprise visuelle).
  /// Renvoie `{ conversation_id, title, status, messages: [{turn_index, role, content, created_at}, …] }`,
  /// trié par `turn_index` croissant. Limit par défaut côté serveur = 100.
  static String mobileAssistanceConversationMessagesUrl(
    String conversationId, {
    int? limit,
  }) {
    final base =
        '$apiBaseUrl/api/mobile/flutter/assistance/conversations/${Uri.encodeComponent(conversationId)}/messages';
    if (limit != null && limit > 0) {
      return '$base?limit=$limit';
    }
    return base;
  }

  /// MVP D.1.4.2 — POST `/conversations/{id}/read` : marque comme lue.
  static String mobileAssistanceConversationReadUrl(String conversationId) {
    return '$apiBaseUrl/api/mobile/flutter/assistance/conversations/${Uri.encodeComponent(conversationId)}/read';
  }

  /// MVP D.1.4.5 — POST `/chat/turn/stream` : streaming SSE (effet
  /// ChatGPT mot-par-mot). Fallback automatique sur polling si le stream
  /// échoue (réseau, proxy, edge buffering).
  static String get mobileAssistanceChatTurnStreamUrl =>
      '$apiBaseUrl/api/mobile/flutter/assistance/chat/turn/stream';

  /// MVP D.1.4.7 — POST `/chat/turn/{conv_id}/cancel` : annulation
  /// volontaire du tour assistant en cours (équivalent du carré stop
  /// ChatGPT). Idempotent (204 même si pas de génération en cours).
  /// Ne tue PAS la task sur disconnect réseau — seulement sur appel
  /// explicite à cet endpoint.
  static String mobileAssistanceChatTurnCancelUrl(String conversationId) {
    return '$apiBaseUrl/api/mobile/flutter/assistance/chat/turn/${Uri.encodeComponent(conversationId)}/cancel';
  }

  /// Voice input — moteur Whisper uniquement.
  ///
  /// Endpoint upload audio (multipart `audio` field, .m4a/aacLc) →
  /// proxy BFF Next vers `POST /api/app/assistance/voice/transcribe`
  /// (FastAPI Python qui appelle l'API OpenAI Whisper). Authentifié
  /// par Bearer JWT (cf. [SessionBearerHttp]).
  ///
  /// Retourne `{ "transcript": "..." }`.
  ///
  /// **Pas appelé** quand `ASSISTANCE_VOICE_ENGINE=native` (défaut) :
  /// la transcription a lieu localement via le moteur natif iOS/Android,
  /// sans aucun upload réseau.
  static String get mobileAssistanceVoiceTranscribeUrl =>
      '$apiBaseUrl/api/mobile/flutter/assistance/voice/transcribe';

  /// Liste des conversations d'assistance du client (MVP D.1.4 — page
  /// « Mes conversations »). Renvoie `{ conversations: [{id, title, status,
  /// created_at, last_message_at}, …] }` triée par `last_message_at` DESC.
  /// Filtres optionnels : `status=active|closed`, `limit` (1-100, défaut 50),
  /// `before` (ISO datetime pour pagination cursor-based).
  static String mobileAssistanceConversationsUrl({
    String? status,
    int? limit,
    String? before,
  }) {
    final base = '$apiBaseUrl/api/mobile/flutter/assistance/conversations';
    final params = <String>[];
    if (status != null && status.isNotEmpty) {
      params.add('status=${Uri.encodeComponent(status)}');
    }
    if (limit != null && limit > 0) {
      params.add('limit=$limit');
    }
    if (before != null && before.isNotEmpty) {
      params.add('before=${Uri.encodeComponent(before)}');
    }
    return params.isEmpty ? base : '$base?${params.join('&')}';
  }

  /// Base URL de l’API Market Data (FastAPI).
  /// - Si MARKET_DATA_BASE_URL est défini : utilisé (sur iOS, localhost → 127.0.0.1 pour le simulateur).
  /// - Sinon : même host que apiBaseUrl avec port 8000.
  /// Émulateur Android : préférer MARKET_DATA_BASE_URL=http://10.0.2.2:8000
  static const String _marketDataBaseUrlEnv = String.fromEnvironment(
    'MARKET_DATA_BASE_URL',
    defaultValue: '',
  );
  static String get marketDataBaseUrl {
    if (_marketDataBaseUrlEnv.trim().isNotEmpty) {
      final base = _marketDataBaseUrlEnv.trim();
      if (Platform.isIOS) {
        final u = Uri.parse(base);
        if (u.host == 'localhost') {
          final p = u.hasPort ? u.port : 8000;
          return '${u.scheme}://127.0.0.1:$p';
        }
      }
      return base;
    }
    // Même hôte que le BFF (Next), port 8000 (FastAPI) — indispensable sur iPhone physique (pas 127.0.0.1).
    final uri = Uri.parse(apiBaseUrl);
    return '${uri.scheme}://${uri.host}:8000';
  }

  static String get marketSummaryUrl => '$marketDataBaseUrl/api/market-data/market-summary';
  static String get topMoversUrl => '$marketDataBaseUrl/api/market-data/top-movers';
  static String get allCryptoUrl => '$marketDataBaseUrl/api/market-data/all-crypto';
  static String get quotesLatestUrl => '$marketDataBaseUrl/api/market-data/quotes/latest';
  static String get candles5mUrl => '$marketDataBaseUrl/api/market-data/candles/5m';
  static String get candles1hUrl => '$marketDataBaseUrl/api/market-data/candles/1h';
  static String get candles4hUrl => '$marketDataBaseUrl/api/market-data/candles/4h';
  static String get candles1dUrl => '$marketDataBaseUrl/api/market-data/candles/1d';
  static String get candles1wUrl => '$marketDataBaseUrl/api/market-data/candles/1w';
  static String get chartHistoryUrl => '$marketDataBaseUrl/api/market-data/chart-history';

  /// 2FA (OTP SMS/email + TOTP) — FastAPI, même base que l’API market data.
  static String get twoFactorStartUrl => '$marketDataBaseUrl/api/2fa/start';
  static String get twoFactorVerifyUrl => '$marketDataBaseUrl/api/2fa/verify';

  /// WebSocket URL for live market quotes. Path: /ws/market-data?symbols=...
  static String get wsMarketDataBaseUrl {
    final base = marketDataBaseUrl;
    if (base.startsWith('https://')) {
      return 'wss://${base.substring(8)}';
    }
    if (base.startsWith('http://')) {
      return 'ws://${base.substring(7)}';
    }
    return base;
  }

  static String wsMarketDataUrl(String symbolsQuery) =>
      '$wsMarketDataBaseUrl/ws/market-data?symbols=${Uri.encodeComponent(symbolsQuery)}';

  /// Résout l'URL du logo : si relative (ex. /media/crypto_logos/btc.png), préfixe avec [marketDataBaseUrl]
  /// pour que l'appareil charge l'image depuis le même hôte que l'API (évite localhost inaccessible).
  static String? resolveLogoUrl(String? logoUrl) {
    if (logoUrl == null || logoUrl.trim().isEmpty) return null;
    final u = logoUrl.trim();
    if (u.startsWith(RegExp(r'https?://'))) return u;
    final base = marketDataBaseUrl.endsWith('/')
        ? marketDataBaseUrl.substring(0, marketDataBaseUrl.length - 1)
        : marketDataBaseUrl;
    return base + (u.startsWith('/') ? u : '/$u');
  }
}
