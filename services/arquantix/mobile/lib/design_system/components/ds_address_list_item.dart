import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'list_card.dart';

/// Ligne d’adresse (titre + sous-titre + chevron) — Figma ZIP Design System 5.
class DsAddressListItem extends StatelessWidget {
  const DsAddressListItem({
    super.key,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.showChevron = true,
  });

  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final bool showChevron;

  static final TextStyle _subtitleStyle = AppTypography.bodySmRegular.copyWith(
    height: 16 / 13,
    letterSpacing: -0.08,
    color: AppColors.textMuted,
  );

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: AppTypography.itemPrimary
                        .copyWith(color: AppColors.textPrimary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    subtitle,
                    style: _subtitleStyle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            if (showChevron) ...[
              const SizedBox(width: AppSpacing.xxl),
              const ChevronRight(size: 12, color: Color(0xFFC7C7CC)),
            ],
          ],
        ),
      ),
    );
  }
}
