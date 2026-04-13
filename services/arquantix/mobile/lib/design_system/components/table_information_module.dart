import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

class TableInformationRowData {
  const TableInformationRowData({
    required this.left,
    required this.right,
    this.showInfoIcon = false,
    this.onInfoTap,
    this.rightWidget,
  });

  final String left;
  final String right;
  final bool showInfoIcon;
  final VoidCallback? onInfoTap;
  /// Si non null, affiché à la place de [right] (ex. lien cliquable).
  final Widget? rightWidget;
}

/// Module blanc "table information" avec titre optionnel et lignes gauche/droite.
class TableInformationModule extends StatelessWidget {
  const TableInformationModule({
    super.key,
    this.title,
    required this.rows,
    this.titleTextStyle,
  });

  final String? title;
  final List<TableInformationRowData> rows;
  final TextStyle? titleTextStyle;

  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _rowSpacing = 14;
  static const double _infoIconSize = 18;

  List<Widget> _buildRows(List<TableInformationRowData> cleanedRows) {
    final widgets = <Widget>[];
    for (int i = 0; i < cleanedRows.length; i++) {
      final row = cleanedRows[i];
      if (i > 0) {
        widgets.add(const SizedBox(height: _rowSpacing));
      }
      widgets.add(
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Flexible(
                    child: Text(
                      row.left,
                      style: AppTypography.subtitleEmphasized.copyWith(
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  if (row.showInfoIcon) ...[
                    const SizedBox(width: 6),
                    GestureDetector(
                      onTap: row.onInfoTap,
                      child: const Icon(
                        Icons.info_outline,
                        size: _infoIconSize,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 12),
            if (row.rightWidget != null)
              row.rightWidget!
            else
              Text(
                row.right,
                style: AppTypography.subtitleRegular.copyWith(
                  color: AppColors.textPrimary,
                ),
                textAlign: TextAlign.right,
              ),
          ],
        ),
      );
    }
    return widgets;
  }

  @override
  Widget build(BuildContext context) {
    final cleanedRows = rows
        .where((r) => r.left.trim().isNotEmpty && r.right.trim().isNotEmpty)
        .toList();
    if (cleanedRows.isEmpty) {
      return const SizedBox.shrink();
    }

    final hasTitle = (title ?? '').trim().isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (hasTitle)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(
              title!.trim(),
              style: titleTextStyle ?? AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(24),
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
              children: _buildRows(cleanedRows),
            ),
          ),
        ),
      ],
    );
  }
}
