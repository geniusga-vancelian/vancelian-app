import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Key-value table row for settings / detail screens.
///
/// Figma specs:
/// - Label: 15px regular (left-aligned)
/// - Value: 15px semi-bold (right-aligned, flex-1)
/// - Gap: 8px
///
/// Typically used inside a [SettingsCard] with a sectionTitle.
class SettingsTableRow extends StatelessWidget {
  const SettingsTableRow({
    super.key,
    required this.label,
    required this.value,
    this.labelStyle,
    this.valueStyle,
    this.labelBold = false,
  });

  final String label;
  final String value;
  final TextStyle? labelStyle;
  final TextStyle? valueStyle;
  final bool labelBold;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          label,
          style: labelStyle ??
              (labelBold
                  ? AppTypography.itemPrimary
                  : AppTypography.itemSecondary),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            value,
            style: valueStyle ?? AppTypography.itemPrimary,
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }
}

/// Footer row with a contrasting background (e.g. #F2F2F7) for totals.
///
/// Figma specs:
/// - bg #F2F2F7, padding 16
/// - Label: 15px semi-bold (left)
/// - Value: 15px semi-bold (right)
class SettingsTableFooter extends StatelessWidget {
  const SettingsTableFooter({
    super.key,
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.pageBackground,
      padding: const EdgeInsets.all(AppSpacing.s4),
      child: Row(
        children: [
          Text(label, style: AppTypography.itemPrimary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: AppTypography.itemPrimary,
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}
