import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Carré catégorie : carré = image seule (bordure + padding si sélectionné) ; titre et description optionnelle en dessous.
class CategoryCard extends StatefulWidget {
  /// Clé de cache stable (ex. id catégorie) pour éviter rechargement au changement d'onglet.
  final String? imageCacheKey;
  final String imageUrl;
  final String title;
  /// Description sous le titre. Si null ou vide, seule la ligne du titre est affichée.
  final String? description;
  final bool selected;
  final VoidCallback onTap;

  /// Côté du carré (image). Si null, utilise [defaultSize].
  final double? squareSize;

  const CategoryCard({
    this.imageCacheKey,
    required this.imageUrl,
    required this.title,
    this.description,
    required this.selected,
    required this.onTap,
    this.squareSize,
    super.key,
  });

  @override
  State<CategoryCard> createState() => _CategoryCardState();
}

class _CategoryCardState extends State<CategoryCard> {
  /// Taille par défaut du carré quand [squareSize] n'est pas fourni.
  static const double defaultSize = 160;

  /// Contour (outline) : épaisseur finale, animée 0 → valeur en 500 ms.
  static const double _borderWidth = 1.5;
  static const double _activeInnerPadding = 6;
  static const Duration _paddingAnimationDuration = Duration(milliseconds: 500);

  /// Rayon des coins du carré (et de l'image) — plus arrondi que la carte standard.
  static const double _squareRadius = 20;

  double get _size => widget.squareSize ?? defaultSize;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: _size,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Carré = image en fond (toujours pleine taille), overlay contour + padding blanc si sélectionné
            SizedBox(
              width: _size,
              height: _size,
              child: AnimatedContainer(
                duration: _paddingAnimationDuration,
                curve: Curves.easeOut,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(_squareRadius),
                  boxShadow: [
                    if (!widget.selected)
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.06),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(_squareRadius),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      // Image toujours pleine taille en arrière-plan (cache stable + pas de fade pour éviter clignotement)
                      widget.imageUrl.isNotEmpty
                          ? CachedNetworkImage(
                              imageUrl: widget.imageUrl,
                              cacheKey: widget.imageCacheKey,
                              fit: BoxFit.cover,
                              fadeInDuration: Duration.zero,
                              fadeOutDuration: Duration.zero,
                              placeholder: (_, __) => _placeholder(),
                              errorWidget: (_, __, ___) => _placeholder(),
                            )
                          : _placeholder(),
                      // Overlay: padding blanc animé (0 → 6 px en 500 ms) + contour immédiat (sans animation)
                      Positioned.fill(
                        child: IgnorePointer(
                          ignoring: true,
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              // Padding blanc : animation de l’épaisseur 0 → 6 px (pas d’opacité)
                              AnimatedContainer(
                                duration: _paddingAnimationDuration,
                                curve: Curves.easeOut,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(_squareRadius),
                                  border: Border.all(
                                    color: Colors.white,
                                    width: widget.selected ? _activeInnerPadding : 0,
                                  ),
                                ),
                              ),
                              // Contour noir : épaisseur 0 → 1.5 px en 500 ms à la sélection, 1.5 → 0 px à la désélection
                              AnimatedContainer(
                                duration: _paddingAnimationDuration,
                                curve: Curves.easeOut,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(_squareRadius),
                                  border: Border.all(
                                    color: AppColors.textPrimary,
                                    width: widget.selected ? _borderWidth : 0,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            // Titre (et description optionnelle) en dessous du carré
            Padding(
              padding: const EdgeInsets.only(
                top: AppSpacing.sm,
                left: 2,
                right: 2,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    widget.title,
                    style: AppTypography.labelSmall.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                      height: 1.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (widget.description != null && widget.description!.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      widget.description!,
                      style: AppTypography.labelSmall.copyWith(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                        height: 1.2,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 32,
        ),
      );
}
