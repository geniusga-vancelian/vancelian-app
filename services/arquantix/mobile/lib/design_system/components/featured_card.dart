import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Composant : carte à la une (image en haut avec padding, contenu en dessous).
class FeaturedCard extends StatelessWidget {
  final String title;
  final String coverUrl;
  final int readingTime;
  /// Texte meta custom (ex. date de publication). Si fourni, remplace "X Minutes".
  final String? metaText;
  /// Auteur optionnel affiche apres la date avec separateur vertical.
  final String? authorName;
  final VoidCallback onTap;
  /// Tag affiché en haut à gauche sur l'image (ex. "Real Estate", "Crypto"), style pill avec fond blur.
  final String? tag;

  const FeaturedCard({
    required this.title,
    required this.coverUrl,
    required this.readingTime,
    this.metaText,
    this.authorName,
    required this.onTap,
    this.tag,
    super.key,
  });

  static const double _imageAspectRatio = 16 / 9;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.image),
                  child: Stack(
                    alignment: Alignment.topLeft,
                    children: [
                      AspectRatio(
                        aspectRatio: _imageAspectRatio,
                        child: coverUrl.isNotEmpty
                            ? Image.network(
                                coverUrl,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => _placeholder(),
                              )
                            : _placeholder(),
                      ),
                      if (tag != null && tag!.isNotEmpty) _buildTag(tag!),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.lg,
                  AppSpacing.lg,
                  AppSpacing.xs,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 72),
                      child: Text(
                        title,
                        style: AppTypography.featuredCardTitle.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Builder(
                      builder: (context) {
                        final hasCustomMeta = (metaText ?? '').trim().isNotEmpty;
                        if (hasCustomMeta) {
                          final hasAuthor = (authorName ?? '').trim().isNotEmpty;
                          if (!hasAuthor) {
                            return Text(
                              metaText!.trim(),
                              style: AppTypography.meta,
                            );
                          }
                          return Row(
                            children: [
                              Text(
                                metaText!.trim(),
                                style: AppTypography.meta,
                              ),
                              const SizedBox(width: AppSpacing.sm),
                              Container(
                                width: 1,
                                height: 18,
                                color: const Color(0xFFDADCE0),
                              ),
                              const SizedBox(width: AppSpacing.sm),
                              Expanded(
                                child: Text(
                                  authorName!.trim(),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: AppTypography.meta,
                                ),
                              ),
                            ],
                          );
                        }
                        return Row(
                          children: [
                            Icon(Icons.schedule, size: 16, color: AppColors.accent),
                            const SizedBox(width: AppSpacing.xs),
                            Text(
                              '$readingTime Minutes',
                              style: AppTypography.meta,
                            ),
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTag(String label) {
    return Positioned(
      top: AppSpacing.sm,
      left: AppSpacing.sm,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.chip),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.5),
                width: 0.5,
              ),
            ),
            child: Text(
              label,
              style: AppTypography.meta.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(Icons.image_not_supported,
            color: AppColors.placeholderIcon, size: 48),
      );
}
