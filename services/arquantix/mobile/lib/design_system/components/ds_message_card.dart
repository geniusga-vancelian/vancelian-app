import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';

/// Carte de textes du module validation Figma (`MessageCard.tsx`).
///
/// - [title] : 15px semibold noir
/// - [description] / [caption] : 13px regular #8E8E93
class DsMessageCard extends StatelessWidget {
  const DsMessageCard({
    super.key,
    this.title,
    this.description,
    this.caption,
    this.descriptionStyle,
    this.captionStyle,
  });

  final String? title;
  final String? description;
  final String? caption;

  /// Par défaut : [AppTypography.bodySmRegular] (13px). Passer [AppTypography.paragraph]
  /// pour un corps « regular » (16px).
  final TextStyle? descriptionStyle;
  final TextStyle? captionStyle;

  @override
  Widget build(BuildContext context) {
    final lines = <Widget>[];

    void addLine(String? text, TextStyle style) {
      if (text == null || text.trim().isEmpty) return;
      lines.add(
        Text(
          text.trim(),
          textAlign: TextAlign.center,
          maxLines: 6,
          overflow: TextOverflow.ellipsis,
          style: style,
        ),
      );
    }

    addLine(
      title,
      AppTypography.itemPrimary.copyWith(color: AppColors.black),
    );
    final muted = AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted);
    addLine(
      description,
      descriptionStyle ?? muted,
    );
    addLine(
      caption,
      captionStyle ?? muted,
    );

    if (lines.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (int i = 0; i < lines.length; i++) ...[
            if (i > 0) const SizedBox(height: 4),
            lines[i],
          ],
        ],
      ),
    );
  }
}
