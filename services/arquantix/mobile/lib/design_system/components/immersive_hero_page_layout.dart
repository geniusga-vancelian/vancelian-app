import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';

/// Gabarit de page réutilisable : **hero immersif** (ex. [ArticleHeroHeader]) puis
/// **contenu** scrollable dans une seule colonne — même structure que la page article.
///
/// Usage typique avec [AppTopNavBar] transparente et `extendBodyBehindAppBar: true`.
class ImmersiveHeroPageTemplate extends StatelessWidget {
  const ImmersiveHeroPageTemplate({
    super.key,
    required this.hero,
    required this.belowHero,
    this.appBar,
    this.scrollController,
    this.scrollPhysics,
    this.backgroundColor,
    this.extendBodyBehindAppBar = true,
    this.onRefresh,
  });

  /// Barre du haut (souvent [AppTopNavBar] avec titre qui apparaît au scroll).
  final PreferredSizeWidget? appBar;

  /// Bloc hero (image 1:1, titre, puces) — en pratique un [ArticleHeroHeader].
  final Widget hero;

  /// Tout le contenu sous le hero (cartes, texte, etc.).
  final Widget belowHero;

  final ScrollController? scrollController;

  /// Physics du scroll (ex. [AlwaysScrollableScrollPhysics] pour pull-to-refresh futur).
  final ScrollPhysics? scrollPhysics;

  final Color? backgroundColor;

  /// Aligné sur le comportement « image sous la status bar » des pages article.
  final bool extendBodyBehindAppBar;

  /// Si défini, enveloppe le scroll dans un [RefreshIndicator] (physics scrollable même court).
  final Future<void> Function()? onRefresh;

  @override
  Widget build(BuildContext context) {
    final effectivePhysics = onRefresh != null
        ? (scrollPhysics ?? const AlwaysScrollableScrollPhysics())
        : scrollPhysics;

    final scroll = SingleChildScrollView(
      controller: scrollController,
      physics: effectivePhysics,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          hero,
          belowHero,
        ],
      ),
    );

    final body = onRefresh != null
        ? RefreshIndicator(
            onRefresh: onRefresh!,
            child: scroll,
          )
        : scroll;

    return Scaffold(
      backgroundColor: backgroundColor ?? AppColors.pageBackground,
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      appBar: appBar,
      body: body,
    );
  }
}
