import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'kalai_icon.dart';

/// Carte de document téléchargeable (PDF, etc.).
///
/// Figma: fond blanc, rounded 16, shadow, icône 36×36 rounded 10 bg #E5E5EA,
/// titre 15px/w600, info 13px/w500 #8E8E93, icône download 16×16.
class ArticleDocumentCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  /// Icône Material **legacy** pour la pastille fichier. Si non fournie, on
  /// affiche l'icône KALAI [KalaiIcons.file] par défaut.
  final IconData? fileIcon;

  /// Icône Material **legacy** pour l'action de droite (download). Si non
  /// fournie, on affiche [KalaiIcons.download1].
  final IconData? actionIcon;

  const ArticleDocumentCard({
    super.key,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.fileIcon,
    this.actionIcon,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.s4),
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          boxShadow: AppShadow.defaultShadowList,
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: const Color(0xFFE5E5EA),
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: fileIcon != null
                  ? Icon(fileIcon, size: 18, color: AppColors.gray)
                  : const KalaiIcon(KalaiIcons.file,
                      size: 18, color: AppColors.gray),
            ),
            const SizedBox(width: AppSpacing.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: AppTypography.itemPrimary.copyWith(
                      color: AppColors.black,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    subtitle,
                    style: AppTypography.itemSupporting.copyWith(
                      color: AppColors.gray,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.s2),
            actionIcon != null
                ? Icon(actionIcon, size: 16, color: AppColors.gray)
                : const KalaiIcon(KalaiIcons.download1,
                    size: 16, color: AppColors.gray),
          ],
        ),
      ),
    );
  }
}
