import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Un segment de l'allocation (label + pourcentage). La couleur est dérivée de l'index (gris).
class PortfolioAllocationSlice {
  const PortfolioAllocationSlice({
    required this.label,
    required this.percentage,
  });

  final String label;
  final double percentage;
}

/// Palette de gris pour les segments du donut (du plus foncé au plus clair).
const List<Color> _segmentGreys = [
  Color(0xFF374151), // gris foncé
  Color(0xFF6B7280), // gris moyen-foncé
  Color(0xFF9CA3AF), // gris moyen
  Color(0xFFD1D5DB), // gris clair
  Color(0xFFE5E7EB), // gris très clair
];

/// Dessine un donut (anneau) avec des segments. Largeur de bande = fraction du rayon + marge en px.
class _DonutPainter extends CustomPainter {
  _DonutPainter({
    required this.slices,
    required this.colors,
    required this.strokeWidthFraction,
    this.strokeWidthExtraPx = 0,
  });

  final List<double> slices;
  final List<Color> colors;
  /// Fraction du rayon pour l'épaisseur du trait (ex. 0.15 = bande fine).
  final double strokeWidthFraction;
  /// Marge additionnelle en pixels (ex. 1 unité de marge générale = AppSpacing.lg).
  final double strokeWidthExtraPx;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2;
    final strokeWidth = radius * strokeWidthFraction + strokeWidthExtraPx;
    final innerRadius = (radius - strokeWidth).clamp(0.0, double.infinity);

    double startAngle = -math.pi / 2; // démarrage en haut (12h)

    for (var i = 0; i < slices.length; i++) {
      final sweepAngle = 2 * math.pi * (slices[i] / 100);
      final color = i < colors.length ? colors[i] : _segmentGreys[i % _segmentGreys.length];

      // Segment en anneau : arc externe puis arc interne en sens inverse.
      final path = Path()
        ..moveTo(
          center.dx + radius * math.cos(startAngle),
          center.dy + radius * math.sin(startAngle),
        )
        ..arcTo(
          Rect.fromCircle(center: center, radius: radius),
          startAngle,
          sweepAngle,
          false,
        )
        ..lineTo(
          center.dx + innerRadius * math.cos(startAngle + sweepAngle),
          center.dy + innerRadius * math.sin(startAngle + sweepAngle),
        )
        ..arcTo(
          Rect.fromCircle(center: center, radius: innerRadius),
          startAngle + sweepAngle,
          -sweepAngle,
          false,
        )
        ..close();

      canvas.drawPath(path, Paint()..color = color);
      startAngle += sweepAngle;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter oldDelegate) {
    return oldDelegate.slices != slices ||
        oldDelegate.colors != colors ||
        oldDelegate.strokeWidthExtraPx != strokeWidthExtraPx;
  }
}

/// Module « Allocation du portefeuille » : texte d'intro, donut (bande fine), légende.
/// Les couleurs des segments sont des dérivées de gris (ou [sliceColors] si fourni).
class PortfolioAllocationModule extends StatelessWidget {
  const PortfolioAllocationModule({
    super.key,
    required this.slices,
    this.introText,
    this.sliceColors,
    this.strokeWidthFraction = 0.15,
  });

  /// Segments (label + pourcentage). Les pourcentages doivent sommer à 100 (ou proche).
  final List<PortfolioAllocationSlice> slices;
  /// Texte optionnel au-dessus du donut (ex. description de l'allocation dynamique).
  final String? introText;
  /// Couleurs par segment. Si null, utilise des gris dérivés.
  final List<Color>? sliceColors;
  /// Épaisseur de l'anneau en fraction du rayon (0.15 ≈ moitié d'un donut "standard").
  final double strokeWidthFraction;

  static const double _cardRadius = 24;
  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _chartSize = 200;
  static const double _legendItemSpacing = 12;

  List<Color> _effectiveColors() {
    if (sliceColors != null && sliceColors!.length >= slices.length) {
      return sliceColors!;
    }
    return List.generate(
      slices.length,
      (i) => _segmentGreys[i % _segmentGreys.length],
    );
  }

  @override
  Widget build(BuildContext context) {
    final percentages = slices.map((s) => s.percentage).toList();
    final colors = _effectiveColors();

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(_cardRadius),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: _horizontalPadding,
          vertical: _verticalPadding,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (introText != null && introText!.isNotEmpty) ...[
              Text(
                introText!,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
            ],
            Center(
              child: SizedBox(
                width: _chartSize,
                height: _chartSize,
                child: CustomPaint(
                  painter: _DonutPainter(
                    slices: percentages,
                    colors: colors,
                    strokeWidthFraction: strokeWidthFraction * 1.5,
                    strokeWidthExtraPx: AppSpacing.lg * 1.5,
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            LayoutBuilder(
              builder: (context, constraints) {
                final leftIndices = <int>[];
                final rightIndices = <int>[];
                for (var i = 0; i < slices.length; i++) {
                  if (i.isEven) {
                    leftIndices.add(i);
                  } else {
                    rightIndices.add(i);
                  }
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          for (var i in leftIndices) ...[
                            if (i != leftIndices.first) const SizedBox(height: _legendItemSpacing),
                            _LegendItem(
                              label: slices[i].label,
                              percentage: slices[i].percentage,
                              color: colors[i],
                            ),
                          ],
                        ],
                      ),
                    ),
                    SizedBox(width: _legendItemSpacing),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          for (var i in rightIndices) ...[
                            if (i != rightIndices.first) const SizedBox(height: _legendItemSpacing),
                            _LegendItem(
                              label: slices[i].label,
                              percentage: slices[i].percentage,
                              color: colors[i],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Module « Allocation compact » : donut à gauche (bande réduite d’une marge), à droite 4 lignes [catégorie | %].
class PortfolioAllocationCompactModule extends StatelessWidget {
  const PortfolioAllocationCompactModule({
    super.key,
    required this.slices,
    this.sliceColors,
  });

  /// Exactement 4 segments (affichés à droite du donut).
  final List<PortfolioAllocationSlice> slices;
  final List<Color>? sliceColors;

  static const double _cardRadius = 24;
  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _chartSize = 120;
  static const double _rowSpacing = 14;

  List<Color> _effectiveColors() {
    if (sliceColors != null && sliceColors!.length >= slices.length) {
      return sliceColors!;
    }
    return List.generate(
      slices.length,
      (i) => _segmentGreys[i % _segmentGreys.length],
    );
  }

  @override
  Widget build(BuildContext context) {
    final take = slices.length >= 4 ? slices.take(4).toList() : slices;
    final percentages = take.map((s) => s.percentage).toList();
    final colors = _effectiveColors();

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(_cardRadius),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: _horizontalPadding,
          vertical: _verticalPadding,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: SizedBox(
                width: _chartSize,
                height: _chartSize,
                child: CustomPaint(
                  painter: _DonutPainter(
                    slices: percentages,
                    colors: colors,
                    strokeWidthFraction: 0.15 * 1.5,
                    strokeWidthExtraPx: 0,
                  ),
                ),
              ),
            ),
            SizedBox(width: AppSpacing.xl),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (var i = 0; i < take.length; i++) ...[
                    if (i > 0) const SizedBox(height: _rowSpacing),
                    _CompactLegendRow(
                      label: take[i].label,
                      percentage: take[i].percentage,
                      color: colors[i],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CompactLegendRow extends StatelessWidget {
  const _CompactLegendRow({
    required this.label,
    required this.percentage,
    required this.color,
  });

  final String label;
  final double percentage;
  final Color color;

  static const double _dotSize = 10;

  @override
  Widget build(BuildContext context) {
    final percentText = '${percentage.toStringAsFixed(0).replaceFirst('.', ',')} %';
    return Row(
      children: [
        Container(
          width: _dotSize,
          height: _dotSize,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Text(
          percentText,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            label,
            style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
          ),
        ),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({
    required this.label,
    required this.percentage,
    required this.color,
  });

  final String label;
  final double percentage;
  final Color color;

  static const double _dotSize = 10;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: _dotSize,
          height: _dotSize,
          margin: const EdgeInsets.only(top: 5),
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                '${percentage.toStringAsFixed(2).replaceFirst('.', ',')} %',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
