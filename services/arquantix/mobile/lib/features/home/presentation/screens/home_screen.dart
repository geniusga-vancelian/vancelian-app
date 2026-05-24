import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';


import '../../../../core/config.dart';
import '../../../../core/profile_identity_coordinator.dart';
import '../../../../core/secure_api_config.dart';
import '../../../../core/session_bearer_http.dart';
import '../../../../core/http_error_display.dart';
import '../../../../core/currency_preference.dart';
import '../../../../core/profile_leading_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../../../ui/navigation/bottom_nav_content_inset.dart';
import '../../../../ui/components/wallets/wallets_module.dart';
import '../../../wallet/widgets/dashboard_scroll_template.dart';
import '../../../wallet/widgets/wallet_header.dart';
import '../../data/dashboard_layout_api.dart';
import '../../../news/data/blog_api.dart';
import '../../../news/domain/models/article.dart';
import '../../../news/presentation/screens/article_detail_screen.dart';
import '../../../notifications/data/notifications_api.dart';
import '../../../notifications/presentation/screens/notification_center_screen.dart';
import '../../../profile/presentation/screens/profile_screen.dart';
import '../../../deposit/presentation/screens/deposit_carte_screen.dart';
import '../../../deposit/presentation/screens/deposit_crypto_screen.dart';
import '../../../deposit/presentation/screens/deposit_virement_screen.dart';
import '../../../wallet/data/crypto_positions_api.dart';
import '../../../wallet/data/global_statistics_api.dart';
import '../../../wallet/domain/models/crypto_positions_data.dart';
import '../../../wallet/domain/models/global_statistics.dart';
import '../../../placements/data/placements_api.dart';
import '../../../placements/domain/models/placement_position.dart';
import '../../../placements/presentation/screens/placements_screen.dart';
import '../../../wallet/presentation/screens/all_crypto_positions_screen.dart';
import '../../../wallet/presentation/screens/compte_euro_screen.dart';
import '../../../wallet/presentation/screens/global_statistics_screen.dart';
import '../../../wallet/presentation/privy_wallet_create_entry.dart';
import '../../../wallet/privy/privy_dart_defines.dart';
import '../../../offers/presentation/screens/offers_screen.dart';
import '../../../offers/presentation/widgets/vaults_marketing_cards_feed.dart';
import 'package:intl/intl.dart';

import '../../../wallet/data/cash_api.dart';
import '../../../wallet/domain/models/cash_data.dart';
import '../../../auth/application/auth_logout.dart';
import '../../../../core/session_identity_context.dart';
import '../../../../core/privy_identity_bridge_service.dart';
import '../../../../core/registration_resume_prompt_gate.dart';
import '../../../profile/data/mobile_app_profile.dart';
import '../../../profile/debug/mobile_app_profile_registration_debug.dart';
import '../../../registration/data/registration_api.dart';
import '../../../registration/screens/registration_flow_screen.dart';
import '../../../registration/widgets/registration_flow_step_info.dart';
import '../../../registration/widgets/registration_progress_module.dart';
import '../../../registration/widgets/registration_progress_module_builder.dart';
import '../../../activation/analytics/activation_journey_funnel_events.dart';
import '../../../activation/presentation/activation_home_visibility.dart';
import '../../../activation/presentation/activation_stage_ui_helpers.dart';
import '../../application/partial_registration_dashboard_rules.dart';
import '../../../activation/presentation/widgets/activation_journey_home_module.dart';
import '../widgets/home_pre_deposit_activation_hero.dart';
import '../../../../core/session/session_lifecycle_state.dart';
import '../../../../core/session/session_state_machine.dart';
import '../../../security/passcode/data/session_service.dart';

/// Page d'accueil : contenu blog (A la une) sous la carte My account.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with TickerProviderStateMixin {
  final BlogApi _api = BlogApi();
  final DashboardLayoutApi _dashboardLayoutApi = DashboardLayoutApi();
  final CashApi _cashApi = CashApi();
  final CryptoPositionsApi _cryptoApi = const CryptoPositionsApi();
  final GlobalStatisticsApi _globalStatsApi = const GlobalStatisticsApi();
  final NotificationsApi _notificationsApi = NotificationsApi();
  final PlacementsApi _placementsApi = const PlacementsApi();
  CashData? _cashData;
  CryptoPositionsData? _cryptoData;
  PlacementsData? _placementsData;
  List<double>? _heroChartData;
  double _heroPerformancePct = 0;
  /// Patrimoine total aligné sur `GET /portfolio/global/statistics` (fiat + crypto + bundles).
  GlobalStatistics? _globalStats;
  bool _cashLoading = true;
  bool _cashError = false;
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _dashboardLayout;
  List<ArticlePreview> _latestNews = const [];
  /// Pour afficher la pastille "messages en attente" sur l'icône messagerie.
  bool _hasUnreadMessages = true;
  int _unreadNotificationCount = 0;

  /// Bloc activation / reprise inscription (au moins une macro-étape incomplète).
  bool _showActivationModule = false;
  String _registrationJurisdiction = 'EU';
  bool _registrationResumeModalVisible = false;
  RegistrationProgressModuleData? _registrationModuleData;
  bool _registrationModuleLoading = false;
  String? _registrationModuleError;

  /// Période affichée pour la performance (All time par défaut). Modifiable via la modale de sélection.
  String _selectedPeriodLabel = 'All time';

  /// Thème du header : dark ou light (header de test en light avec fond grain-gris, éléments en sombre).
  WalletHeaderTheme _headerTheme = WalletHeaderTheme.dark;

  ScrollController? _scrollController;
  bool _layoutReloadInFlight = false;
  DateTime? _lastLayoutReloadAt;
  static const Duration _layoutReloadMinInterval = Duration(seconds: 2);
  static const double _layoutReloadOverscrollThreshold = -20;

  /// Incrémenté au pull-to-refresh pour forcer le rechargement du widget news (cache-bust API + images).
  int _vancelianNewsRefreshNonce = 0;

  /// Wallets Privy persistés (`GET /auth/privy/person-wallets`). -1 = chargement inconnu / erreur.
  int _personCryptoWalletCount = -1;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(_lifecycleObserver);
    _scrollController = ScrollController();
    _scrollController?.addListener(_onScrollForLayoutReload);
    _loadAll(forceLayoutRefresh: true);
  }

  late final WidgetsBindingObserver _lifecycleObserver = _DashboardLifecycleObserver(
    onAppResumed: () => _loadAll(forceLayoutRefresh: true),
  );

  @override
  void reassemble() {
    super.reassemble();
    // Hot reload/hot refresh en debug : relire le layout depuis la base.
    _loadAll(forceLayoutRefresh: true);
  }

  Future<void> _loadAll({
    bool forceLayoutRefresh = false,
    bool refreshVancelianNews = false,
  }) async {
    if (refreshVancelianNews && mounted) {
      setState(() {
        _vancelianNewsRefreshNonce++;
      });
    }
    final session = SessionService.instance;
    final hasSession = await session.hasSessionCredentials();

    // Garde : session serveur attendue → aucun appel parallèle (y compris bootstrap) sans Bearer.
    if (hasSession) {
      final token =
          await SessionIdentityContext.instance.waitForAccessTokenForDashboard();
      if (token == null) {
        debugPrint(
          '[HomeScreen][guard] session attendue mais access token absent après attente — '
          'aucun chargement authentifié',
        );
        if (mounted) {
          setState(() {
            _loading = false;
            _showActivationModule = false;
            _registrationModuleData = null;
            _registrationModuleLoading = false;
            _registrationModuleError = null;
          });
        }
        return;
      }
      if (kDebugMode) {
        debugPrint(
          '[HomeScreen][guard] access token prêt (opaque len=${token.length}) — '
          'bootstrap + chargements',
        );
      }
    } else if (kDebugMode) {
      debugPrint(
        '[HomeScreen][guard] pas de session stockée — flux public / dev (sans Bearer)',
      );
    }

    SessionStateMachine.instance.apply(SessionLifecycleEvent.homeBootstrapStarted);
    final trackBootstrappingHome =
        SessionStateMachine.instance.state == SessionLifecycleState.bootstrappingHome;
    try {
      await _loadBootstrap();
      await Future.wait([
        _loadDashboardLayout(forceRefresh: forceLayoutRefresh),
        _loadFeed(),
        _loadCashData(),
        _loadCryptoData(),
        _loadPlacementsData(),
        _loadHeroChart(),
        _loadUnreadNotificationCount(),
        _loadPersonCryptoWalletsSnapshot(),
      ]);
      // Même source que Mon compte : initiales depuis GET /profile (JWT), après bootstrap.
      if (hasSession) {
        final prevActivationJourney =
            ProfileIdentityCoordinator.instance.cachedProfile?.activationJourney;
        final profile = await ProfileIdentityCoordinator.instance
            .refreshDisplayIdentity(debugTag: 'HomeScreen');
        if (mounted) {
          final newAj = profile?.activationJourney;
          if (newAj != null) {
            ActivationJourneyFunnelEvents.emitProgressDiff(
              prevActivationJourney,
              newAj,
            );
          }
          final showActivation =
              profile != null && shouldShowActivationModuleCard(profile);
          final aj = profile?.activationJourney;
          final needsLegacyRegistrationFlow = showActivation &&
              aj == null &&
              profile != null &&
              profile.shouldShowRegistrationResume;
          setState(() {
            _showActivationModule = showActivation;
            final j = profile?.jurisdiction?.trim();
            _registrationJurisdiction =
                (j != null && j.isNotEmpty) ? j : 'EU';
            if (needsLegacyRegistrationFlow) {
              _registrationModuleLoading = true;
              _registrationModuleError = null;
            } else {
              _registrationModuleData = null;
              _registrationModuleLoading = false;
              _registrationModuleError = null;
            }
          });
          _tryShowRegistrationResumeSoftPrompt(profile);
          await _loadRegistrationModuleData(profile);
        }
      } else if (mounted) {
        setState(() {
          _showActivationModule = false;
          _registrationModuleData = null;
          _registrationModuleLoading = false;
          _registrationModuleError = null;
        });
      }
    } finally {
      if (trackBootstrappingHome) {
        SessionStateMachine.instance
            .apply(SessionLifecycleEvent.homeBootstrapCompleted);
      }
    }
  }

  Future<void> _loadPersonCryptoWalletsSnapshot() async {
    if (!SecureApiConfig.hasAuthBackend) {
      if (mounted) setState(() => _personCryptoWalletCount = 0);
      return;
    }
    if (!(await SessionService.instance.hasSessionCredentials())) {
      if (mounted) setState(() => _personCryptoWalletCount = 0);
      return;
    }
    try {
      final list =
          await PrivyIdentityBridgeService.instance.fetchAuthenticatedPersonCryptoWallets();
      if (mounted) setState(() => _personCryptoWalletCount = list.length);
    } catch (_) {
      if (mounted) setState(() => _personCryptoWalletCount = -1);
    }
  }

  String _heroMoreButtonLabel() =>
      _personCryptoWalletCount > 0 ? 'Mon wallet crypto' : 'Create wallet';

  Future<void> _loadBootstrap() async {
    try {
      final accessToken = await SessionService.instance.readAccessToken();
      final expectAuth =
          await SessionService.instance.hasSessionCredentials();
      if (expectAuth &&
          (accessToken == null || accessToken.trim().isEmpty)) {
        debugPrint(
          '[HomeScreen][bootstrap] abandon: session annoncée sans token lisible',
        );
        return;
      }

      Future<void> applyBody(String body) async {
        if (responseBodyLooksLikeNonJsonApi(body)) {
          debugPrint('[HomeScreen] Bootstrap: ignored non-JSON body');
          return;
        }
        try {
          final json = jsonDecode(body) as Map<String, dynamic>;
          final client = json['client'] as Map<String, dynamic>? ?? {};
          final cid = client['id'];
          if (cid != null) {
            SessionIdentityContext.instance
                .hydrateResolvedClientIdFromBootstrap(cid.toString());
          }
          CurrencyPreference.instance.loadFromBootstrap(
            client['reference_currency'] as String?,
          );
          ProfileLeadingPreference.instance.loadFromBootstrapJson(
            client['initials'],
          );
        } catch (e) {
          debugPrint('[HomeScreen] Bootstrap JSON parse error: $e');
        }
      }

      final bootstrapUri = Uri.parse(Config.bootstrapUrl);
      final bootstrapHeaders = await SessionBearerHttp.jsonHeadersAppScoped(
        uri: bootstrapUri,
        debugTag: 'HomeScreen.bootstrap',
        overrideAccessToken: accessToken,
      );

      var res = await http.get(
        bootstrapUri,
        headers: bootstrapHeaders,
      );
      if (kDebugMode) {
        final hasBearer = accessToken != null && accessToken.isNotEmpty;
        debugPrint(
          '[HomeScreen][bootstrap] bearer=$hasBearer status=${res.statusCode} '
          'url=${Config.bootstrapUrl}',
        );
      }
      if (res.statusCode == 404) {
        if (accessToken == null || accessToken.isEmpty) {
          debugPrint(
            '[HomeScreen] Bootstrap: 404 — connexion ou inscription requise '
            '(le bootstrap nécessite une session).',
          );
        } else {
          debugPrint(
            '[HomeScreen] Bootstrap: 404 avec session — profil client introuvable ou non lié.',
          );
        }
      }
      if (res.statusCode == 200) {
        await applyBody(res.body);
      }
    } catch (e) {
      debugPrint('[HomeScreen] Bootstrap error: $e');
    }
  }

  Future<void> _loadCashData() async {
    if (mounted) setState(() { _cashLoading = true; _cashError = false; });
    try {
      final data = await _cashApi.fetchCashData();
      if (mounted) setState(() { _cashData = data; _cashLoading = false; });
    } catch (e) {
      debugPrint('[HomeScreen] Cash data not available: $e');
      if (mounted) setState(() { _cashLoading = false; _cashError = true; });
    }
  }

  Future<void> _loadCryptoData() async {
    try {
      final data = await _cryptoApi.fetchPositions();
      if (mounted) setState(() { _cryptoData = data; });
    } catch (e) {
      debugPrint('[HomeScreen] Crypto positions not available: $e');
    }
  }

  Future<void> _loadPlacementsData() async {
    try {
      final data = await _placementsApi.fetchEarnPositions();
      if (mounted) setState(() { _placementsData = data; });
    } catch (e) {
      debugPrint('[HomeScreen] Placements data not available: $e');
    }
  }

  Future<void> _loadHeroChart() async {
    try {
      final results = await Future.wait([
        _globalStatsApi.fetchHistory(period: 'ALL'),
        _globalStatsApi.fetchStatistics(),
      ]);
      if (!mounted) return;
      final histResult = results[0] as GlobalHistoryResult;
      final stats = results[1] as GlobalStatistics;
      final points = histResult.points;
      List<double>? normalized;
      if (points.isNotEmpty) {
        final chartValues = points.map((p) => p.performanceValue).toList();
        final mn = chartValues.reduce((a, b) => a < b ? a : b);
        final mx = chartValues.reduce((a, b) => a > b ? a : b);
        final range = (mx - mn).abs() < 0.01 ? 1.0 : (mx - mn);
        normalized = chartValues.map((v) => (v - mn) / range).toList();
      }

      setState(() {
        _globalStats = stats;
        _heroPerformancePct = stats.performancePct;
        _heroChartData = normalized;
      });
    } catch (e) {
      debugPrint('[HomeScreen] Hero chart not available: $e');
      if (mounted) {
        setState(() => _globalStats = null);
      }
    }
  }

  Future<void> _loadUnreadNotificationCount() async {
    try {
      final count = await _notificationsApi.fetchUnreadCount();
      if (mounted) setState(() => _unreadNotificationCount = count);
    } catch (_) {
      // Graceful: keep previous count
    }
  }

  Future<void> _loadDashboardLayout({bool forceRefresh = false}) async {
    try {
      final layout = await _dashboardLayoutApi.getDashboardLayout(
        forceRefresh: forceRefresh,
      );
      if (mounted) setState(() => _dashboardLayout = layout);
    } catch (_) {
      // Fallback silencieux : on garde le rendu local statique si la lecture DB échoue.
      if (mounted) setState(() => _dashboardLayout = null);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(_lifecycleObserver);
    _scrollController?.removeListener(_onScrollForLayoutReload);
    _scrollController?.dispose();
    super.dispose();
  }

  void _onScrollForLayoutReload() {
    final controller = _scrollController;
    if (controller == null || !controller.hasClients) return;
    if (_layoutReloadInFlight) return;

    final now = DateTime.now();
    if (_lastLayoutReloadAt != null &&
        now.difference(_lastLayoutReloadAt!) < _layoutReloadMinInterval) {
      return;
    }

    // Pull down en haut de page (overscroll négatif) => relire le layout DB.
    final pixels = controller.position.pixels;
    if (pixels <= _layoutReloadOverscrollThreshold) {
      _layoutReloadInFlight = true;
      _lastLayoutReloadAt = now;
      _loadDashboardLayout(forceRefresh: true).whenComplete(() {
        _layoutReloadInFlight = false;
      });
    }
  }

  Future<void> _loadFeed() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _api.getFeed(
        page: 1,
        pageSize: 20,
      );
      final allNews = <ArticlePreview>[];
      if (data.featured != null) allNews.add(data.featured!);
      allNews.addAll(data.highlighted);
      allNews.addAll(data.articles);
      setState(() {
        _latestNews = allNews;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e is BlogApiException ? e.message : e.toString();
      });
    }
  }


  void _onWalletTap(WalletItem item) {
    if (item.title == 'Euro Account') {
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (context) => const CompteEuroScreen(),
        ),
      );
    } else if (item.title == 'Crypto') {
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (context) => const AllCryptoPositionsScreen(),
        ),
      );
    } else if (item.title == 'Exclusive offers') {
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (context) => const PlacementsScreen(),
        ),
      ).then((_) {
        if (mounted) _loadPlacementsData();
      });
    }
  }

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  static final _usdFormatter = NumberFormat.currency(
    locale: 'en_US',
    symbol: '\$',
    decimalDigits: 2,
  );

  NumberFormat get _activeFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _usdFormatter
          : _eurFormatter;

  List<WalletItem> get _walletItems {
    final defaults = mockWalletItems;
    final account = _cashData?.cashAccount;
    final pref = CurrencyPreference.instance;

    return defaults.map((item) {
      if (item.title == 'Euro Account' && account != null) {
        final eurBalance = account.availableBalance;
        return WalletItem(
          title: item.title,
          subtitle: item.subtitle,
          balance: _eurFormatter.format(eurBalance),
          numericBalance: eurBalance,
          change: item.change,
          icon: item.icon,
          iconBackgroundColor: item.iconBackgroundColor,
        );
      }
      if (item.title == 'Crypto' && _cryptoData != null) {
        final crypto = _cryptoData!;
        final countLabel = crypto.hasPrivyLedgerPositions
            ? '${crypto.positionsCount} crypto-actif${crypto.positionsCount > 1 ? 's' : ''} · incl. Privy'
            : '${crypto.positionsCount} crypto-actif${crypto.positionsCount > 1 ? 's' : ''}';
        final cryptoValue = pref.selectValue(
          eur: crypto.totalValueEur,
          usd: crypto.totalValueUsd,
        ) ?? 0;
        return WalletItem(
          title: item.title,
          subtitle: countLabel,
          balance: _activeFormatter.format(cryptoValue),
          numericBalance: cryptoValue,
          change: item.change,
          icon: item.icon,
          iconBackgroundColor: item.iconBackgroundColor,
        );
      }
      if (item.title == 'Exclusive offers' && _placementsData != null) {
        final placements = _placementsData!;
        final countLabel = placements.positionsCount > 0
            ? '${placements.positionsCount} placement${placements.positionsCount > 1 ? 's' : ''}'
            : 'Discover exclusive offers!';
        return WalletItem(
          title: item.title,
          subtitle: countLabel,
          balance: _eurFormatter.format(placements.totalValueEur),
          numericBalance: placements.totalValueEur,
          change: item.change,
          icon: item.icon,
          iconBackgroundColor: item.iconBackgroundColor,
        );
      }
      return item;
    }).toList();
  }

  /// Montant sous « Balance » : priorité à la valorisation globale API (même source que Statistiques).
  /// Sinon repli sur la somme Compte euro + Crypto uniquement (sans offres / lignes mock).
  String get _headerBalanceSubtitle {
    final stats = _globalStats;
    if (stats != null) {
      return _activeFormatter.format(stats.currentValue);
    }
    var sum = 0.0;
    for (final w in _walletItems) {
      if (w.title == 'Euro Account' || w.title == 'Crypto') {
        sum += w.numericBalance;
      }
    }
    return _activeFormatter.format(sum);
  }

  /// Modal douce : PARTIAL + progression déjà entamée (pas de redirection forcée).
  bool _eligibleForRegistrationSoftPrompt(MobileAppProfile? p) {
    if (p == null) return false;
    if ((p.clientStatus ?? '').toUpperCase() != 'PARTIAL') return false;
    final pct = p.registrationProgressDisplayPercent;
    final done = p.registrationDerivedCompletedCount;
    if (pct > 0) return true;
    if (done != null && done > 0) return true;
    return false;
  }

  void _tryShowRegistrationResumeSoftPrompt(MobileAppProfile? profile) {
    if (_registrationResumeModalVisible) return;
    if (!_eligibleForRegistrationSoftPrompt(profile)) return;
    if (!RegistrationResumePromptGate.shouldOfferPrompt()) return;
    _registrationResumeModalVisible = true;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) {
        _registrationResumeModalVisible = false;
        return;
      }
      final p = ProfileIdentityCoordinator.instance.cachedProfile;
      if (!_eligibleForRegistrationSoftPrompt(p)) {
        _registrationResumeModalVisible = false;
        return;
      }
      if (!RegistrationResumePromptGate.shouldOfferPrompt()) {
        _registrationResumeModalVisible = false;
        return;
      }
      try {
        await Modale.show<void>(
          context,
          ModaleParams(
            title: 'Reprendre votre inscription ?',
            description: p!.registrationResumePromptModalDescription,
            primaryButton: ModaleButtonConfig(
              label: 'Continuer',
              onTapAsync: () async {
                _openRegistrationResume();
              },
            ),
            secondaryButton: ModaleButtonConfig(
              label: 'Plus tard',
            ),
          ),
        );
      } finally {
        if (mounted) {
          _registrationResumeModalVisible = false;
        }
        RegistrationResumePromptGate.suppressForCurrentIdentity();
      }
    });
  }

  void _openRegistrationResume() {
    Navigator.of(context)
        .push<void>(
      MaterialPageRoute<void>(
        builder: (_) => RegistrationFlowScreen(
          jurisdiction: _registrationJurisdiction,
        ),
      ),
    )
        .then((_) {
      if (mounted) {
        unawaited(_loadAll(forceLayoutRefresh: false));
      }
    });
  }

  /// Même module que le hub « Parcours d’inscription » : flux actif + progression dérivée profil.
  Future<void> _loadRegistrationModuleData(MobileAppProfile? profile) async {
    if (profile == null) {
      debugLogRegistrationModuleApi(
        tag: 'HomeScreen._loadRegistrationModuleData',
        skipped: true,
        skipReason: 'profil null',
      );
      if (mounted) {
        setState(() {
          _registrationModuleData = null;
          _registrationModuleLoading = false;
          _registrationModuleError = null;
        });
      }
      return;
    }
    // Parcours d’activation : pas de second appel flux — les libellés viennent du profil.
    if (profile.activationJourney != null) {
      if (mounted) {
        setState(() {
          _registrationModuleData = null;
          _registrationModuleLoading = false;
          _registrationModuleError = null;
        });
      }
      return;
    }
    if (!profile.shouldShowRegistrationResume) {
      debugLogRegistrationModuleApi(
        tag: 'HomeScreen._loadRegistrationModuleData',
        skipped: true,
        skipReason: 'shouldShowRegistrationResume=false',
      );
      if (mounted) {
        setState(() {
          _registrationModuleData = null;
          _registrationModuleLoading = false;
          _registrationModuleError = null;
        });
      }
      return;
    }

    try {
      final api = RegistrationApi(
        baseUrl: Config.marketDataBaseUrl,
        accessTokenResolver: SessionService.instance.readAccessToken,
      );
      final jRes = await api.getCurrentJurisdiction();
      if (!mounted) return;
      if (!jRes.isSuccess || jRes.data == null) {
        throw Exception(jRes.errorMessage ?? 'Chargement juridiction');
      }
      final jBody = jRes.data!;
      final jCode = jBody['jurisdiction_code'] as String?;
      final jName = jBody['jurisdiction_name'] as String?;
      final flowName = jBody['active_flow_name'] as String?;
      final flowVersion = jBody['active_flow_version'] as int?;
      final flowId = jBody['active_flow_id'] as String?;

      var steps = <RegistrationFlowStepInfo>[];
      if (jCode != null && jCode.isNotEmpty) {
        final flowRes = await api.getActiveFlow(jCode);
        if (flowRes.isSuccess && flowRes.data != null) {
          steps = RegistrationFlowStepInfo.fromFlowJson(flowRes.data!);
        }
      }

      final canLaunch = jCode != null &&
          jCode.isNotEmpty &&
          flowId != null &&
          flowId.isNotEmpty;
      final resolvedJurisdiction = (jCode != null && jCode.isNotEmpty)
          ? jCode
          : ((profile.jurisdiction?.trim().isNotEmpty ?? false)
              ? profile.jurisdiction!.trim()
              : 'EU');

      final moduleData = RegistrationProgressModuleBuilder.build(
        profile: profile,
        flowSteps: steps,
        jurisdictionName: jName,
        flowName: flowName,
        flowVersion: flowVersion,
        canLaunch: canLaunch,
        onNavigate: _openRegistrationResume,
      );

      if (mounted) {
        setState(() {
          _registrationJurisdiction = resolvedJurisdiction;
          _registrationModuleData = moduleData;
          _registrationModuleLoading = false;
          _registrationModuleError = null;
        });
      }
      debugLogRegistrationModuleApi(
        tag: 'HomeScreen._loadRegistrationModuleData',
        skipped: false,
        jurisdictionCode: jCode,
        flowId: flowId,
        flowStepsCount: steps.length,
        canLaunch: canLaunch,
      );
    } catch (e, st) {
      debugPrint('[HomeScreen] registration module: $e\n$st');
      debugLogRegistrationModuleApi(
        tag: 'HomeScreen._loadRegistrationModuleData',
        skipped: false,
        error: e,
      );
      if (!mounted) return;
      final fallbackJurisdiction =
          (profile.jurisdiction?.trim().isNotEmpty ?? false)
              ? profile.jurisdiction!.trim()
              : 'EU';
      setState(() {
        _registrationJurisdiction = fallbackJurisdiction;
        _registrationModuleData = null;
        _registrationModuleLoading = false;
        _registrationModuleError = e.toString();
      });
    }
  }

  Widget _buildRegistrationModuleErrorBanner() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.errorBackground,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            _registrationModuleError ?? 'Erreur de chargement',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.errorText,
            ),
          ),
        ),
        const SizedBox(height: 12),
        AppPrimaryButton(
          label: 'Continuer',
          onPressed: _openRegistrationResume,
        ),
      ],
    );
  }

  Widget _buildAccountsCard() {
    final walletItems = _walletItems;
    return TransactionListCard(
      items: walletItems.map((w) {
        final changeLabel = w.change;
        Color? changeColor;
        if (changeLabel != null && changeLabel.isNotEmpty) {
          if (changeLabel.contains('-')) {
            changeColor = AppColors.red;
          } else {
            changeColor = AppColors.green;
          }
        }
        return TransactionListItemData(
          leadingWidget: IconContainer(
            size: IconContainerSize.md,
            backgroundColor: w.iconBackgroundColor,
            child: Icon(w.icon, size: 20, color: Colors.white),
          ),
          title: w.title,
          subtitle: w.subtitle ?? '',
          amount: w.balance,
          secondaryAmount: changeLabel,
          secondaryAmountColor: changeColor,
          onTap: () => _onWalletTap(w),
        );
      }).toList(),
    );
  }

  void _openArticle(ArticlePreview article) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => ArticleDetailScreen(slug: article.slug),
      ),
    );
  }

  void _goToProfile() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => const ProfileScreen(),
      ),
    );
  }

  void _goToNotificationCenter() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => const NotificationCenterScreen(),
      ),
    ).then((_) => _loadUnreadNotificationCount());
  }

  void _goToGlobalStatistics() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => const GlobalStatisticsScreen(),
      ),
    );
  }

  Future<void> _onLogoutPressed() async {
    await AuthLogout.confirmSignOutAndGoToWelcome(context);
  }

  static const List<String> _periodOptions = [
    'All time',
    '1 year',
    '6 months',
    '1 month',
    '1 week',
    '24 hours',
  ];

  void _openPeriodModal() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => _PeriodSelectionSheet(
        options: _periodOptions,
        selectedLabel: _selectedPeriodLabel,
        onSelect: (label) {
          setState(() => _selectedPeriodLabel = label);
          Navigator.of(context).pop();
        },
      ),
    );
  }

  void _openDepositModal() {
    Modale.show<void>(
      context,
      ModaleParams(
        title: 'Comment souhaitez-vous déposer de l\'argent sur votre application Vancelian?',
        rows: <ModaleListRow>[
          ModaleListRow(
            label: 'Par virement bancaire',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const DepositVirementScreen(),
                ),
              );
            },
          ),
          ModaleListRow(
            label: 'Par carte bancaire',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const DepositCarteScreen(),
                ),
              );
            },
          ),
          ModaleListRow(
            label: 'Par transfert crypto',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const DepositCryptoScreen(),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Future<void> _openPrivyCreateWallet() async {
    if (!mounted) return;
    if (!SecureApiConfig.hasAuthBackend) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'API d’authentification non configurée (AUTH_API_BASE_URL).',
          ),
        ),
      );
      return;
    }
    try {
      final existing =
          await PrivyIdentityBridgeService.instance.fetchAuthenticatedPersonCryptoWallets();
      if (!mounted) return;
      if (existing.isNotEmpty) {
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => const DepositCryptoScreen(),
          ),
        );
        return;
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Impossible de vérifier si un wallet existe déjà. Réessayez dans quelques instants.',
          ),
        ),
      );
      return;
    }
    if (!PrivyDartDefines.isConfigured ||
        !PrivyDartDefines.isOAuthRedirectConfigured) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text(
              'Privy non configuré : PRIVY_APP_ID, PRIVY_APP_CLIENT_ID '
              '(et scheme OAuth natif pour le SDK). Voir .env.flutter.',
            ),
        ),
      );
      return;
    }
    final created = await openPrivyWalletEmailCreationFlow(context);
    if (created && mounted) {
      await _loadPersonCryptoWalletsSnapshot();
    }
  }

  void _onActivationTargetRoute(String route) {
    final stepKey = activationStepKeyForTargetRoute(route);
    if (stepKey != null) {
      ActivationJourneyFunnelEvents.stepClicked(
        stepKey: stepKey,
        targetRoute: route,
      );
    }
    switch (route) {
      case 'registration_resume':
        _openRegistrationResume();
        break;
      case 'deposit':
        _openDepositModal();
        break;
      case 'invest_crypto':
        Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => const OffersScreen(),
          ),
        );
        break;
      default:
        break;
    }
  }

  Widget _buildActivationHomeSection() {
    final cached = ProfileIdentityCoordinator.instance.cachedProfile;
    final aj = cached?.activationJourney;
    if (aj != null && aj.showModule) {
      return ActivationJourneyExposure(
        journey: aj,
        child: ActivationJourneyHomeModule(
          journey: aj,
          compact: true,
          onTargetRoute: _onActivationTargetRoute,
        ),
      );
    }
    if (_registrationModuleLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 24),
          child: CircularProgressIndicator(
            color: AppColors.indigo,
          ),
        ),
      );
    }
    if (_registrationModuleError != null) {
      return _buildRegistrationModuleErrorBanner();
    }
    if (_registrationModuleData != null) {
      return RegistrationProgressModule(
        data: _registrationModuleData!,
        onContinue: _openRegistrationResume,
      );
    }
    return const SizedBox.shrink();
  }

  /// Bandeau « Compte activé » après les 3 étapes (API v3 : `activation_complete` + `completion_message`).
  bool _showActivationCompletionStrip() {
    final aj = ProfileIdentityCoordinator.instance.cachedProfile?.activationJourney;
    final msg = aj?.completionMessage?.trim();
    return aj != null &&
        !aj.showModule &&
        aj.activationComplete &&
        msg != null &&
        msg.isNotEmpty;
  }

  Widget _buildActivationCompletionStrip() {
    final msg = ProfileIdentityCoordinator.instance.cachedProfile?.activationJourney
            ?.completionMessage
            ?.trim() ??
        '';
    if (msg.isEmpty) return const SizedBox.shrink();
    return ActivationJourneyCompletionStrip(message: msg);
  }

  Map<String, dynamic>? _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    return null;
  }

  List<Map<String, dynamic>> _asMapList(dynamic value) {
    if (value is! List) return const [];
    return value.whereType<Map<String, dynamic>>().toList();
  }

  List<String> _asStringList(dynamic value) {
    if (value is! List) return const [];
    return value.map((e) => e.toString()).toList();
  }

  Map<String, dynamic>? get _layoutStructure => _asMap(_dashboardLayout?['structure']);
  Map<String, dynamic>? get _navbarConfig => _asMap(_layoutStructure?['navbar']);
  Map<String, dynamic>? get _headerConfig => _asMap(_layoutStructure?['header']);

  List<String> get _headerElements {
    final raw = _headerConfig?['elements'];
    if (raw is! List) return const [];
    return raw.map((e) => e.toString()).toList();
  }

  Map<String, dynamic>? get _headerBackgroundConfig => _asMap(_headerConfig?['background']);

  Color? _parseHexColor(String? raw) {
    if (raw == null) return null;
    final value = raw.trim();
    if (value.isEmpty) return null;
    var hex = value.startsWith('#') ? value.substring(1) : value;
    if (hex.length == 6) hex = 'FF$hex';
    if (hex.length != 8) return null;
    final parsed = int.tryParse(hex, radix: 16);
    if (parsed == null) return null;
    return Color(parsed);
  }



  Color? get _headerBackgroundColor {
    final bg = _headerBackgroundConfig;
    if (bg == null) return null;
    final direct = _parseHexColor((bg['color'] ?? bg['backgroundColor'])?.toString());
    if (direct != null) return direct;
    final overlay = _asMap(bg['overlay']);
    return _parseHexColor(overlay?['color']?.toString());
  }


  List<Map<String, dynamic>> get _bodyWidgetConfigs {
    final body = _asMap(_layoutStructure?['body']);
    return _asMapList(body?['widgets']);
  }

  bool _navbarHasElement(String key) {
    final left = _asStringList(_navbarConfig?['left']);
    final right = _asStringList(_navbarConfig?['right']);
    final flat = _asStringList(_navbarConfig?['elements']);

    final hasConfiguredElements = left.isNotEmpty || right.isNotEmpty || flat.isNotEmpty;
    if (!hasConfiguredElements) return true;
    return left.contains(key) || right.contains(key) || flat.contains(key);
  }

  List<dynamic> get _headerActionButtonsRaw {
    final header = _asMap(_layoutStructure?['header']);
    final raw = header?['action_buttons'];
    if (raw is List) return raw;
    return const [];
  }

  bool _matchWidget(
    Map<String, dynamic> config, {
    required List<String> keys,
    required List<String> types,
  }) {
    final key = (config['key'] ?? '').toString();
    final type = (config['type'] ?? '').toString();
    return keys.contains(key) || types.contains(type);
  }

  /// Widget Builder — feed `top10news` (Vancelian News). Filtre par slug pour ne pas
  /// confondre avec d'autres `widget_builder_widget`.
  bool _configIsTop10NewsWidget(Map<String, dynamic> config) {
    final slug = (config['widgetSlug'] ?? config['slug'] ?? '').toString().trim();
    return slug == 'top10news';
  }

  static const String _vancelianNewsFeedTitle = 'Vancelian News';

  VoidCallback? _callbackForHeaderAction(String key) {
    switch (key) {
      case 'deposit':
        return _openDepositModal;
      case 'send':
      case 'withdraw':
      case 'transfer':
        return () {};
      case 'buy':
      case 'invest':
        return () {};
      case 'more':
        return () => unawaited(_openPrivyCreateWallet());
      default:
        return () {};
    }
  }

  IconData _iconForHeaderAction(String key) {
    switch (key) {
      case 'deposit':
        return Icons.add;
      case 'send':
      case 'withdraw':
        return Icons.arrow_forward_rounded;
      case 'buy':
      case 'invest':
      case 'transfer':
        return Icons.swap_horiz_rounded;
      case 'more':
        return Icons.account_balance_wallet_rounded;
      default:
        return Icons.more_horiz_rounded;
    }
  }

  String _labelForHeaderAction(String key) {
    switch (key) {
      case 'deposit':
        return 'Déposer';
      case 'send':
        return 'Envoyer';
      case 'withdraw':
        return 'Retirer';
      case 'transfer':
        return 'Investir';
      case 'buy':
      case 'invest':
        return 'Acheter';
      case 'more':
        return _heroMoreButtonLabel();
      default:
        return key;
    }
  }

  ({List<CircleButtonItem> items, List<VoidCallback?> callbacks}) _resolveHeaderActions({
    required bool isDarkHeader,
  }) {
    if (_headerActionButtonsRaw.isEmpty) {
      final items = [
        CircleButtonItem(
          icon: Icons.add,
          label: 'Déposer',
          onTap: _openDepositModal,
          isPrimary: true,
        ),
        CircleButtonItem(
          icon: Icons.arrow_forward_rounded,
          label: 'Envoyer',
          onTap: () {},
        ),
        CircleButtonItem(
          icon: Icons.swap_horiz_rounded,
          label: 'Acheter',
          onTap: () {},
        ),
        CircleButtonItem(
          icon: Icons.account_balance_wallet_rounded,
          label: _heroMoreButtonLabel(),
          onTap: () => unawaited(_openPrivyCreateWallet()),
        ),
      ];
      return (items: items, callbacks: items.map((e) => e.onTap).toList());
    }

    final items = <CircleButtonItem>[];
    for (final raw in _headerActionButtonsRaw) {
      if (raw is String) {
        final key = raw.trim().toLowerCase();
        if (key.isEmpty) continue;
        items.add(
          CircleButtonItem(
            icon: _iconForHeaderAction(key),
            label: _labelForHeaderAction(key),
            onTap: _callbackForHeaderAction(key),
            isPrimary: key == 'deposit',
          ),
        );
        continue;
      }

      if (raw is Map<String, dynamic>) {
        final key = (raw['key'] ?? raw['action'] ?? '').toString().trim().toLowerCase();
        if (key.isEmpty) continue;
        final label = (raw['label'] ?? '').toString().trim();
        items.add(
          CircleButtonItem(
            icon: _iconForHeaderAction(key),
            label: key == 'more'
                ? _heroMoreButtonLabel()
                : (label.isEmpty ? _labelForHeaderAction(key) : label),
            onTap: _callbackForHeaderAction(key),
            isPrimary: key == 'deposit',
          ),
        );
      }
    }

    if (items.isEmpty) {
      final fallback = [
        CircleButtonItem(
          icon: Icons.add,
          label: 'Déposer',
          onTap: _openDepositModal,
          isPrimary: true,
        ),
        CircleButtonItem(
          icon: Icons.arrow_forward_rounded,
          label: 'Envoyer',
          onTap: () {},
        ),
        CircleButtonItem(
          icon: Icons.swap_horiz_rounded,
          label: 'Acheter',
          onTap: () {},
        ),
        CircleButtonItem(
          icon: Icons.account_balance_wallet_rounded,
          label: _heroMoreButtonLabel(),
          onTap: () => unawaited(_openPrivyCreateWallet()),
        ),
      ];
      return (items: fallback, callbacks: fallback.map((e) => e.onTap).toList());
    }
    return (items: items, callbacks: items.map((e) => e.onTap).toList());
  }


  int _intFromDynamic(dynamic value, {required int fallback}) {
    if (value is int) return value;
    if (value is String) {
      final parsed = int.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
    return fallback;
  }

  MarketingCardsLayout _marketingLayoutFromConfig(Map<String, dynamic> config) {
    final raw = (config['layout'] ?? '').toString().toLowerCase();
    return raw == 'portrait'
        ? MarketingCardsLayout.portrait
        : MarketingCardsLayout.landscape;
  }

  MarketingCardsMode _marketingModeFromConfig(Map<String, dynamic> config) {
    final raw = (config['mode'] ?? '').toString().toLowerCase();
    return raw == 'carousel'
        ? MarketingCardsMode.carousel
        : MarketingCardsMode.sliding;
  }

  List<MarketingCardItemConfig> _marketingItemsFromConfig(
    Map<String, dynamic> config,
  ) {
    final rawItems = config['items'];
    if (rawItems is! List) return const [];

    final out = <MarketingCardItemConfig>[];
    for (final item in rawItems) {
      if (item is! Map<String, dynamic>) continue;
      final imageUrl = (item['imageUrl'] ?? '').toString();
      final redirectUrl = (item['redirectUrl'] ?? '').toString();
      if (imageUrl.isEmpty || redirectUrl.isEmpty) continue;
      out.add(
        MarketingCardItemConfig(
          imageUrl: imageUrl,
          redirectUrl: redirectUrl,
          title: (item['title'] ?? '').toString().isEmpty
              ? null
              : (item['title'] ?? '').toString(),
          description: (item['description'] ?? '').toString().isEmpty
              ? null
              : (item['description'] ?? '').toString(),
          logoLabel: (item['logoLabel'] ?? '').toString().isEmpty
              ? null
              : (item['logoLabel'] ?? '').toString(),
          buttonLabel: (item['buttonLabel'] ?? '').toString().isEmpty
              ? null
              : (item['buttonLabel'] ?? '').toString(),
        ),
      );
    }
    return out;
  }

  Future<void> _openMarketingRedirect(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final hasHeaderConfig = _headerElements.isNotEmpty;
    final showLineChart = hasHeaderConfig ? _headerElements.contains('line_chart') : true;
    final showActionButtons = hasHeaderConfig ? _headerElements.contains('action_buttons') : true;
    final showProfileInNavbar = _navbarHasElement('profile');
    final showStatisticsInNavbar = _navbarHasElement('statistics');
    final showNotificationsInNavbar = _navbarHasElement('notifications');
    final hasDbBodyWidgets = _bodyWidgetConfigs.isNotEmpty;
    final isDarkHeader = _headerTheme == WalletHeaderTheme.dark;
    final profileForHeader = ProfileIdentityCoordinator.instance.cachedProfile;
    final ajForHeader = profileForHeader?.activationJourney;
    final hasEuroAccount = hasEuroCashAccount(_cashData);
    final basePreDepositActivationHeader = profileForHeader != null &&
        shouldShowActivationModuleCard(profileForHeader) &&
        ajForHeader != null;
    final usePreDepositActivationHeader = shouldUsePreDepositActivationHeader(
      basePreDepositConditionsMet: basePreDepositActivationHeader,
      profile: profileForHeader,
      cash: _cashData,
    );
    if (kDebugMode) {
      final orchestration = resolveHomeDashboardOrchestrationMode(
        usePreDepositActivationHeader: usePreDepositActivationHeader,
      );
      debugPrint(
        '[HomeScreen][dashboard] isPartialRegistration='
        '${isPartialRegistrationClientStatus(profileForHeader)} '
        'hasEuroAccount=$hasEuroAccount '
        'dashboardMode=$orchestration',
      );
    }
    final resolvedHeaderActions = _resolveHeaderActions(isDarkHeader: isDarkHeader);

    final navActions = <AppTopNavBarAction>[
      if (showStatisticsInNavbar)
        AppTopNavBarAction(
          icon: Icons.bar_chart_rounded,
          onPressed: _goToGlobalStatistics,
        ),
      if (showNotificationsInNavbar)
        AppTopNavBarAction(
          icon: Icons.notifications_outlined,
          onPressed: _goToNotificationCenter,
          showDot: _unreadNotificationCount > 0,
        ),
      AppTopNavBarAction(
        icon: Icons.logout_rounded,
        onPressed: _onLogoutPressed,
        iconColor: Colors.white,
      ),
    ];

    final heroFullBleedWidget = showLineChart
        ? LineChartModule(
            data: _heroChartData,
            height: 80,
            strokeWidth: 3,
            lineColor: Colors.white,
            paddingTop: 8,
            paddingBottom: 8,
          )
        : null;

    final perfLabel = _heroPerformancePct >= 0
        ? '+${_heroPerformancePct.toStringAsFixed(2)}%'
        : '${_heroPerformancePct.toStringAsFixed(2)}%';
    final heroActionsWidget = GestureDetector(
      onTap: _openPeriodModal,
      child: GlassBadge(
        text: '$perfLabel · $_selectedPeriodLabel',
        opacity: GlassBadgeOpacity.light,
      ),
    );

    final heroActionsBelowWidget = showActionButtons
        ? CircleButtonRow(items: resolvedHeaderActions.items)
        : null;

    final cachedProfile = ProfileIdentityCoordinator.instance.cachedProfile;
    final showMyAccountsCardHere = !hasDbBodyWidgets &&
        shouldShowMyAccountsCard(
          cachedProfile,
          hasEuroCashAccount: hasEuroAccount,
        );
    final prioritizeMyAccountsWithPartialEuro =
        isPartialRegistrationClientStatus(cachedProfile) &&
            hasEuroAccount &&
            _showActivationModule &&
            !hasDbBodyWidgets &&
            showMyAccountsCardHere;

    final contentList = <Widget>[
      if (prioritizeMyAccountsWithPartialEuro) ...[
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
          ),
          child: _buildAccountsCard(),
        ),
        Padding(
          padding: const EdgeInsets.only(
            bottom: DashboardLayoutConstants.moduleGap,
            left: DashboardLayoutConstants.moduleHorizontalMargin,
            right: DashboardLayoutConstants.moduleHorizontalMargin,
          ),
          child: _buildActivationHomeSection(),
        ),
      ] else ...[
        if (_showActivationModule)
          Padding(
            padding: const EdgeInsets.only(
              bottom: DashboardLayoutConstants.moduleGap,
              left: DashboardLayoutConstants.moduleHorizontalMargin,
              right: DashboardLayoutConstants.moduleHorizontalMargin,
            ),
            child: _buildActivationHomeSection(),
          ),
      ],
      if (!_showActivationModule && _showActivationCompletionStrip())
        Padding(
          padding: const EdgeInsets.only(
            bottom: DashboardLayoutConstants.moduleGap,
            left: DashboardLayoutConstants.moduleHorizontalMargin,
            right: DashboardLayoutConstants.moduleHorizontalMargin,
          ),
          child: _buildActivationCompletionStrip(),
        ),
      if (!prioritizeMyAccountsWithPartialEuro && showMyAccountsCardHere)
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
          ),
          child: _buildAccountsCard(),
        ),
      _buildContentBelowSheet(),
    ];

    return ListenableBuilder(
      listenable: ProfileLeadingPreference.instance,
      builder: (context, _) {
        if (usePreDepositActivationHeader) {
          // `usePreDepositActivationHeader` implique profil + journey non null (voir basePreDepositActivationHeader).
          final profile = profileForHeader!;
          final journey = ajForHeader!;
          final isPartialRegistration =
              (profile.clientStatus ?? '').toUpperCase() == 'PARTIAL';
          final ctaLabel = journey.primaryCtaLabel?.trim() ?? '';
          final route = effectiveActivationPrimaryRoute(
                journey,
                profile,
              )?.trim() ??
              '';
          return LayoutPageLevel1(
            heroBackground: activationPreDepositHeroBackground(),
            heroHeightFraction: 0.62,
            heroMinHeight: 520,
            heroFallbackColor: const Color(0xFF0D1B2A),
            heroOverlay: HeroOverlayConfig.none,
            title: '',
            subtitle: null,
            heroActionsAlignEnd: true,
            heroActions: activationPreDepositHeroActionsColumn(
              context: context,
              useRegistrationPartialVaultAsset: isPartialRegistration,
              apiHeroImageUrl: journey.heroImageUrl,
              ctaLabel: ctaLabel.isNotEmpty ? ctaLabel : null,
              onCtaPressed: route.isNotEmpty
                  ? () => _onActivationTargetRoute(route)
                  : null,
            ),
            showChart: false,
            heroActionsBelowFullBleed: null,
            leadingType: showProfileInNavbar
                ? AppTopNavBarLeading.profile
                : AppTopNavBarLeading.back,
            onLeadingTap: showProfileInNavbar
                ? _goToProfile
                : () => Navigator.of(context).pop(),
            navBarActions: navActions,
            navBarForegroundColor: Colors.white,
            profileInitials: ProfileLeadingPreference.instance.initials,
            content: contentList,
            onRefresh: () => _loadAll(
                  forceLayoutRefresh: true,
                  refreshVancelianNews: true,
                ),
          );
        }

        return LayoutPageLevel1(
          heroHeightFraction: 0.65,
          heroBackground: activationPreDepositHeroBackground(),
          heroFallbackColor: const Color(0xFF0D1B2A),
          heroOverlay: HeroOverlayConfig.none,
          title: 'Balance',
          subtitle: _headerBalanceSubtitle,
          subtitleStyle: AppTypography.amountPrimary.copyWith(
            color: Colors.white,
          ),
          heroFullBleed: heroFullBleedWidget,
          showChart: showLineChart,
          heroActions: heroActionsWidget,
          heroActionsBelowFullBleed: heroActionsBelowWidget,
          leadingType: showProfileInNavbar
              ? AppTopNavBarLeading.profile
              : AppTopNavBarLeading.back,
          onLeadingTap: showProfileInNavbar ? _goToProfile : () => Navigator.of(context).pop(),
          navBarActions: navActions,
          navBarForegroundColor: Colors.white,
          profileInitials: ProfileLeadingPreference.instance.initials,
          content: contentList,
          onRefresh: () => _loadAll(
                forceLayoutRefresh: true,
                refreshVancelianNews: true,
              ),
        );
      },
    );
  }

  /// Contenu sous la carte blanche (My account → Offres et récompenses). Pas de marge horizontale (pleine largeur).
  Widget _buildContentBelowSheet() {
    if (_loading && _latestNews.isEmpty) {
      return Padding(
        padding: const EdgeInsets.only(top: DashboardLayoutConstants.moduleGap),
        child: VancelianNewsModuleSkeleton(
          title: _vancelianNewsFeedTitle,
          cardCount: 2,
        ),
      );
    }
    if (_error != null && _latestNews.isEmpty) {
      return Padding(
        padding: const EdgeInsets.only(top: DashboardLayoutConstants.moduleGap),
        child: _buildError(),
      );
    }
    final hasDbBodyWidgets = _bodyWidgetConfigs.isNotEmpty;
    final bodyModules = hasDbBodyWidgets
        ? _buildModulesFromDashboardLayout()
        : _buildLegacyModules();
    final topPadding = hasDbBodyWidgets ? 0.0 : DashboardLayoutConstants.moduleGap;
    final bottomInset = BottomNavContentInset.level1(context);
    return Padding(
      padding: EdgeInsets.only(top: topPadding, bottom: bottomInset),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: bodyModules,
      ),
    );
  }

  List<Widget> _buildLegacyModules() {
    return [
      VaultsMarketingCardsFeed(
        widgetSlug: 'top10news',
        title: _vancelianNewsFeedTitle,
        refreshNonce: _vancelianNewsRefreshNonce,
      ),
      const SizedBox(height: DashboardLayoutConstants.moduleGap),
    ];
  }

  List<Widget> _buildModulesFromDashboardLayout() {
    final widgets = <Widget>[];
    var addedTop10NewsFromLayout = false;

    for (final config in _bodyWidgetConfigs) {
      final title = (config['title'] ?? '').toString();

      if (_matchWidget(
        config,
        keys: const ['my_account'],
        types: const ['account_summary_widget'],
      )) {
        if (shouldShowMyAccountsCard(
          ProfileIdentityCoordinator.instance.cachedProfile,
          hasEuroCashAccount: hasEuroCashAccount(_cashData),
        )) {
          widgets.add(
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
              ),
              child: _buildAccountsCard(),
            ),
          );
          widgets.add(const SizedBox(height: DashboardLayoutConstants.moduleGap));
        }
        continue;
      }

      if (_matchWidget(
        config,
        keys: const ['marketing_cards', 'marketing_cards_landscape'],
        types: const ['marketing_cards_widget'],
      )) {
        final marketingItems = _marketingItemsFromConfig(config);
        if (marketingItems.isNotEmpty) {
          widgets.add(
            MarketingCardsModule(
              title: title.isNotEmpty ? title : 'Marketing cards',
              layout: _marketingLayoutFromConfig(config),
              mode: _marketingModeFromConfig(config),
              items: marketingItems,
              onRedirect: (url) {
                _openMarketingRedirect(url);
              },
            ),
          );
          widgets.add(const SizedBox(height: DashboardLayoutConstants.moduleGap));
        }
        continue;
      }

      if (_configIsTop10NewsWidget(config)) {
        final widgetSlug = (config['widgetSlug'] ?? config['slug'] ?? '').toString().trim();
        if (widgetSlug.isNotEmpty) {
          widgets.add(
            VaultsMarketingCardsFeed(
              widgetSlug: widgetSlug,
              title: title.isNotEmpty ? title : _vancelianNewsFeedTitle,
              refreshNonce: _vancelianNewsRefreshNonce,
            ),
          );
          widgets.add(const SizedBox(height: DashboardLayoutConstants.moduleGap));
          addedTop10NewsFromLayout = true;
        }
        continue;
      }


    }

    if (widgets.isEmpty) {
      return _buildLegacyModules();
    }
    if (!addedTop10NewsFromLayout) {
      widgets.add(
        VaultsMarketingCardsFeed(
          widgetSlug: 'top10news',
          title: _vancelianNewsFeedTitle,
          refreshNonce: _vancelianNewsRefreshNonce,
        ),
      );
      widgets.add(const SizedBox(height: DashboardLayoutConstants.moduleGap));
    }
    return widgets;
  }

  Widget _buildError() {
    return Center(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.grey[600]),
              const SizedBox(height: 16),
              Text(
                _errorMessage(),
                style: AppTypography.paragraph.copyWith(fontSize: 14, color: Colors.grey[700]),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _loadFeed,
                icon: const Icon(Icons.refresh, size: 20),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _errorMessage() {
    final e = _error ?? 'Erreur';
    if (e.contains('404')) {
      return 'API non disponible (404).\n\nVérifiez que le serveur tourne.';
    }
    final noHtml = e
        .replaceAll(RegExp(r'<[^>]*>'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    return noHtml.length > 300 ? '${noHtml.substring(0, 300)}…' : noHtml;
  }
}

class _DashboardLifecycleObserver with WidgetsBindingObserver {
  _DashboardLifecycleObserver({required this.onAppResumed});

  final VoidCallback onAppResumed;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      onAppResumed();
    }
  }
}

/// Modale de sélection de période (performance / chart) : liste avec coche sur l’élément sélectionné.
class _PeriodSelectionSheet extends StatelessWidget {
  const _PeriodSelectionSheet({
    required this.options,
    required this.selectedLabel,
    required this.onSelect,
  });

  final List<String> options;
  final String selectedLabel;
  final void Function(String label) onSelect;

  @override
  Widget build(BuildContext context) {
    final maxHeight = MediaQuery.sizeOf(context).height * 0.75;
    return Container(
      constraints: BoxConstraints(maxHeight: maxHeight),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.max,
          children: [
            const SizedBox(height: 12),
            Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 20),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: DashboardLayoutConstants.moduleHorizontalMargin),
              child: Text(
                'Choisissez une période pour visualiser vos performances historiques',
                style: AppTypography.modalTitle,
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 24),
            Flexible(
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: options
                      .map(
                        (label) => Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () => onSelect(label),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                                vertical: 16,
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      label,
                                      style: AppTypography.titleSmall.copyWith(
                                        color: AppColors.textPrimary,
                                      ),
                                    ),
                                  ),
                                  if (label == selectedLabel)
                                    Icon(
                                      Icons.check,
                                      color: AppColors.accent,
                                      size: 22,
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.paddingOf(context).bottom + 8),
          ],
        ),
      ),
    );
  }
}

