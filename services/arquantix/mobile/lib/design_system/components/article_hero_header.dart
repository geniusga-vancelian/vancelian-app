import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'app_back_button.dart';
import 'category_badge.dart';
import 'kalai_icon.dart';

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

  /// Si `true` et [imageUrl] vide → bascule sur un layout **compact** :
  /// hauteur intrinsèque (s'adapte au contenu), bloc puces+titre calé en haut
  /// juste sous la nav bar, padding top réduit, **pas d'overlay noir**, fond
  /// = [heroFallbackColor] (par défaut [AppColors.gray6]). Utilisé pour les
  /// pages dont la cover est optionnelle / absente (Help, Academy, certains
  /// articles News). Sans effet si [imageUrl] est non vide.
  final bool compactWhenNoCover;
  /// Couleur du titre / sous-titre / puces en mode compact (cf.
  /// [compactWhenNoCover]). Par défaut [AppColors.textPrimary] (texte noir
  /// sur fond clair). Mettre [AppColors.white] si le fond compact est foncé.
  final Color compactTextColor;

  /// Quand le hero est en mode compact ([compactWhenNoCover] + [imageUrl]
  /// vide) : si `true` (défaut), le scroll passe **sous** la barre du haut
  /// (`extendBodyBehindAppBar`) — padding top = safe area + toolbar + petit gap.
  /// Si `false`, le corps commence **sous** [AppTopNavBar] : utiliser un simple
  /// [compactTopGapBelowAppBar] pour espacer titre et barre — hauteur du bloc
  /// hero ≈ contenu uniquement.
  final bool compactBodyExtendsBehindAppBar;

  /// Espace sous la barre du haut quand [compactBodyExtendsBehindAppBar] est
  /// `false` (mode compact « light », sans image de fond).
  final double compactTopGapBelowAppBar;

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
    this.compactWhenNoCover = false,
    this.compactTextColor = AppColors.textPrimary,
    this.compactBodyExtendsBehindAppBar = true,
    this.compactTopGapBelowAppBar = AppSpacing.s4,
  });

  @override
  Widget build(BuildContext context) {
    if (compactWhenNoCover && imageUrl.isEmpty) {
      return _buildCompactNoCover(context);
    }

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
            child: _buildTitleArea(AppColors.white),
          ),
        ],
      ),
    );
  }

  /// Layout compact (pas de cover image) : hauteur intrinsèque, padding top
  /// **réduit** au-dessus des puces (~8px sous la nav bar), texte sombre par
  /// défaut sur fond clair. Pas d'overlay noir, pas de Stack — le screen
  /// hôte fournit sa propre `AppTopNavBar` (cas Help/Academy/News sans
  /// cover : `showNavBar: false` côté composant).
  Widget _buildCompactNoCover(BuildContext context) {
    final topPadding = MediaQuery.paddingOf(context).top;
    final double padTop;
    if (compactBodyExtendsBehindAppBar) {
      // Scroll sous AppBar : même logique qu'avant (safe area + toolbar + gap).
      padTop = topPadding + kToolbarHeight + AppSpacing.s2;
    } else {
      // Corps sous AppBar : léger écart sous la barre — hauteur ≈ contenu.
      padTop = compactTopGapBelowAppBar;
    }
    return Container(
      width: double.infinity,
      color: heroFallbackColor ?? AppColors.gray6,
      padding: EdgeInsets.only(
        top: padTop,
        left: AppSpacing.s4,
        right: AppSpacing.s4,
        bottom: compactTopGapBelowAppBar,
      ),
      child: _buildTitleArea(compactTextColor),
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
            kalaiIcon: KalaiIcons.arrowLeft,
            onPressed: onBack,
            variant: AppBackButtonVariant.glass,
          ),
        const Spacer(),
        ...navBarActions,
      ],
    );
  }

  Widget _buildTitleArea(Color textColor) {
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
            color: textColor,
          ),
        ),
        if (sub != null && sub.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s2),
          Text(
            sub,
            style: AppTypography.bodyRegular.copyWith(
              color: textColor.withValues(alpha: 0.92),
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
              KalaiIcon(
                KalaiIcons.clock,
                size: 12,
                color: textColor.withValues(alpha: 0.7),
              ),
              const SizedBox(width: AppSpacing.s1),
              Text(
                readingTime!,
                style: AppTypography.bodySmRegular.copyWith(
                  color: textColor.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
