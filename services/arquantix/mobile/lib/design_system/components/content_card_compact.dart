import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Carte plate compacte : texte à gauche (titre + description + tags), image à droite.
/// Réutilisable pour Steps (Itinerary) et toute liste type "news small/flat".
class ContentCardCompact extends StatelessWidget {
  const ContentCardCompact({
    required this.title,
    super.key,
    this.dateLabel,
    this.description,
    this.tags = const [],
    this.imageUrl,
    this.onTap,
    this.borderRadius,
    this.alwaysShowImageArea = false,
  });

  /// Date ou label affiché tout en haut de la carte (ex. "15 mars 2025").
  final String? dateLabel;

  final String title;
  final String? description;
  final List<String> tags;
  final String? imageUrl;

  /// Si true, réserve toujours la place pour l'image à droite (placeholder si pas d'URL).
  final bool alwaysShowImageArea;
  final VoidCallback? onTap;
  final double? borderRadius;

  static const double _imageSize = 80;
  static const double _defaultRadius = 16;

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? _defaultRadius;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(radius),
        child: Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(radius),
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 8,
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
                    if (dateLabel != null && dateLabel!.trim().isNotEmpty) ...[
                      Text(
                        dateLabel!,
                        style: AppTypography.labelSmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: AppSpacing.xs),
                    ],
                    Text(
                      title,
                      style: AppTypography.titleSmall.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (description != null && description!.trim().isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        description!,
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                          height: 1.35,
                        ),
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (tags.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.sm),
                      Wrap(
                        spacing: AppSpacing.xs,
                        runSpacing: AppSpacing.xs,
                        children: tags
                            .take(4)
                            .map((tag) => _TagPill(label: tag))
                            .toList(),
                      ),
                    ],
                  ],
                ),
              ),
              if ((imageUrl != null && imageUrl!.isNotEmpty) || alwaysShowImageArea) ...[
                const SizedBox(width: AppSpacing.md),
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.image),
                  child: SizedBox(
                    width: _imageSize,
                    height: _imageSize,
                    child: imageUrl != null && imageUrl!.isNotEmpty
                        ? Image.network(
                            imageUrl!,
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
        child: Icon(
          Icons.image_not_supported_outlined,
          color: AppColors.placeholderIcon,
          size: 28,
        ),
      );
}

/// Petite pill pour tag (affichage seul, non cliquable).
class _TagPill extends StatelessWidget {
  const _TagPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppColors.navBarActivePill.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        label,
        style: AppTypography.labelSmall.copyWith(
          color: AppColors.textPrimary,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}
