import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../core/currency_formatter.dart';
import '../../../../design_system/design_system.dart';
import '../../../markets/data/market_data_api.dart';
import '../../../markets/data/market_data_ws_service.dart';
import '../../../markets/data/market_display_utils.dart';
import '../../../markets/presentation/widgets/chart_asset_module.dart';
import '../../../markets/presentation/widgets/top_crypto_assets_module.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Carte « instrument » embarquée dans une bulle assistant — Phase 2c.6
/// (refonte v2 : alignement strict sur le hero `LayoutPageInstrumentDetail`).
///
/// L'agent `product` (ou `advisor`) déclenche un embed
/// `instrument_detail_card` via le tool `show_instrument_card`. Le
/// serveur envoie au client :
///
///   - `symbol` (ex. `BTC`) + `name` (ex. `Bitcoin`) + `logo_url`
///     (`/media/...`)
///   - `currency` (`EUR` ou fallback `USD`) + `price`
///   - `change_24h_abs` + `change_24h_pct` (peuvent être `null`)
///   - `sparkline_24h` : liste de `double` (closes 5 min sur 24 h) — utilisé
///     uniquement comme fallback initial avant que `getChartHistory`
///     remonte les vraies bougies.
///   - `actions` : 2 deep-links whitelistés `buy_instrument` +
///     `sell_instrument` (cf. `action_cta_catalog`).
///
/// Différence clé avec [TransactionDetailEmbed] et
/// [PortfolioAllocationDonutEmbed] : ici le LLM peut **écrire un
/// texte explicatif en plus** de la carte (ex. *« Bitcoin est la
/// première cryptomonnaie… »*). La carte joue le rôle de **fiche
/// factuelle complémentaire**, pas de réponse exclusive.
///
/// Refonte 2026-05-04 : on charge les vraies bougies via
/// [MarketDataApi.getChartHistory] et on délègue le rendu chart à
/// [ChartAssetModule] en mode `instrumentDetailStyle: true` — aligné
/// sur le hero détail instrument ([CryptoDetailScreen]) :
///   - tag « Crypto » au-dessus du titre (fond gris page pour contraste
///     sur la coque blanche),
///   - avatar [CryptoAvatar] (résolu via `Config.resolveLogoUrl`,
///     fallback SVG bundled puis logo réseau puis icône),
///   - ligne de perf (puces gris page) puis montant principal, comme
///     espacement visuel vs fond blanc,
///   - CTAs Acheter / Vendre **entre** le bloc titre/perfs/prix et le chart
///     (identique à [LayoutPageInstrumentDetail]),
///   - line chart bord à bord + onglets période inversés (capsule grise,
///     segment actif blanc),
///   - disclaimer mid-rate sous le chart.
///
/// La coque reste un **module blanc** bulle assistant (ombre carte)
/// plutôt que la pleine largeur sur fond gris écran.
class InstrumentDetailCardEmbed extends StatefulWidget {
  const InstrumentDetailCardEmbed({
    super.key,
    required this.symbol,
    required this.name,
    required this.currency,
    required this.price,
    required this.actions,
    this.logoUrl,
    this.change24hAbs,
    this.change24hPct,
    this.sparkline = const [],
  });

  final String symbol;
  final String name;
  final String currency;
  final double price;
  final List<AssistanceChoiceOption> actions;
  final String? logoUrl;
  final double? change24hAbs;
  final double? change24hPct;

  /// Sparkline 24h fournie par le backend, conservée pour l'affichage
  /// initial (avant que les bougies arrivent depuis l'API).
  final List<double> sparkline;

  @override
  State<InstrumentDetailCardEmbed> createState() =>
      _InstrumentDetailCardEmbedState();
}

class _InstrumentDetailCardEmbedState extends State<InstrumentDetailCardEmbed> {
  final MarketDataApi _api = MarketDataApi();
  final MarketDataWsService _ws = MarketDataWsService();

  static const List<String> _periodKeys = ['1j', '1s', '1m', '1a', '5a'];
  static const List<String> _periodLabels = [
    '1 jour',
    '1 semaine',
    '1 mois',
    '1 an',
    '5 ans',
  ];

  int _timeframeIndex = 0;
  int _displayTimeframeIndex = 0;
  bool _isLineChart = true;
  List<CandleItem> _candles = const [];
  bool _candlesLoading = true;
  String? _candlesError;

  /// Prix live USD reçu par WebSocket Binance (ticker stream). Prime
  /// sur le dernier close des bougies pour l'affichage prix + perf.
  double? _livePriceUsd;

  String get _providerSymbol => tickerToProviderSymbol(widget.symbol);

  @override
  void initState() {
    super.initState();
    _loadCandles(initial: true);
    _subscribeWs();
  }

  @override
  void dispose() {
    _ws.disconnect();
    super.dispose();
  }

  void _subscribeWs() {
    _ws.subscribe([_providerSymbol], _onWsQuotes);
  }

  void _onWsQuotes(List<QuoteUpdate> updates) {
    if (updates.isEmpty || !mounted) return;
    for (final u in updates) {
      if (u.symbol == _providerSymbol) {
        setState(() => _livePriceUsd = u.price);
        break;
      }
    }
  }

  Future<void> _loadCandles({bool initial = false}) async {
    final requested = _timeframeIndex;
    if (initial) {
      setState(() {
        _candlesLoading = true;
        _candlesError = null;
      });
    } else {
      setState(() {
        _candlesLoading = true;
        _candlesError = null;
      });
    }
    try {
      final period = _periodKeys[requested.clamp(0, _periodKeys.length - 1)];
      final list = await _api.getChartHistory(
        symbol: _providerSymbol,
        period: period,
      );
      if (!mounted) return;
      if (requested != _timeframeIndex) return;
      setState(() {
        _candles = list;
        _candlesLoading = false;
        _displayTimeframeIndex = _timeframeIndex;
      });
    } catch (e) {
      if (!mounted) return;
      if (requested != _timeframeIndex) return;
      setState(() {
        _candlesLoading = false;
        _candlesError = _userFriendlyError(e);
      });
    }
  }

  static String _userFriendlyError(Object e) {
    if (e is MarketDataApiException) {
      if (e.statusCode == 401) {
        return 'Données indisponibles (connexion requise).';
      }
      if (e.statusCode >= 500) {
        return 'Service temporairement indisponible.';
      }
      if (e.statusCode >= 400) {
        return 'Impossible de charger les données.';
      }
    }
    return 'Une erreur est survenue.';
  }

  /// Dernier prix connu en USD : priorité au tick WS live, fallback
  /// sur le dernier close des bougies (donne un prix avant que le WS
  /// ne pousse son premier tick).
  double? get _currentPriceUsd {
    if (_livePriceUsd != null) return _livePriceUsd;
    if (_candles.isEmpty) return null;
    return _candles.last.close;
  }

  /// Prix d'ouverture de la période (= premier close des bougies). Sert
  /// à calculer la perf période et à positionner la ligne horizontale
  /// + puce dans le chart.
  double? get _entryPriceUsd {
    if (_candles.isEmpty) return null;
    return _candles.first.close;
  }

  ({double absUsd, double pct})? get _periodPerformanceUsd {
    final entry = _entryPriceUsd;
    final current = _currentPriceUsd;
    if (entry == null || current == null || entry <= 0) return null;
    final abs = current - entry;
    final pct = abs / entry * 100;
    return (absUsd: abs, pct: pct);
  }

  String get _periodLabelDisplayed {
    var i = _displayTimeframeIndex;
    if (i < 0) i = 0;
    if (i >= _periodLabels.length) i = _periodLabels.length - 1;
    return _periodLabels[i];
  }

  String get _displayPriceText {
    final usd = _currentPriceUsd;
    if (usd != null) return CurrencyFormatter.priceUsd(usd);
    // Fallback : prix initial fourni par le backend (peut être EUR).
    final symbol = _currencySymbol(widget.currency);
    final formatted = formatPrice(widget.price);
    if (widget.currency.toUpperCase() == 'EUR') {
      return '$formatted $symbol';
    }
    return '$formatted $symbol';
  }

  static String _currencySymbol(String currency) {
    switch (currency.toUpperCase()) {
      case 'EUR':
        return '€';
      case 'GBP':
        return '£';
      case 'USD':
      default:
        return r'$';
    }
  }

  /// Ligne de performance — calculée sur la période **affichée** (cohérente
  /// avec les bougies en cours). Fallback sur les valeurs 24h envoyées
  /// par le backend tant que les bougies ne sont pas chargées.
  Widget? _buildPerformanceRow() {
    final period = _periodPerformanceUsd;
    if (period != null) {
      final isPositive = period.absUsd >= 0;
      final perfColor = isPositive
          ? AppColors.semanticPositive
          : AppColors.semanticNegative;
      final sign = isPositive ? '+' : '-';
      return InstrumentDetailHeroPerformanceRow(
        absChipText:
            '$sign${CurrencyFormatter.priceUsdRaw(period.absUsd.abs())} \$',
        percentChipText:
            '$sign${period.pct.abs().toStringAsFixed(2)} %',
        periodLabel: _periodLabelDisplayed,
        absChipColor: instrumentHeroAbsChipColor(
          changeAbs: period.absUsd,
          changePct: period.pct,
          perfColor: perfColor,
        ),
        percentColor: perfColor,
        percentIsPositive: isPositive,
        chipSurfaceColor: AppColors.pageBackground,
      );
    }
    // Fallback initial sur les valeurs 24 h fournies par le backend.
    final pct = widget.change24hPct;
    final abs = widget.change24hAbs;
    if (pct == null && abs == null) return null;
    final isPositive = (pct ?? 0) >= 0;
    final perfColor = isPositive
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
    final sign = isPositive ? '+' : '-';
    final pctText = pct != null
        ? '$sign${pct.abs().toStringAsFixed(2)} %'
        : '—';
    final symbolDisplay = _currencySymbol(widget.currency);
    final absText = abs != null
        ? '$sign${formatPrice(abs.abs())} $symbolDisplay'
        : null;
    return InstrumentDetailHeroPerformanceRow(
      absChipText: absText,
      percentChipText: pctText,
      periodLabel: '1 jour',
      absChipColor: instrumentHeroAbsChipColor(
        changeAbs: abs,
        changePct: pct,
        perfColor: perfColor,
      ),
      percentColor: perfColor,
      percentIsPositive: isPositive,
      chipSurfaceColor: AppColors.pageBackground,
    );
  }

  CryptoAssetItem _buildAssetItem() {
    return CryptoAssetItem(
      name: widget.name,
      ticker: widget.symbol.toUpperCase(),
      price: _displayPriceText,
      variationPercent: widget.change24hPct ?? 0,
      logoUrl: widget.logoUrl,
    );
  }

  Widget _buildHeader() {
    final logoUrl = Config.resolveLogoUrl(widget.logoUrl);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const CategoryBadge(
          label: 'Crypto',
          dotColor: AppColors.accent,
          surfaceColor: AppColors.pageBackground,
        ),
        const SizedBox(height: AppSpacing.s2),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            CryptoAvatar(
              ticker: widget.symbol.toUpperCase(),
              logoUrl: logoUrl,
              size: CryptoAvatarSize.small,
            ),
            const SizedBox(width: AppSpacing.s2),
            Expanded(
              child: Text(
                widget.name,
                style: AppTypography.headerTertiary.copyWith(
                  color: AppColors.textPrimary,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Builder(
          builder: (_) {
            final perf = _buildPerformanceRow();
            return perf ?? const SizedBox.shrink();
          },
        ),
        const SizedBox(height: AppSpacing.s2),
        Text(
          _displayPriceText,
          style: AppTypography.amountPrimary.copyWith(
            color: AppColors.textPrimary,
            inherit: false,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }

  Widget _buildChart(double containerWidth) {
    final asset = _buildAssetItem();
    return ChartAssetModule(
      asset: asset,
      displayPrice: _displayPriceText,
      instrumentDetailStyle: true,
      chartContainerWidth: containerWidth,
      currentPrice: _currentPriceUsd,
      change24hPct: widget.change24hPct,
      change24hAbs: widget.change24hAbs,
      periodLabel: _periodLabelDisplayed,
      candles: _candles.isEmpty ? null : _candles,
      chartLoading: _candlesLoading && _candles.isEmpty,
      chartError: _candlesError,
      selectedTimeframeIndex: _timeframeIndex,
      onTimeframeChanged: (index) {
        if (index != _timeframeIndex &&
            index >= 0 &&
            index < _periodKeys.length) {
          setState(() => _timeframeIndex = index);
          _loadCandles();
        }
      },
      onRefresh: () => _loadCandles(),
      isLineChart: _isLineChart,
      onChartTypeChanged: (isLine) {
        setState(() => _isLineChart = isLine);
      },
      invertedPeriodChips: true,
    );
  }

  Widget _buildCtas(BuildContext context) {
    final ctas = widget.actions
        .where((a) => a.hasDeepLink)
        .toList(growable: false);
    if (ctas.isEmpty) return const SizedBox.shrink();

    AssistanceChoiceOption? buy;
    AssistanceChoiceOption? sell;
    for (final a in ctas) {
      if (a.id == 'buy_instrument' && buy == null) {
        buy = a;
      } else if (a.id == 'sell_instrument' && sell == null) {
        sell = a;
      }
    }
    // Fallback : prendre les deux premières actions si les ids ne sont
    // pas reconnus (le backend reste autoritatif sur l'ordre).
    if (buy == null && sell == null) {
      if (ctas.isNotEmpty) buy = ctas[0];
      if (ctas.length >= 2) sell = ctas[1];
    }

    final children = <Widget>[];
    if (buy != null) {
      children.add(
        AppPrimaryButton(
          label: buy.label,
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.primary,
          horizontalPadding: AppSpacing.s4,
          leading: const Icon(Icons.arrow_upward, size: 20),
          onPressed: () => _onCtaTap(context, buy!),
        ),
      );
    }
    if (sell != null) {
      children.add(
        AppPrimaryButton(
          label: sell.label,
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.secondary,
          horizontalPadding: AppSpacing.s4,
          leading: const Icon(Icons.arrow_downward, size: 20),
          onPressed: () => _onCtaTap(context, sell!),
        ),
      );
    }
    return InstrumentDetailHeroCtaRow(children: children);
  }

  void _onCtaTap(BuildContext context, AssistanceChoiceOption action) {
    final link = action.deepLink;
    if (link == null || link.isEmpty) return;
    AssistanceDeepLinkResolver.resolve(context, link);
  }

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final containerWidth = constraints.maxWidth;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                ),
                child: _buildHeader(),
              ),
              const SizedBox(height: AppSpacing.lg + AppSpacing.s1),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                ),
                child: _buildCtas(context),
              ),
              const SizedBox(height: AppSpacing.sm),
              // Chart bord à bord du module (pas de padding horizontal).
              _buildChart(containerWidth),
            ],
          );
        },
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Card shell — coque blanche bulle assistant (radius bubble, shadow)
// ─────────────────────────────────────────────────────────────────────

/// Coque spécifique au card embed instrument : **pas de padding
/// horizontal** (le chart va bord à bord), padding vertical conservé.
/// Le header et les CTAs gèrent leur propre padding interne.
class _CardShell extends StatelessWidget {
  const _CardShell({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
      clipBehavior: Clip.antiAlias,
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.only(
          topLeft: Radius.zero,
          topRight: Radius.circular(AppRadius.bubble),
          bottomLeft: Radius.circular(AppRadius.bubble),
          bottomRight: Radius.circular(AppRadius.bubble),
        ),
        boxShadow: AppShadow.defaultShadowList,
      ),
      child: child,
    );
  }
}
