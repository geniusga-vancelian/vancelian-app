import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Une ligne de stats style Figma DS (valeur + libellé), colonnes égales — aligné web `figma_stats_grid` (ex. 4 ou 6 colonnes sur une ligne).
class DsFigmaStatsGridRow extends StatelessWidget {
  const DsFigmaStatsGridRow({
    super.key,
    required this.items,
  });

  final List<({String value, String label})> items;

  static const Color _muted = Color(0xFF62656E);
  static const Color _border = Color(0xFFF3F3F3);

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SizedBox(
          width: constraints.maxWidth,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (var i = 0; i < items.length; i++) ...[
                if (i > 0)
                  Container(
                    width: 1,
                    color: _border,
                  ),
                Expanded(
                  child: _StatCell(
                    value: items[i].value,
                    label: items[i].label,
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _StatCell extends StatelessWidget {
  const _StatCell({
    required this.value,
    required this.label,
  });

  final String value;
  final String label;

  static const Color _muted = DsFigmaStatsGridRow._muted;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 76),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: AppSpacing.lg,
        ),
        child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.titleSmall.copyWith(
              color: _muted,
              fontWeight: FontWeight.w800,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.bodySmall.copyWith(
              color: _muted,
              fontWeight: FontWeight.w400,
              height: 1.35,
            ),
          ),
        ],
      ),
      ),
    );
  }
}
