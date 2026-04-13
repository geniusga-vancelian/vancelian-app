import 'package:flutter/material.dart';

import '../../../../design_system/atoms/dashboard_header_gradient.dart';
import 'dashboard_scroll_template.dart';
import 'wallet_header.dart';

/// Constantes de layout pour le template dashboard wallet (même logique que [DashboardLayoutConstants]).
class DashboardWalletLayoutConstants {
  DashboardWalletLayoutConstants._();

  /// Fraction de la hauteur d'écran pour la bande bleue (arrière-plan). Ex. 0.60 = 60 %.
  static const double headerBackgroundHeightFraction = 0.60;
  /// Fraction pour le header ; on retire 2 marges pour le calcul en pixels.
  static const double headerHeightFraction = 0.60;
  static const double headerGeneralMargin = 16;
}

/// Template de page "dashboard wallet" : même layout que l'accueil (arrière-plan 60 %, header, content)
/// avec éléments optionnels (performance, line chart) et contenu adapté à chaque écran.
///
/// - [showPerformance] : affiche ou non la ligne "X% · Période" sous le montant (défaut true).
/// - [showLineChart] : affiche ou non le graphique entre Balance et boutons (défaut true).
/// - [content] : contenu principal sous la carte sheet (modules adaptés à chaque page).
/// - [sheetChild] : carte type "My account" (optionnelle).
/// - [contentBeforeSheet] : contenu entre le header et la carte (optionnel).
class DashboardWalletTemplate extends StatelessWidget {
  const DashboardWalletTemplate({
    super.key,
    required this.content,
    this.balanceTitle = 'Balance',
    this.balanceAmount = '0 €',
    this.balanceAssetIcon,
    this.balanceBelowAmount,
    this.performanceText = '0 %',
    this.periodLabel = 'All time',
    this.showPerformance = true,
    this.showLineChart = true,
    this.showProfileInNavbar = true,
    this.showStatisticsInNavbar = true,
    this.showNotificationsInNavbar = true,
    this.onPeriodTap,
    this.onAvatarTap,
    this.onNotificationTap,
    this.onBalanceTap,
    this.onChartTap,
    this.actionButtons,
    this.onDeposit,
    this.onSend,
    this.onBuy,
    this.onMore,
    this.showBackButton = false,
    this.onBackTap,
    this.theme = WalletHeaderTheme.dark,
    this.headerBackground,
    this.headerBackgroundHeight,
    this.headerHeight,
    this.contentBeforeSheet,
    this.sheetChild,
    this.sheetPadding,
    this.bottomReserved,
    this.onRefresh,
    this.scrollController,
    this.backgroundColor,
    this.refreshIndicatorBuilder,
    this.showInteractionOverlay = true,
  });

  /// Contenu principal sous le header (et la carte sheet si présente). Modules libres par écran.
  final Widget content;

  /// Titre au-dessus du montant (ex. "Balance" ou "Euro").
  final String balanceTitle;
  /// Montant affiché (ex. "145 022,50 €").
  final String balanceAmount;
  /// Logo de l’asset à gauche du titre (ex. € dans un disque bleu pour Euro, BTC pour Bitcoin). Optionnel.
  final Widget? balanceAssetIcon;
  /// Widget affiché juste sous le montant (ex. bouton IBAN avec chevron). Optionnel.
  final Widget? balanceBelowAmount;
  /// Texte de performance (ex. "0 %", "+2,5 %"). Utilisé si [showPerformance] est true.
  final String performanceText;
  /// Période affichée (ex. "All time"). Utilisé si [showPerformance] est true.
  final String periodLabel;
  /// Affiche la ligne performance / période sous le montant.
  final bool showPerformance;
  /// Affiche le module line chart entre Balance et les boutons.
  final bool showLineChart;
  final bool showProfileInNavbar;
  final bool showStatisticsInNavbar;
  final bool showNotificationsInNavbar;
  /// Callback sélection de période (si [showPerformance] et clic sur la période).
  final VoidCallback? onPeriodTap;

  final VoidCallback? onAvatarTap;
  final VoidCallback? onNotificationTap;
  final VoidCallback? onBalanceTap;
  final VoidCallback? onChartTap;
  /// Boutons d'action (Déposer, Envoyer, etc.). Null = pas de boutons.
  final Widget? actionButtons;
  final VoidCallback? onDeposit;
  final VoidCallback? onSend;
  final VoidCallback? onBuy;
  final VoidCallback? onMore;

  /// Si true, le header affiche uniquement un bouton Retour (pas d'avatar, stat, notification).
  final bool showBackButton;
  final VoidCallback? onBackTap;

  final WalletHeaderTheme theme;

  /// Arrière-plan de la zone header (bande). Si null, utilise le dégradé 3 couleurs par défaut (sans image).
  final Widget? headerBackground;
  /// Hauteur de la bande bleue en px. Si null, 60 % de l'écran.
  final double? headerBackgroundHeight;
  /// Hauteur du header en px. Si null, 60 % - 2 marges.
  final double? headerHeight;

  /// Contenu entre le header et la carte sheet (optionnel).
  final Widget? contentBeforeSheet;
  /// Carte type "My account" sous le header (optionnelle).
  final Widget? sheetChild;
  /// Padding autour du sheet. Si null, padding horizontal par défaut. [EdgeInsets.zero] = sheet plein largeur (ex. modules sliding).
  final EdgeInsetsGeometry? sheetPadding;

  final double? bottomReserved;
  final Future<void> Function()? onRefresh;
  final ScrollController? scrollController;
  final Color? backgroundColor;
  final Widget Function(BuildContext context, dynamic controller)? refreshIndicatorBuilder;
  /// Affiche l'overlay de zones cliquables (avatar, période, etc.). Mettre false en debug si besoin.
  final bool showInteractionOverlay;

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.sizeOf(context).height;
    final headerBackgroundHeightValue = headerBackgroundHeight ??
        screenHeight * DashboardWalletLayoutConstants.headerBackgroundHeightFraction;
    final headerHeightValue = headerHeight ??
        (screenHeight * DashboardWalletLayoutConstants.headerHeightFraction -
                2 * DashboardWalletLayoutConstants.headerGeneralMargin)
            .clamp(0.0, double.infinity);

    final defaultBackground = headerBackground ??
        const DecoratedBox(
          decoration: DashboardHeaderGradient.decoration,
          child: SizedBox.expand(),
        );

    final header = WalletHeader(
      progress: 0,
      balanceTitle: balanceTitle,
      balanceAmount: balanceAmount,
      balanceAssetIcon: balanceAssetIcon,
      balanceBelowAmount: balanceBelowAmount,
      performanceText: performanceText,
      periodLabel: periodLabel,
      showPerformance: showPerformance,
      showLineChart: showLineChart,
      onPeriodTap: onPeriodTap,
      onAvatarTap: onAvatarTap,
      onNotificationTap: onNotificationTap,
      theme: theme,
      actionButtons: actionButtons,
      moduleHorizontalMargin: DashboardLayoutConstants.moduleHorizontalMargin,
      hideForegroundElements: false,
      showBackButton: showBackButton,
      onBackTap: onBackTap,
      showNavbar: false,
      showProfileInNavbar: showProfileInNavbar,
      showStatisticsInNavbar: showStatisticsInNavbar,
      showNotificationsInNavbar: showNotificationsInNavbar,
    );

    final topInset = MediaQuery.paddingOf(context).top;
    final fixedNavBarHeight = walletHeaderNavBarHeight + topInset;
    final fixedNavBar = WalletHeaderNavBar(
      progress: 0,
      showBackButton: showBackButton,
      showProfile: showProfileInNavbar,
      showStatistics: showStatisticsInNavbar,
      showNotifications: showNotificationsInNavbar,
      showAvatarDot: true,
      onBackTap: onBackTap,
      onAvatarTap: onAvatarTap,
      onNotificationTap: onNotificationTap,
      showNotificationDot: false,
    );

    final overlay = showInteractionOverlay
        ? WalletHeaderHitOverlay(
            headerHeight: headerHeightValue,
            periodLabel: periodLabel,
            onAvatarTap: onAvatarTap,
            onNotificationTap: onNotificationTap,
            onPeriodTap: onPeriodTap,
            onBalanceTap: onBalanceTap,
            onChartTap: onChartTap ?? onPeriodTap,
            onDeposit: onDeposit,
            onSend: onSend,
            onBuy: onBuy,
            onMore: onMore,
            showBackButton: showBackButton,
            onBackTap: onBackTap,
          )
        : null;

    return DashboardScrollTemplate(
      header: header,
      headerHeight: headerHeightValue,
      headerBackground: defaultBackground,
      headerBackgroundHeight: headerBackgroundHeightValue,
      headerInteractionOverlay: overlay,
      contentBeforeSheet: contentBeforeSheet,
      sheetChild: sheetChild,
      sheetPadding: sheetPadding,
      content: content,
      bottomReserved: bottomReserved,
      onRefresh: onRefresh ?? () async {},
      scrollController: scrollController,
      backgroundColor: backgroundColor,
      refreshIndicatorBuilder: refreshIndicatorBuilder,
      fixedTopOverlay: fixedNavBar,
      fixedTopOverlayHeight: fixedNavBarHeight,
    );
  }
}
