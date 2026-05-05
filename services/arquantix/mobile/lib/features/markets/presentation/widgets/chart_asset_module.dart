import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../design_system/design_system.dart';
import '../../../../ui/theme/app_typography.dart' as ui_typography;
import '../../data/market_data_api.dart';
import 'top_crypto_assets_module.dart';

/// Chart candle data is sourced from Binance USDT pairs.
/// We always display USD regardless of user's reference_currency
/// to avoid a visual mismatch between the data and the label.
const String _chartCurrencySymbol = '\$';

/// Supported timeframes for the asset detail chart. 1j/1s/1m/1a/5a backed by backend (5m, 1h, 4h, 1d, 1w candles).
enum AssetChartTimeframe {
  j1(0, '1j', '1 jour', true),
  s1(1, '1s', '1 semaine', true),
  m1(2, '1m', '1 mois', true),
  a1(3, '1a', '1 an', true),
  a5(4, '5a', '5 ans', true);

  const AssetChartTimeframe(this.chipIndex, this.label, this.periodCaption, this.supported);
  final int chipIndex;
  final String label;
  final String periodCaption;
  final bool supported;
}

/// Couleur de la courbe ligne : verte si la période affichée est haussière, rouge sinon.
/// Basée sur les chandelles courantes (recompute à chaque chargement / changement de période).
Color _lineTrendColorFromCandles(List<CandleItem> candleList) {
  if (candleList.length >= 2) {
    final a = candleList.first.close;
    final b = candleList.last.close;
    return instrumentDetailLineTrendColorFromEndpoints(a, b);
  }
  if (candleList.length == 1) {
    final c = candleList.first;
    return c.close >= c.open
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
  }
  return AppColors.chartLine;
}

/// Couleur de tendance de la courbe (vert / rouge), alignée sur le détail instrument.
Color instrumentDetailLineTrendColorFromEndpoints(double first, double last) {
  return last >= first ? AppColors.semanticPositive : AppColors.semanticNegative;
}

/// Chart card for asset detail: price block + line/candlestick toggle + timeframe chips (1j/1s/1m/1a) + chart.
/// Candles and loading/error are owned by the parent; this widget is presentational.
/// [onRefresh] relance le chargement des chandelles pour la période courante.
class ChartAssetModule extends StatelessWidget {
  const ChartAssetModule({
    super.key,
    required this.asset,
    required this.displayPrice,
    this.currentPrice,
    this.change24hPct,
    this.change24hAbs,
    this.periodLabel = '1 jour',
    this.candles,
    this.chartLoading = false,
    this.chartError,
    this.selectedTimeframeIndex = 0,
    this.onTimeframeChanged,
    this.onRefresh,
    this.isLineChart = true,
    this.onChartTypeChanged,
    /// Si true : pas de carte blanche, pas de bloc prix (affiché dans le header),
    /// graphique bord à bord sur le fond page.
    this.instrumentDetailStyle = false,
    /// Largeur de référence pour dimensionner le chart (override de
    /// `MediaQuery.sizeOf(context).width`). Utilisé quand le module est
    /// embarqué dans un container plus petit que l'écran (ex. bulle chat
    /// `InstrumentDetailCardEmbed`). Null = comportement actuel = full
    /// width écran (page détail instrument).
    this.chartContainerWidth,
    /// Capsule des périodes en gris page, segment sélectionné blanc (contraste sur fond carte blanche).
    this.invertedPeriodChips = false,
  });

  final CryptoAssetItem asset;
  final String displayPrice;
  /// Prix temps réel (pour calcul performance période = current - premier candle close).
  final double? currentPrice;
  final double? change24hPct;
  final double? change24hAbs;
  final String periodLabel;
  final List<CandleItem>? candles;
  final bool chartLoading;
  final String? chartError;
  final int selectedTimeframeIndex;
  final void Function(int index)? onTimeframeChanged;
  final VoidCallback? onRefresh;
  /// true = courbe ligne, false = chandeliers.
  final bool isLineChart;
  /// Appelé avec true (ligne) ou false (chandeliers) quand l’utilisateur change le type.
  final void Function(bool isLineChart)? onChartTypeChanged;

  /// Variante [LayoutPageInstrumentDetail] : surface transparente, sans doublon de prix.
  final bool instrumentDetailStyle;

  /// Override optionnel de la largeur de référence du chart (cf.
  /// constructeur). Null = `MediaQuery.sizeOf(context).width`.
  final double? chartContainerWidth;

  /// Voir [ChartAssetModule.invertedPeriodChips] (constructeur).
  final bool invertedPeriodChips;

  static const double _chartVerticalSafety = 30;
  /// Marge à droite entre la fin du chart (et le point animé) et le bord du module (évite que le sonar soit tronqué).
  static const double _chartRightMargin = 24.0;
  /// Marge en bas du chart pour que la puce (point de départ / sonar) ne soit jamais coupée par les onglets.
  static const double _chartBottomMargin = 24.0;
  static const double _chartHeightBase = 212.0;
  static const double _chartTotalHeight = _chartHeightBase + _chartBottomMargin;
  static const double _lineChartStrokeWidth = 2.0;
  static const double _periodChipHeight = 36.0;
  /// Écart (bordure visuelle) entre la puce grise et la capsule blanche, et retrait de la puce dans le segment.
  static const double _periodPillInset = 2.0;
  /// Hauteur totale du module d’onglets (puces + padding capsule).
  static const double _periodModuleHeight =
      _periodChipHeight + 2 * _periodPillInset; // 40
  static const List<String> _periodLabels = ['1j', '1s', '1m', '1a', '5a'];

  /// Hauteur du module en [instrumentDetailStyle] : courbe + onglets + disclaimer (alignée sur le [build]).
  /// Utilisée par [LayoutPageInstrumentDetail] pour dimensionner le hero sans grand vide sous le chart.
  static double get instrumentDetailEstimatedHeightPx {
    const disclaimerLinesPx = 56.0;
    return _chartTotalHeight +
        AppSpacing.md +
        _periodModuleHeight +
        AppSpacing.md +
        disclaimerLinesPx;
  }

  /// Épaisseur de la courbe en mode ligne (détail instrument) — réutiliser pour les bundles.
  static double get instrumentDetailLineStrokeWidth => _lineChartStrokeWidth;

  @override
  Widget build(BuildContext context) {
    final screenWidth =
        chartContainerWidth ?? MediaQuery.sizeOf(context).width;
    final chartWidth = instrumentDetailStyle
        ? screenWidth - _chartRightMargin
        : screenWidth - AppSpacing.lg - _chartRightMargin;
    final chartLeft = instrumentDetailStyle ? 0.0 : -AppSpacing.lg;

    final chartStack = SizedBox(
      height: _chartTotalHeight,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            left: chartLeft,
            top: 0,
            child: SizedBox(
              width: chartWidth,
              height: _chartTotalHeight,
              child: _buildChartContent(
                chartWidth,
                _chartTotalHeight,
                startPriceLabelLeft:
                    instrumentDetailStyle ? AppSpacing.sm : 0,
              ),
            ),
          ),
        ],
      ),
    );

    final periodAndDisclaimer = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: AppSpacing.md),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(child: _buildPeriodChips(context)),
            if (onChartTypeChanged != null) ...[
              const SizedBox(width: AppSpacing.sm),
              SizedBox(
                height: _periodModuleHeight,
                width: _periodModuleHeight,
                child: Material(
                  color: invertedPeriodChips
                      ? AppColors.white
                      : AppColors.cardBackground,
                  borderRadius: BorderRadius.circular(999),
                  child: InkWell(
                    onTap: () => onChartTypeChanged!(!isLineChart),
                    borderRadius: BorderRadius.circular(999),
                    child: Padding(
                      padding: const EdgeInsets.all(10),
                      child: Icon(
                        isLineChart ? Icons.candlestick_chart_rounded : Icons.show_chart_rounded,
                        size: 24,
                        color: AppColors.accent,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Ces taux se situent à mi-chemin entre les taux d\'achat et de vente de vos devises. '
          'Votre taux réel peut varier selon que vous achetez ou vendez.',
          textAlign: TextAlign.center,
          style: AppTypography.meta.copyWith(
            color: AppColors.textSecondary,
            fontSize: 12,
          ),
        ),
      ],
    );

    if (instrumentDetailStyle) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          chartStack,
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: periodAndDisclaimer,
          ),
        ],
      );
    }

    final candleList = candles ?? [];
    final entryPrice = candleList.isNotEmpty ? candleList.first.close : null;
    final cp = currentPrice;
    final ep = entryPrice;
    final usePeriodPerf = cp != null && ep != null && ep > 0;
    final double? periodAmount = usePeriodPerf ? cp - ep : null;
    final double? periodPct =
        periodAmount != null && ep != null ? periodAmount / ep * 100 : null;
    final isPositive = usePeriodPerf
        ? (periodAmount ?? 0) >= 0
        : (change24hPct ?? 0) >= 0;
    final perfColor = isPositive
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
    final changeStr = usePeriodPerf && periodPct != null
        ? '${isPositive ? '+' : ''}${periodPct.toStringAsFixed(2)} %'
        : (change24hPct != null
            ? '${(change24hPct! >= 0) ? '+' : ''}${change24hPct!.toStringAsFixed(2)} %'
            : '—');
    final absStr = usePeriodPerf && periodAmount != null
        ? '${periodAmount >= 0 ? '+' : ''}${periodAmount.toStringAsFixed(2)} $_chartCurrencySymbol'
        : (change24hAbs != null
            ? '${change24hAbs! >= 0 ? '+' : ''}${change24hAbs!.toStringAsFixed(2)} $_chartCurrencySymbol'
            : '');

    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.card),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.lg,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  displayPrice,
                  style: ui_typography.AppTypography.tileTitle.copyWith(
                    color: AppColors.textPrimary,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                    height: 1.0,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    if (absStr != '—') ...[
                      Text(
                        absStr,
                        style: ui_typography.AppTypography.tileSubtitle.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.xs),
                    ],
                    Icon(
                      isPositive ? Icons.arrow_drop_up : Icons.arrow_drop_down,
                      color: perfColor,
                      size: 20,
                    ),
                    Text(
                      changeStr,
                      style: ui_typography.AppTypography.tileSubtitle.copyWith(
                        color: perfColor,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Container(
                      width: 1,
                      height: 14,
                      color: const Color(0xFFDADCE0),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      periodLabel,
                      style: ui_typography.AppTypography.tileSubtitle.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            chartStack,
            periodAndDisclaimer,
          ],
        ),
      ),
    );
  }

  Widget _buildChartContent(
    double width,
    double height, {
    double startPriceLabelLeft = 0,
  }) {
    if (chartLoading) {
      return _ChartLoadingPlaceholder(width: width, height: height);
    }
    if (chartError != null && chartError!.isNotEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline_rounded,
                size: 40,
                color: AppColors.textSecondary.withValues(alpha: 0.8),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                chartError!,
                textAlign: TextAlign.center,
                style: AppTypography.meta.copyWith(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
              if (onRefresh != null) ...[
                const SizedBox(height: AppSpacing.md),
                TextButton.icon(
                  onPressed: onRefresh,
                  icon: const Icon(Icons.refresh_rounded, size: 18),
                  label: const Text('Rafraîchir'),
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.accent,
                  ),
                ),
              ],
            ],
          ),
        ),
      );
    }
    final candleList = candles ?? [];
    if (candleList.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Aucune donnée pour cette période',
              style: AppTypography.meta.copyWith(
                color: AppColors.textSecondary,
                fontSize: 13,
              ),
            ),
            if (onRefresh != null) ...[
              const SizedBox(height: AppSpacing.md),
              TextButton.icon(
                onPressed: onRefresh,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Rafraîchir'),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.accent,
                ),
              ),
            ],
          ],
        ),
      );
    }
    if (isLineChart) {
      final lineColor = _lineTrendColorFromCandles(candleList);
      return _ChartEntranceAnimation(
        key: ValueKey(
          'chart-$selectedTimeframeIndex-$isLineChart-${lineColor.toARGB32()}',
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final size = Size(constraints.maxWidth, constraints.maxHeight);
            final geometry = _computeLineGeometryFromCandles(candleList, size);
            return Stack(
              clipBehavior: Clip.none,
              children: [
                Positioned.fill(
                  child: CustomPaint(
                    painter: _LinePainter(
                      accent: lineColor,
                      strokeWidth: ChartAssetModule._lineChartStrokeWidth,
                      points: geometry.points,
                      startY: geometry.startY,
                    ),
                  ),
                ),
                Positioned(
                  left: startPriceLabelLeft,
                  top: geometry.startY + 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.xs,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.pageBackground,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      geometry.startPriceLabel,
                      style: AppTypography.meta.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: geometry.lastPoint.dx - ChartSonarPoint.size / 2,
                  top: geometry.lastPoint.dy - ChartSonarPoint.size / 2,
                  child: ChartSonarPoint(color: lineColor),
                ),
              ],
            );
          },
        ),
      );
    }
    final geometry = _candlestickStartGeometry(candleList, Size(width, height));
    // Candlestick : pas de point bleu (contrairement au line chart qui a le sonar en fin de courbe).
    return _ChartEntranceAnimation(
      key: ValueKey('chart-$selectedTimeframeIndex-$isLineChart'),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          CustomPaint(
            painter: _CandlestickPainter(
              candles: candleList,
              size: Size(width, height),
              positiveColor: AppColors.semanticPositive,
              negativeColor: AppColors.semanticNegative,
            ),
            size: Size(width, height),
          ),
          Positioned.fill(
            child: CustomPaint(
              painter: _DashedLineOnlyPainter(startY: geometry.startY),
              size: Size(width, height),
            ),
          ),
          Positioned(
            left: startPriceLabelLeft,
            top: geometry.startY + 6,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xs,
              ),
              decoration: BoxDecoration(
                color: AppColors.pageBackground,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                geometry.startPriceLabel,
                style: AppTypography.meta.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  _CandlestickStartGeometry _candlestickStartGeometry(
    List<CandleItem> candleList,
    Size size,
  ) {
    if (candleList.isEmpty) {
      return const _CandlestickStartGeometry(
        startY: 0,
        startPriceLabel: '—',
        firstPoint: Offset(0, 0),
      );
    }
    const paddingLeft = 0.0;
    final paddingRight = _chartRightMargin;
    const paddingTop = 16.0;
    final paddingBottom = 16.0 + _chartBottomMargin;
    final usableWidth = math.max(1.0, size.width - paddingLeft - paddingRight);
    final lowMin = candleList.map((c) => c.low).reduce(math.min);
    final highMax = candleList.map((c) => c.high).reduce(math.max);
    final range = (highMax - lowMin).abs() < 1e-9 ? 1.0 : (highMax - lowMin);
    final usableHeight = math.max(1.0, size.height - paddingTop - paddingBottom);
    final n = candleList.length;
    // Même grille X que le line chart : barres centrées en i/(n-1)*usableWidth pour n>1.
    final barWidth = n <= 1 ? usableWidth * 0.5 : (usableWidth / (n - 1)) * 0.85;
    final first = candleList.first;
    final closeY = paddingTop + (1.0 - (first.close - lowMin) / range) * usableHeight;
    final firstCenterX = n <= 1 ? paddingLeft + usableWidth * 0.5 : paddingLeft + 0;
    final formatted = first.close.abs() < 1
        ? first.close.toStringAsFixed(6).replaceAll('.', ',')
        : first.close.toStringAsFixed(2).replaceAll('.', ',');
    return _CandlestickStartGeometry(
      startY: closeY,
      startPriceLabel: '$formatted $_chartCurrencySymbol',
      firstPoint: Offset(firstCenterX, closeY),
    );
  }

  /// Grille Y basée sur le candlestick (min low, max high). Le line chart s’ajuste à cette grille.
  _LineGeometry _computeLineGeometryFromCandles(List<CandleItem> candleList, Size size) {
    if (candleList.isEmpty) {
      return const _LineGeometry(
        points: [],
        startY: 0,
        lastPoint: Offset(0, 0),
        startPriceLabel: '—',
      );
    }
    final closes = candleList.map((c) => c.close).toList();
    final lowMin = candleList.map((c) => c.low).reduce(math.min);
    final highMax = candleList.map((c) => c.high).reduce(math.max);
    const paddingTop = 16.0;
    final paddingBottom = 16.0 + _chartBottomMargin;
    final range = (highMax - lowMin).abs() < 1e-9 ? 1.0 : (highMax - lowMin);
    final usableHeight = math.max(1.0, size.height - paddingTop - paddingBottom);
    final usableWidth = math.max(1.0, size.width - _chartRightMargin);
    final points = <Offset>[];
    for (var i = 0; i < closes.length; i++) {
      final x = closes.length == 1 ? 0.0 : usableWidth * (i / (closes.length - 1));
      final normalized = (closes[i] - lowMin) / range;
      final y = paddingTop + (1 - normalized) * usableHeight;
      points.add(Offset(x, y));
    }
    final first = closes.first;
    final formattedFirst = first.abs() < 1
        ? first.toStringAsFixed(6).replaceAll('.', ',')
        : first.toStringAsFixed(2).replaceAll('.', ',');
    return _LineGeometry(
      points: points,
      startY: points.isEmpty ? 0 : points.first.dy,
      lastPoint: points.isEmpty ? Offset.zero : points.last,
      startPriceLabel: '$formattedFirst $_chartCurrencySymbol',
    );
  }

  Widget _buildPeriodChips(BuildContext context) {
    final outerColor =
        invertedPeriodChips ? AppColors.pageBackground : AppColors.cardBackground;
    final slidingPillColor =
        invertedPeriodChips ? AppColors.cardBackground : AppColors.pageBackground;
    return Container(
      padding: const EdgeInsets.all(_periodPillInset),
      decoration: BoxDecoration(
        color: outerColor,
        borderRadius: BorderRadius.circular(999),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final segmentWidth = constraints.maxWidth / _periodLabels.length;
          final pillW = segmentWidth - 2 * _periodPillInset;
          final pillH = _periodChipHeight - 2 * _periodPillInset;
          return SizedBox(
            height: _periodChipHeight,
            child: Stack(
              children: [
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOutCubic,
                  left:
                      selectedTimeframeIndex * segmentWidth + _periodPillInset,
                  top: _periodPillInset,
                  width: pillW,
                  height: pillH,
                  child: Container(
                    decoration: BoxDecoration(
                      color: slidingPillColor,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                Row(
                  children: [
                    for (int i = 0; i < _periodLabels.length; i++) ...[
                      Expanded(
                        child: _PeriodChipItem(
                          label: _periodLabels[i],
                          isSelected: selectedTimeframeIndex == i,
                          isEnabled: AssetChartTimeframe.values[i].supported,
                          onTap: AssetChartTimeframe.values[i].supported
                              ? () => onTimeframeChanged?.call(i)
                              : null,
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _PeriodChipItem extends StatelessWidget {
  const _PeriodChipItem({
    required this.label,
    required this.isSelected,
    required this.isEnabled,
    this.onTap,
  });

  final String label;
  final bool isSelected;
  final bool isEnabled;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap == null
          ? null
          : () {
              HapticFeedback.lightImpact();
              onTap!();
            },
      behavior: HitTestBehavior.opaque,
      child: Center(
        child: Text(
          label,
          style: AppTypography.bodyMedium.copyWith(
            color: isEnabled
                ? AppColors.textPrimary
                : AppColors.textSecondary.withValues(alpha: 0.5),
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

/// Pendant le chargement : rien (pas de texte, pas d’icône).
class _ChartLoadingPlaceholder extends StatelessWidget {
  const _ChartLoadingPlaceholder({required this.width, required this.height});

  final double width;
  final double height;

  @override
  Widget build(BuildContext context) {
    return const SizedBox.expand();
  }
}

/// Animation : le chart se construit de la gauche vers la droite (révélation rapide).
class _ChartEntranceAnimation extends StatefulWidget {
  const _ChartEntranceAnimation({super.key, required this.child});

  final Widget child;

  @override
  State<_ChartEntranceAnimation> createState() => _ChartEntranceAnimationState();
}

class _ChartEntranceAnimationState extends State<_ChartEntranceAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _reveal;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _reveal = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _reveal,
      builder: (context, child) {
        return ClipRect(
          child: Align(
            alignment: Alignment.centerLeft,
            widthFactor: _reveal.value,
            child: widget.child,
          ),
        );
      },
    );
  }
}

/// Point en bout de line chart avec effet sonar (anneaux qui s’étendent et s’estompent = temps réel).
class ChartSonarPoint extends StatefulWidget {
  const ChartSonarPoint({super.key, required this.color});

  static const double size = 50.0;
  final Color color;

  @override
  State<ChartSonarPoint> createState() => _ChartSonarPointState();
}

class _ChartSonarPointState extends State<ChartSonarPoint>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();
    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: ChartSonarPoint.size,
      height: ChartSonarPoint.size,
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          return CustomPaint(
            painter: _ChartSonarPointPainter(
              color: widget.color,
              ringProgress: _animation.value,
            ),
            size: Size(ChartSonarPoint.size, ChartSonarPoint.size),
          );
        },
      ),
    );
  }
}

class _ChartSonarPointPainter extends CustomPainter {
  _ChartSonarPointPainter({required this.color, required this.ringProgress});

  final Color color;
  final double ringProgress;

  static const double _dotRadius = 4.5;
  /// Diamètre d’expansion limité à ~1 marge pour ne pas être coupé par le bord droit du module.
  static const double _ringMaxRadius = 14.0;
  static const double _ringStrokeWidth = 1.8;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    // Premier anneau : progress 0 → 1
    _drawRing(canvas, center, ringProgress);

    // Deuxième anneau : décalé de 50 % pour effet continu
    final ring2Progress = (ringProgress + 0.5) % 1.0;
    _drawRing(canvas, center, ring2Progress);

    // Point central plein
    canvas.drawCircle(
      center,
      _dotRadius,
      Paint()..color = color,
    );
  }

  void _drawRing(Canvas canvas, Offset center, double progress) {
    if (progress <= 0) return;
    final radius = _dotRadius + (_ringMaxRadius - _dotRadius) * progress;
    final opacity = (1 - progress).clamp(0.0, 1.0) * 0.5;
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = color.withValues(alpha: opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = _ringStrokeWidth,
    );
  }

  @override
  bool shouldRepaint(covariant _ChartSonarPointPainter oldDelegate) =>
      oldDelegate.ringProgress != ringProgress || oldDelegate.color != color;
}

class _LinePainter extends CustomPainter {
  _LinePainter({
    required this.accent,
    this.strokeWidth = ChartAssetModule._lineChartStrokeWidth,
    required this.points,
    required this.startY,
  });

  final Color accent;
  final double strokeWidth;
  final List<Offset> points;
  final double startY;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = accent
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final dotted = Paint()
      ..color = AppColors.textSecondary.withValues(alpha: 0.55)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final path = Path();
    if (points.isEmpty) return;
    final yStart = startY.clamp(0, size.height).toDouble();
    const dashWidth = 2.2;
    const gap = 5.0;
    var x = 0.0;
    while (x < size.width) {
      final x2 = math.min(x + dashWidth, size.width).toDouble();
      canvas.drawLine(Offset(x, yStart), Offset(x2, yStart), dotted);
      x += dashWidth + gap;
    }

    if (points.isEmpty) return;
    final clamped = <Offset>[
      for (final p in points)
        Offset(p.dx.clamp(0, size.width).toDouble(), p.dy.clamp(0, size.height).toDouble()),
    ];
    path.moveTo(clamped[0].dx, clamped[0].dy);
    if (clamped.length == 1) {
      canvas.drawPath(path, paint);
      return;
    }
    if (clamped.length == 2) {
      path.lineTo(clamped[1].dx, clamped[1].dy);
      canvas.drawPath(path, paint);
      return;
    }
    for (var i = 0; i < clamped.length - 1; i++) {
      final p0 = clamped[i > 0 ? i - 1 : i];
      final p1 = clamped[i];
      final p2 = clamped[i + 1];
      final p3 = clamped[i + 1 < clamped.length - 1 ? i + 2 : i + 1];
      final c1 = i == 0
          ? p1
          : Offset(
              p1.dx + (p2.dx - p0.dx) / 6,
              p1.dy + (p2.dy - p0.dy) / 6,
            );
      final c2 = i == clamped.length - 2
          ? p2
          : Offset(
              p2.dx - (p3.dx - p1.dx) / 6,
              p2.dy - (p3.dy - p1.dy) / 6,
            );
      path.cubicTo(c1.dx, c1.dy, c2.dx, c2.dy, p2.dx, p2.dy);
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _LinePainter oldDelegate) =>
      oldDelegate.accent != accent ||
      oldDelegate.strokeWidth != strokeWidth ||
      oldDelegate.startY != startY ||
      oldDelegate.points.length != points.length ||
      (points.isNotEmpty &&
          oldDelegate.points.isNotEmpty &&
          oldDelegate.points.last != points.last);
}

class _CandlestickPainter extends CustomPainter {
  _CandlestickPainter({
    required this.candles,
    required this.size,
    required this.positiveColor,
    required this.negativeColor,
  });

  final List<CandleItem> candles;
  final Size size;
  final Color positiveColor;
  final Color negativeColor;

  static const double _paddingTop = 16.0;
  static const double _paddingBottomExtra = 24.0;

  @override
  void paint(Canvas canvas, Size size) {
    if (candles.isEmpty) return;
    final s = this.size;
    const paddingLeft = 0.0;
    const paddingRight = 24.0; // même écart qu’à droite du line chart (_chartRightMargin)
    final paddingBottom = 16.0 + _paddingBottomExtra;
    final usableWidth = math.max(1.0, s.width - paddingLeft - paddingRight);
    final lowMin = candles.map((c) => c.low).reduce(math.min);
    final highMax = candles.map((c) => c.high).reduce(math.max);
    final range = (highMax - lowMin).abs() < 1e-9 ? 1.0 : (highMax - lowMin);
    final usableHeight = math.max(1.0, s.height - _paddingTop - paddingBottom);
    final n = candles.length;
    final barWidth = n <= 1 ? usableWidth * 0.5 : (usableWidth / (n - 1)) * 0.85;
    double barCenterXAt(int i) => n <= 1 ? paddingLeft + usableWidth * 0.5 : paddingLeft + usableWidth * i / (n - 1);

    for (var i = 0; i < n; i++) {
      final c = candles[i];
      final barCenterXVal = barCenterXAt(i);
      final openY = _paddingTop + (1.0 - (c.open - lowMin) / range) * usableHeight;
      final closeY = _paddingTop + (1.0 - (c.close - lowMin) / range) * usableHeight;
      final highY = _paddingTop + (1.0 - (c.high - lowMin) / range) * usableHeight;
      final lowY = _paddingTop + (1.0 - (c.low - lowMin) / range) * usableHeight;

      final isUp = c.close >= c.open;
      final bodyTop = math.min(openY, closeY);
      final bodyHeight = (openY - closeY).abs().clamp(2.0, double.infinity);

      final wickPaint = Paint()
        ..color = isUp ? positiveColor : negativeColor
        ..strokeWidth = 1.2
        ..style = PaintingStyle.stroke;
      canvas.drawLine(Offset(barCenterXVal, highY), Offset(barCenterXVal, lowY), wickPaint);

      final bodyPaint = Paint()
        ..color = isUp ? positiveColor : negativeColor
        ..style = PaintingStyle.fill;
      canvas.drawRect(
        Rect.fromLTWH(barCenterXVal - barWidth / 2, bodyTop, barWidth, bodyHeight),
        bodyPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _CandlestickPainter oldDelegate) =>
      oldDelegate.candles != candles ||
      oldDelegate.size != size ||
      oldDelegate.positiveColor != positiveColor ||
      oldDelegate.negativeColor != negativeColor;
}

class _LineGeometry {
  const _LineGeometry({
    required this.points,
    required this.startY,
    required this.lastPoint,
    required this.startPriceLabel,
  });

  final List<Offset> points;
  final double startY;
  final Offset lastPoint;
  final String startPriceLabel;
}

class _CandlestickStartGeometry {
  const _CandlestickStartGeometry({
    required this.startY,
    required this.startPriceLabel,
    required this.firstPoint,
  });

  final double startY;
  final String startPriceLabel;
  final Offset firstPoint;
}

class _DashedLineOnlyPainter extends CustomPainter {
  _DashedLineOnlyPainter({required this.startY});

  final double startY;

  @override
  void paint(Canvas canvas, Size size) {
    final yStart = startY.clamp(0, size.height).toDouble();
    final dotted = Paint()
      ..color = AppColors.textSecondary.withValues(alpha: 0.55)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    const dashWidth = 2.2;
    const gap = 5.0;
    var x = 0.0;
    while (x < size.width) {
      final x2 = math.min(x + dashWidth, size.width).toDouble();
      canvas.drawLine(Offset(x, yStart), Offset(x2, yStart), dotted);
      x += dashWidth + gap;
    }
  }

  @override
  bool shouldRepaint(covariant _DashedLineOnlyPainter oldDelegate) =>
      oldDelegate.startY != startY;
}
