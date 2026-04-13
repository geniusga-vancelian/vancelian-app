import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'bar_chart_module.dart';
import 'stat_card.dart';

/// Section header row: title (left) + optional action text (right).
///
/// Figma spec: title 20px/w600/-0.45, action 16px/w600/-0.31 indigo,
/// min-height 32px.
class SectionHeaderRow extends StatelessWidget {
  const SectionHeaderRow({
    super.key,
    required this.title,
    this.actionText,
    this.onAction,
  });

  final String title;
  final String? actionText;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 32),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: AppTypography.sectionTitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (actionText != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onAction,
              behavior: HitTestBehavior.opaque,
              child: Text(
                actionText!,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.accent,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.31,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Assembled module: [SectionHeaderRow] + [StatCard] with [BarChartModule].
///
/// Figma "Module Gain" — displays a titled section with a colored bar chart
/// card and a summary info row below.
class ModuleGain extends StatelessWidget {
  const ModuleGain({
    super.key,
    this.title = 'Module Gain',
    this.actionText = 'See more',
    this.onAction,
    required this.chartData,
    required this.amount,
    required this.period,
    required this.description,
    this.amountColor = const Color(0xFF34C759),
    this.backgroundColor = const Color(0xFF34C759),
    this.backgroundImageUrl,
    this.icon,
    this.chartHeight = 144,
    this.valueFormatter,
  });

  final String title;
  final String? actionText;
  final VoidCallback? onAction;
  final List<BarChartData> chartData;
  final String amount;
  final String period;
  final String description;
  final Color amountColor;
  final Color backgroundColor;
  final String? backgroundImageUrl;
  final Widget? icon;
  final double chartHeight;
  final String Function(double)? valueFormatter;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        SectionHeaderRow(
          title: title,
          actionText: actionText,
          onAction: onAction,
        ),
        const SizedBox(height: AppSpacing.s1),
        StatCard(
          amount: amount,
          amountColor: amountColor,
          period: period,
          description: description,
          backgroundColor: backgroundColor,
          backgroundImageUrl: backgroundImageUrl,
          icon: icon,
          chartWidget: BarChartModule(
            data: chartData,
            height: chartHeight,
            barColor: Colors.white,
            labelColor: Colors.white,
            valueFormatter: valueFormatter,
          ),
        ),
      ],
    );
  }
}
