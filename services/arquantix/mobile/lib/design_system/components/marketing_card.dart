import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Hauteur prédéfinie pour [MarketingCard].
enum MarketingCardSize {
  small,
  medium,
  large,
}

/// Composant : carte marketing full image — image en fond, texte à gauche.
/// Seuls [imageUrl] et [title] sont requis ; description, label, logoLabel et bouton sont optionnels.
class MarketingCard extends StatelessWidget {
  /// URL de l'image de fond (full bleed).
  final String imageUrl;

  /// Texte principal (affiché en bas à gauche, blanc, gros).
  final String title;

  /// Description optionnelle sous le titre (blanc).
  final String? description;

  /// Label optionnel en haut à gauche (ex. "30 %", catégorie).
  final String? label;

  /// Lettre ou court texte affiché dans un disque en coin haut gauche (ex. "R" pour logo). Optionnel.
  final String? logoLabel;

  /// Libellé du bouton ; si null, pas de bouton. Optionnel.
  final String? buttonLabel;

  /// Rayon des coins (optionnel). Si null, utilise [AppRadius.card].
  final double? borderRadius;

  /// Callback du bouton (ignoré si [buttonLabel] est null).
  final VoidCallback? onButtonTap;

  /// Callback au tap sur la carte (optionnel).
  final VoidCallback? onTap;

  /// Hauteur de la carte.
  final MarketingCardSize size;

  /// Hauteur personnalisée (prioritaire sur [size]) pour ratio largeur/hauteur.
  final double? customHeight;

  const MarketingCard({
    required this.imageUrl,
    required this.title,
    this.description,
    this.label,
    this.logoLabel,
    this.buttonLabel,
    this.onButtonTap,
    this.onTap,
    this.size = MarketingCardSize.medium,
    this.customHeight,
    this.borderRadius,
    super.key,
  });

  static double _heightFor(MarketingCardSize s) {
    switch (s) {
      case MarketingCardSize.small:
        return 160;
      case MarketingCardSize.medium:
        return 200;
      case MarketingCardSize.large:
        return 260;
    }
  }


  @override
  Widget build(BuildContext context) {
    final height = customHeight ?? _heightFor(size);
    final radius = borderRadius ?? AppRadius.card;
    final content = ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Image full bleed
          imageUrl.isNotEmpty
              ? Image.network(
                  imageUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => _placeholder(),
                )
              : _placeholder(),

          // Gradient noir progressif pour lisibilité du texte (plus foncé en bas)
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.transparent,
                  Colors.black.withValues(alpha: 0.15),
                  Colors.black.withValues(alpha: 0.5),
                  Colors.black.withValues(alpha: 0.75),
                ],
                stops: const [0.0, 0.4, 0.7, 1.0],
              ),
            ),
          ),

          // Disque logo en coin haut gauche (sans label)
          if (logoLabel != null && logoLabel!.isNotEmpty)
            Positioned(
              left: AppSpacing.xl,
              top: AppSpacing.xl,
              child: Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF2563EB),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.2),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Text(
                  logoLabel!,
                  style: AppTypography.titleMedium.copyWith(
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ),

          // Titre (style module) + description (bold) + bouton
          Positioned(
            left: AppSpacing.xl,
            right: AppSpacing.xl,
            bottom: AppSpacing.xxl,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: AppTypography.sectionTitle.copyWith(
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    height: 1.2,
                    letterSpacing: -0.3,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (description != null && description!.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    description!,
                    style: AppTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      height: 1.35,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                if (buttonLabel != null && buttonLabel!.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.xxl),
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: onButtonTap,
                      borderRadius: BorderRadius.circular(AppRadius.button),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                          vertical: AppSpacing.sm,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(AppRadius.button),
                        ),
                        child: Text(
                          buttonLabel!,
                          style: AppTypography.paragraphSmall.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(radius),
        child: Container(
          height: height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(radius),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: content,
        ),
      ),
    );
  }

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 40,
        ),
      );
}
