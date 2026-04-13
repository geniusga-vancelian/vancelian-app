import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';

/// Carte de statut Figma `StatusCard` (icône + titre coloré + textes centrés).
class DsStatusCard extends StatelessWidget {
  const DsStatusCard({
    super.key,
    required this.icon,
    required this.title,
    required this.primaryText,
    this.secondaryText,
    this.titleColor = AppColors.semanticPositive,
  });

  final Widget icon;
  final String title;
  final String primaryText;
  final String? secondaryText;
  final Color titleColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        icon,
        const SizedBox(height: 24),
        Text(
          title,
          textAlign: TextAlign.center,
          style: AppTypography.articleTitle.copyWith(color: titleColor),
        ),
        const SizedBox(height: 24),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(
            children: [
              Text(
                primaryText,
                textAlign: TextAlign.center,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.itemPrimary.copyWith(color: AppColors.black),
              ),
              if (secondaryText != null) ...[
                const SizedBox(height: 4),
                Text(
                  secondaryText!,
                  textAlign: TextAlign.center,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodySmRegular.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
