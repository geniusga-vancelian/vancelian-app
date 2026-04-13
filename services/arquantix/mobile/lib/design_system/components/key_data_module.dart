import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';

/// Une ligne du module données clés : label à gauche, valeur à droite, optionnellement icône info.
class KeyDataRow {
  const KeyDataRow({
    required this.label,
    required this.value,
    this.showInfoIcon = false,
    this.onInfoTap,
  });

  final String label;
  final String value;
  final bool showInfoIcon;
  final VoidCallback? onInfoTap;
}

/// Module « données clés » : carte blanche, coins arrondis, lignes label / valeur.
/// Style aligné sur le screenshot (padding généreux, optionnellement icône « i » à côté du label).
class KeyDataModule extends StatelessWidget {
  const KeyDataModule({
    super.key,
    required this.rows,
  });

  final List<KeyDataRow> rows;

  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _rowSpacing = 14;
  static const double _infoIconSize = 18;

  @override
  Widget build(BuildContext context) {
    return Container(
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
          children: [
            for (int i = 0; i < rows.length; i++) ...[
              if (i > 0) const SizedBox(height: _rowSpacing),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(
                          child: Text(
                            rows[i].label,
                            style: AppTypography.bodyMedium.copyWith(
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        if (rows[i].showInfoIcon) ...[
                          const SizedBox(width: 6),
                          GestureDetector(
                            onTap: rows[i].onInfoTap,
                            child: Icon(
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
                  Text(
                    rows[i].value,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textPrimary,
                    ),
                    textAlign: TextAlign.right,
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
