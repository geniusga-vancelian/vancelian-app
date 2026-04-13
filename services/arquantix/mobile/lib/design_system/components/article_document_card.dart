import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Carte de document téléchargeable (PDF, etc.).
///
/// Figma: fond blanc, rounded 16, shadow, icône 36×36 rounded 10 bg #E5E5EA,
/// titre 15px/w600, info 13px/w500 #8E8E93, icône download 16×16.
class ArticleDocumentCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final IconData fileIcon;
  final IconData actionIcon;

  const ArticleDocumentCard({
    super.key,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.fileIcon = Icons.picture_as_pdf_rounded,
    this.actionIcon = Icons.download_rounded,
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
              child: Icon(fileIcon, size: 18, color: AppColors.gray),
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
            Icon(actionIcon, size: 16, color: AppColors.gray),
          ],
        ),
      ),
    );
  }
}
