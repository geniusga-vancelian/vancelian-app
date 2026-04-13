import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Two-section card: colored chart area (top) + white info row (bottom).
///
/// Figma spec:
/// - Card: borderRadius 16, shadow 0 0 20 -10 rgba(0,0,0,0.12), clipBehavior
/// - Chart section: gradient overlay (195° transparent → 60% black) + solid bg + optional image (mix-blend-multiply)
/// - Info section: white, icon (36×36, bg #E5E5EA, radius 10) + amount + period + description
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.amount,
    required this.period,
    required this.description,
    this.chartWidget,
    this.icon,
    this.amountColor = const Color(0xFF34C759),
    this.backgroundColor = const Color(0xFF34C759),
    this.backgroundImageUrl,
    this.gradientAngle = 195.818,
    this.gradientOpacity = 0.6,
  });

  /// Chart or visualization widget rendered inside the colored top area.
  final Widget? chartWidget;

  /// Icon widget displayed at the left of the info row.
  final Widget? icon;

  /// Main amount text, e.g. "+34,59 €".
  final String amount;

  /// Color of the amount text.
  final Color amountColor;

  /// Period text appended after amount, e.g. "cette semaine".
  final String period;

  /// Description text below the amount line.
  final String description;

  /// Solid background color for the chart section.
  final Color backgroundColor;

  /// Optional background image URL overlaid with mix-blend-multiply.
  final String? backgroundImageUrl;

  /// Gradient angle in degrees (default ~196° as Figma).
  final double gradientAngle;

  /// Black overlay max opacity (default 0.6).
  final double gradientOpacity;

  static const _cardRadius = BorderRadius.all(Radius.circular(16));

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: _cardRadius,
        boxShadow: const [
          BoxShadow(
            color: Color(0x1F000000),
            blurRadius: 20,
            spreadRadius: -10,
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (chartWidget != null) _buildChartSection(),
          _buildInfoSection(),
        ],
      ),
    );
  }

  Widget _buildChartSection() {
    final radians = gradientAngle * 3.14159265 / 180;
    final dx = -1.0 * (radians - 3.14159265).abs().clamp(0, 1);

    return Stack(
      children: [
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: [
                  Colors.transparent,
                  Colors.black.withValues(alpha: gradientOpacity),
                ],
              ),
              color: backgroundColor,
            ),
          ),
        ),
        Positioned.fill(
          child: ColoredBox(color: backgroundColor.withValues(alpha: 0.3)),
        ),
        if (backgroundImageUrl != null)
          Positioned.fill(
            child: ColorFiltered(
              colorFilter: const ColorFilter.mode(
                Colors.transparent,
                BlendMode.multiply,
              ),
              child: Image.network(
                backgroundImageUrl!,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const SizedBox.shrink(),
              ),
            ),
          ),
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: 14,
          ),
          child: chartWidget ?? const SizedBox.shrink(),
        ),
      ],
    );
  }

  Widget _buildInfoSection() {
    return Container(
      color: AppColors.cardBackground,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: 14,
      ),
      child: Row(
        children: [
          if (icon != null) ...[
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: const Color(0xFFE5E5EA),
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: icon,
            ),
            const SizedBox(width: AppSpacing.lg),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text.rich(
                  TextSpan(children: [
                    TextSpan(
                      text: amount,
                      style: AppTypography.bodyMedium.copyWith(
                        color: amountColor,
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                        height: 20 / 16,
                      ),
                    ),
                    TextSpan(
                      text: ' $period',
                      style: AppTypography.bodyMedium.copyWith(
                        color: const Color(0xFF444140),
                        fontWeight: FontWeight.w400,
                        fontSize: 16,
                        height: 20 / 16,
                      ),
                    ),
                  ]),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    height: 16 / 12,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
