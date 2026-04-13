import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'category_badge.dart';
import 'app_back_button.dart';

/// Données d'un badge catégorie pour le hero header.
class ArticleCategoryBadgeData {
  final String label;
  final Color dotColor;

  const ArticleCategoryBadgeData({
    required this.label,
    required this.dotColor,
  });
}

/// Hero header immersif pour la page article.
///
/// Hauteur du fond : [backgroundHeightScreenFraction] (défaut article
/// [kArticleBackgroundHeightScreenFraction] ; offre exclusive 70 % ;
/// bundle [kBundleBackgroundHeightScreenFraction] 40 %).
/// Overlay ~32 %, bouton retour glassmorphism 40×40, badges catégorie, titre blanc.
/// Le layout height est réduit de [overlapHeight] pour permettre au premier
/// contenu de chevaucher visuellement le bas du hero.
class ArticleHeroHeader extends StatelessWidget {
  /// Page article : fraction de la hauteur d’écran pour le fond image (40 %).
  static const double kArticleBackgroundHeightScreenFraction = 0.4;

  /// Page offre exclusive : fraction pour le même composant (70 %).
  static const double kExclusiveOfferBackgroundHeightScreenFraction = 0.7;

  /// Page détail bundle (crypto) — même gabarit immersif qu’offre exclusive, fond 40 %.
  static const double kBundleBackgroundHeightScreenFraction = 0.4;

  /// Page détail instrument (marchés / achat) — fond hero 40 %.
  static const double kInstrumentDetailBackgroundHeightScreenFraction = 0.4;

  final String imageUrl;
  final String title;
  /// Sous-titre sous le titre principal (ex. chapô offre exclusive, [AppTypography.bodyRegular]).
  final String? subtitle;
  final List<ArticleCategoryBadgeData> badges;
  final VoidCallback? onBack;
  final double overlapHeight;
  final double overlayOpacity;
  final String? readingTime;
  final List<Widget> navBarActions;

  /// When true, the hero renders its own AppBackButton back/nav row.
  /// Set to false when an external [AppTopNavBar] handles navigation.
  final bool showNavBar;

  /// Extra top padding to account for an external app bar overlaid on top.
  /// Typically `kToolbarHeight` when [showNavBar] is false.
  final double extraTopPadding;

  /// Distance du **bord bas** du hero au **bas** du bloc titre (puces + titre).
  /// Défaut [AppSpacing.s10] (40px).
  final double titleBottomInset;

  /// Contenu sous le titre (ex. CTA pleine largeur) — reste dans le hero, au-dessus du chevauchement contenu.
  final Widget? belowTitle;

  /// Part de la hauteur d’écran pour la zone image (ex. 0.4 = 40 %).
  final double backgroundHeightScreenFraction;

  /// Fond du hero si [imageUrl] est vide ou en erreur de chargement (ex. couleur marque actif).
  final Color? heroFallbackColor;

  const ArticleHeroHeader({
    super.key,
    required this.imageUrl,
    required this.title,
    this.subtitle,
    this.badges = const [],
    this.onBack,
    this.overlapHeight = 16,
    this.overlayOpacity = 0.32,
    this.readingTime,
    this.navBarActions = const [],
    this.showNavBar = true,
    this.extraTopPadding = 0,
    this.titleBottomInset = AppSpacing.s10,
    this.belowTitle,
    this.backgroundHeightScreenFraction = kArticleBackgroundHeightScreenFraction,
    this.heroFallbackColor,
  });

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.sizeOf(context).height;
    final heroVisualHeight = screenHeight * backgroundHeightScreenFraction;
    final topPadding = MediaQuery.paddingOf(context).top;

    return SizedBox(
      height: heroVisualHeight - overlapHeight,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: heroVisualHeight,
            child: _buildBackground(),
          ),
          if (showNavBar)
            Positioned(
              top: topPadding,
              left: AppSpacing.s4,
              right: AppSpacing.s4,
              child: _buildNavBar(),
            ),
          Positioned(
            bottom: titleBottomInset,
            left: AppSpacing.s4,
            right: AppSpacing.s4,
            child: _buildTitleArea(),
          ),
        ],
      ),
    );
  }

  Color get _emptyOrErrorBackgroundColor => heroFallbackColor ?? AppColors.gray6;

  Widget _buildBackground() {
    return Stack(
      fit: StackFit.expand,
      children: [
        if (imageUrl.isNotEmpty)
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 380),
            switchInCurve: Curves.easeOut,
            switchOutCurve: Curves.easeOut,
            transitionBuilder: (child, animation) {
              return FadeTransition(opacity: animation, child: child);
            },
            layoutBuilder: (currentChild, previousChildren) {
              return Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  ...previousChildren,
                  if (currentChild != null) currentChild,
                ],
              );
            },
            child: CachedNetworkImage(
              key: ValueKey<String>(imageUrl),
              imageUrl: imageUrl,
              cacheKey: imageUrl,
              fit: BoxFit.cover,
              fadeInDuration: Duration.zero,
              fadeOutDuration: Duration.zero,
              placeholder: (context, url) =>
                  Container(color: _emptyOrErrorBackgroundColor),
              errorWidget: (_, __, ___) =>
                  Container(color: _emptyOrErrorBackgroundColor),
            ),
          )
        else
          Container(color: _emptyOrErrorBackgroundColor),
        DecoratedBox(
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: overlayOpacity),
          ),
        ),
      ],
    );
  }

  Widget _buildNavBar() {
    return Row(
      children: [
        if (onBack != null)
          AppBackButton(
            icon: Icons.arrow_back_ios_new_rounded,
            onPressed: onBack,
            variant: AppBackButtonVariant.glass,
          ),
        const Spacer(),
        ...navBarActions,
      ],
    );
  }

  Widget _buildTitleArea() {
    final sub = subtitle?.trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (badges.isNotEmpty) ...[
          Wrap(
            spacing: AppSpacing.s2,
            runSpacing: AppSpacing.s1,
            children: badges
                .map((b) => CategoryBadge(label: b.label, dotColor: b.dotColor))
                .toList(),
          ),
          const SizedBox(height: AppSpacing.s2),
        ],
        Text(
          title,
          style: AppTypography.amountSecondary.copyWith(
            color: AppColors.white,
          ),
        ),
        if (sub != null && sub.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s2),
          Text(
            sub,
            style: AppTypography.bodyRegular.copyWith(
              color: AppColors.white.withValues(alpha: 0.92),
              height: 1.35,
            ),
          ),
        ],
        if (belowTitle != null) ...[
          const SizedBox(height: AppSpacing.s3),
          belowTitle!,
        ],
        if (readingTime != null) ...[
          const SizedBox(height: AppSpacing.s2),
          Row(
            children: [
              Icon(Icons.schedule_rounded, size: 12, color: AppColors.white.withValues(alpha: 0.7)),
              const SizedBox(width: AppSpacing.s1),
              Text(
                readingTime!,
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.white.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
