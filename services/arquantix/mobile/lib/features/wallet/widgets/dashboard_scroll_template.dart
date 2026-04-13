import 'package:flutter/material.dart';
import 'package:custom_refresh_indicator/custom_refresh_indicator.dart';

import '../../../../design_system/design_system.dart';
import '../../../../design_system/layout/module_horizontal_margin.dart';
import '../../../../ui/components/logo_loader.dart';

// ——— Audit layout dashboard ———
//
// Structure actuelle (réutilisable) :
// 1. Scaffold(backgroundColor) → body: Stack
// 2. Stack :
//    - Positioned(header) : hauteur = headerHeight (ex. 60 % écran), peut être animée (bounce)
//    - CustomMaterialIndicator > CustomScrollView :
//      - SliverToBoxAdapter(SizedBox(headerHeight)) : réserve la place du header
//      - SliverToBoxAdapter(sheet) : carte (ex. WalletsModule) sous le header, sans chevauchement
//      - SliverToBoxAdapter(content) : contenu sous la carte
//      - SliverToBoxAdapter(SizedBox(bottomReserved)) : marge bas pour la nav
// 3. Header (WalletHeader) : navbar + zone étendue (Balance ± LineChart) + boutons. Line chart optionnel (showLineChart).
// 4. Constantes partagées : moduleHorizontalMargin, sheetOverlapTopPadding, bottomReserved.
//
// Réutilisation : toute page "dashboard" (header hero + carte blanche + liste) utilise ce template.
// Debug : activer [debugLayoutBorders] (design_system) pour un contour blanc + label sur chaque zone.

/// Constantes de layout partagées pour les pages type dashboard (header + sheet + scroll).
/// Utiliser [moduleHorizontalMargin] partout pour les marges gauche/droite (home, compte euro, détail transaction, liste transactions, IBAN, etc.).
class DashboardLayoutConstants {
  DashboardLayoutConstants._();

  /// Marge horizontale unique pour tout le projet (pages, modules, listes, carrousels).
  /// Alignée sur [kModuleHorizontalMargin] (design system).
  static const double moduleHorizontalMargin = kModuleHorizontalMargin;
  /// Chevauchement du premier module (sheet) sur le header. 0 = sheet juste sous le header ; valeur positive = sheet remonte.
  static const double sheetOverlapTopPadding = 0;
  static const double moduleGap = AppSpacing.s10;
  static const double bottomNavBarHeight = 56;
  static const double bottomNavBarMargin = 16;
}

/// Template réutilisable : header fixe (hero) + zone scrollable avec carte sous le header + contenu.
/// Utilisé par HomeScreen et toute autre page dashboard (même structure, header + sheet + body).
class DashboardScrollTemplate extends StatelessWidget {
  const DashboardScrollTemplate({
    super.key,
    required this.header,
    required this.headerHeight,
    this.headerBackground,
    this.headerBackgroundHeight,
    this.headerInteractionOverlay,
    this.contentBeforeSheet,
    this.sheetChild,
    required this.content,
    this.bottomReserved,
    this.onRefresh,
    this.scrollController,
    this.sheetOverlapTopPadding = DashboardLayoutConstants.sheetOverlapTopPadding,
    this.moduleHorizontalMargin = DashboardLayoutConstants.moduleHorizontalMargin,
    this.sheetPadding,
    this.backgroundColor,
    this.refreshIndicatorBuilder,
    this.fixedTopOverlay,
    this.fixedTopOverlayHeight,
    /// Trait noir pleine largeur sous la zone header ([headerHeight]) pour debug (délimiter hero vs scroll).
    this.debugHeaderBottomEdge = false,
    /// Espace entre le bas du header positionné et le début du [content] scrollé (1er module / fond page).
    /// Utilisé par [LayoutPageInstrumentDetail] ([AppSpacing.pageDescriptionToFirstField]).
    this.scrollContentTopSpacing = 0,
  });

  /// Bloc header (ex. WalletHeader) affiché en Positioned(top: 0, height: headerHeight). Fond transparent si [headerBackground] fourni.
  final Widget header;

  /// Image (ou widget) d’arrière-plan de la zone header, même taille que le header, en arrière-plan de la page.
  /// Si non null, affiché derrière le header ; le header ne dessine pas son propre fond.
  final Widget? headerBackground;

  /// Hauteur de la zone d'arrière-plan (image). Si null, utilise [headerHeight]. Ex. 60 % de l'écran.
  final double? headerBackgroundHeight;

  /// Couche transparente au-dessus du scroll pour garder les zones cliquables du header (avatar, notification, période). Même taille que le header.
  final Widget? headerInteractionOverlay;

  /// Hauteur du header (ex. MediaQuery.sizeOf(context).height * 0.60).
  final double headerHeight;

  /// Contenu affiché au premier plan, juste sous la zone header (avant la carte sheet). Ex. module Flash info.
  final Widget? contentBeforeSheet;

  /// Carte qui chevauche le header (ex. WalletsModule). Null = pas de carte.
  final Widget? sheetChild;

  /// Contenu sous la carte (ou directement sous le header si pas de sheet).
  final Widget content;

  /// Hauteur réservée en bas (nav bar + marge). Par défaut bottomNavBarHeight + bottomNavBarMargin + MediaQuery.padding.bottom.
  final double? bottomReserved;

  /// Pull-to-refresh. Si null, pas d’indicateur de refresh.
  final Future<void> Function()? onRefresh;

  /// Contrôleur de scroll (optionnel).
  final ScrollController? scrollController;

  final double sheetOverlapTopPadding;
  final double moduleHorizontalMargin;
  /// Padding autour du [sheetChild]. Si null, utilise [EdgeInsets.only(left/right: moduleHorizontalMargin)].
  /// Passer [EdgeInsets.zero] pour un sheet plein largeur (ex. carousel sliding).
  final EdgeInsetsGeometry? sheetPadding;
  final Color? backgroundColor;

  /// Builder custom pour l’indicateur de refresh (ex. LogoLoader). Si null et onRefresh non null, utilise l’indicateur par défaut.
  final Widget Function(BuildContext context, dynamic controller)? refreshIndicatorBuilder;
  /// Overlay fixe en haut de page (ex. navbar) rendu au-dessus du scroll.
  final Widget? fixedTopOverlay;
  final double? fixedTopOverlayHeight;

  /// Affiche un trait noir sur toute la largeur à `y = headerHeight` (bas du hero positionné).
  final bool debugHeaderBottomEdge;

  /// Voir [scrollContentTopSpacing] sur le constructeur.
  final double scrollContentTopSpacing;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;
    final reserved = bottomReserved ??
        (DashboardLayoutConstants.bottomNavBarHeight +
            DashboardLayoutConstants.bottomNavBarMargin +
            bottomInset);
    final bodyColor = backgroundColor ?? const Color(0xFFF2F2F2);
    // Bande bleue = blueHeight (60 %). Header = headerHeight (60 % - 2 m). Content juste en dessous du header (spacer = headerHeight), fond transparent pour voir le bleu.
    final blueHeight = headerBackgroundHeight ?? headerHeight;

    // Réduire l'espace réservé pour que le sheet chevauche l'image (premier module à cheval sur le header).
    final spaceBeforeSheet = headerHeight - sheetOverlapTopPadding;

    final contentSection = Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(height: spaceBeforeSheet),
        if (scrollContentTopSpacing > 0)
          SizedBox(height: scrollContentTopSpacing),
        if (contentBeforeSheet != null)
          Padding(
            padding: EdgeInsets.symmetric(horizontal: moduleHorizontalMargin),
            child: debugLayoutBorder(label: 'Avant sheet', child: contentBeforeSheet!),
          ),
        debugLayoutBorder(
          label: 'Content',
          child: Container(
            color: Colors.transparent,
            padding: EdgeInsets.zero,
            margin: EdgeInsets.zero,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (sheetChild != null)
                  Padding(
                    padding: sheetPadding ?? EdgeInsets.only(left: moduleHorizontalMargin, right: moduleHorizontalMargin),
                    child: sheetChild,
                  ),
                content,
              ],
            ),
          ),
        ),
      ],
    );

    Widget scrollContent = CustomScrollView(
      controller: scrollController,
      clipBehavior: Clip.none,
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      slivers: [
        SliverToBoxAdapter(
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              if (headerBackground != null)
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  height: blueHeight,
                  child: debugLayoutBorder(label: 'Arrière-plan ($blueHeight px)', child: headerBackground!),
                ),
              contentSection,
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                height: headerHeight,
                child: debugLayoutBorder(
                  label: 'Header ($headerHeight px)',
                  child: Stack(
                    // loose : ne force pas le hero à remplir toute la hauteur réservée (évite vide sous le chart).
                    fit: StackFit.loose,
                    alignment: Alignment.topCenter,
                    children: [
                      header,
                      if (headerInteractionOverlay != null) headerInteractionOverlay!,
                    ],
                  ),
                ),
              ),
              if (debugHeaderBottomEdge) ...[
                Positioned(
                  top: headerHeight,
                  left: 0,
                  right: 0,
                  height: 2,
                  child: const IgnorePointer(
                    child: ColoredBox(color: Colors.black),
                  ),
                ),
                Positioned(
                  top: headerHeight + 2,
                  left: 4,
                  child: IgnorePointer(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      color: Colors.black,
                      child: Text(
                        'debug header ${headerHeight.toStringAsFixed(0)} px → scroll en dessous',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          height: 1.2,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        SliverToBoxAdapter(
          child: debugLayoutBorder(
            label: 'Réserve bas ($reserved px)',
            child: SizedBox(height: reserved),
          ),
        ),
      ],
    );

    if (onRefresh != null) {
      scrollContent = CustomMaterialIndicator(
        onRefresh: onRefresh!,
        backgroundColor: Colors.transparent,
        useMaterialContainer: false,
        indicatorBuilder: refreshIndicatorBuilder ??
            (context, controller) => const Padding(
                  padding: EdgeInsets.all(12.0),
                  child: LogoLoader(size: 28, color: Colors.white),
                ),
        child: scrollContent,
      );
    }

    if (fixedTopOverlay == null || fixedTopOverlayHeight == null) {
      return Scaffold(
        backgroundColor: bodyColor,
        body: scrollContent,
      );
    }

    return Scaffold(
      backgroundColor: bodyColor,
      body: Stack(
        children: [
          Positioned.fill(child: scrollContent),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: fixedTopOverlayHeight!,
            child: fixedTopOverlay!,
          ),
        ],
      ),
    );
  }
}
