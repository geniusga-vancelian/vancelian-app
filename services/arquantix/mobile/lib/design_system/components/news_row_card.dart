import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Composant : carte news horizontale (contenu à gauche, image à droite).
/// Si [showImage] est false, l'image est masquée et le contenu occupe toute la largeur.
class NewsRowCard extends StatelessWidget {
  final String title;
  final String coverUrl;
  final int readingTime;
  final VoidCallback onTap;
  /// Afficher l'image à droite (défaut true). Si false, le contenu prend toute la place.
  final bool showImage;
  /// Libellé éditorial optionnel (Market / Company / Analysis).
  final String? editorialLabel;

  const NewsRowCard({
    required this.title,
    required this.coverUrl,
    required this.readingTime,
    required this.onTap,
    this.showImage = true,
    this.editorialLabel,
    super.key,
  });

  static const double _imageSize = 100;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (editorialLabel != null && editorialLabel!.trim().isNotEmpty) ...[
                      Text(
                        editorialLabel!,
                        style: AppTypography.meta.copyWith(
                          color: AppColors.accent,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                    ],
                    Text(
                      title,
                      style: AppTypography.newsCardTitle.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                      maxLines: showImage ? 3 : 4,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Row(
                      children: [
                        Icon(Icons.schedule, size: 16, color: AppColors.accent),
                        const SizedBox(width: AppSpacing.xs),
                        Text(
                          '$readingTime min de lecture',
                          style: AppTypography.meta,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (showImage) ...[
                const SizedBox(width: AppSpacing.md),
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.image),
                  child: SizedBox(
                    width: _imageSize,
                    height: _imageSize,
                    child: coverUrl.isNotEmpty
                        ? Image.network(
                            coverUrl,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => _placeholder(),
                          )
                        : _placeholder(),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(Icons.image_not_supported,
            color: AppColors.placeholderIcon, size: 32),
      );
}
