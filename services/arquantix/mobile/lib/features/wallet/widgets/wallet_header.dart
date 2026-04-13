import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../design_system/debug_layout.dart';
import '../../../../ui/components/buttons/action_button_row.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../../../ui/theme/app_colors.dart';

const double _collapseThreshold = 0.65;

/// Thème visuel du header : dark (fond sombre, écritures blanches) ou light (fond clair, écritures sombres).
enum WalletHeaderTheme {
  dark,
  light,
}

/// Couleurs du header en mode dark (dégradé bleu nuit).
const Color _headerGradientStart = Color(0xFF0D1B2A);
const Color _headerGradientMid = Color(0xFF1B263B);
const Color _headerGradientEnd = Color(0xFF2D3E50);

/// Hauteur de la barre navbar (avatar + icônes) en px. Utilisée pour garder la navbar fixe lors du hot refresh.
const double walletHeaderNavBarHeight = 56;
const double _navbarHeight = walletHeaderNavBarHeight;

/// Marges horizontales de la navbar (évite que les éléments aillent de bord à bord).
const double _navbarHorizontalMargin = 16;

/// Estimation de la hauteur du module Balance (titre + montant + perf) pour le centrage vertical.
const double _balanceModuleEstimatedHeight = 100;

/// Hauteur du line chart sticky au-dessus des boutons (sans marge en bas).
const double _stickyLineChartHeight = 80;

/// Hauteur réservée en bas du header pour la bande de boutons (Déposer, Envoyer, etc.).
const double _buttonsStripHeight = 120;
const double _navbarBlurSigma = 18;

/// Module central du header : titre (ex. Balance), montant (centimes en plus petit type Revolut), performance optionnelle.
class _BalanceModule extends StatelessWidget {
  const _BalanceModule({
    required this.title,
    required this.amountFull,
    required this.performanceText,
    required this.periodLabel,
    this.onPeriodTap,
    this.foregroundPrimary,
    this.foregroundSecondary,
    this.showPerformance = true,
    this.titleLeading,
    this.childBelowAmount,
  });

  final String title;
  /// Widget affiché juste sous le montant (ex. bouton IBAN avec chevron).
  final Widget? childBelowAmount;
  /// Logo de l’asset (ex. € dans un disque bleu pour Euro, BTC pour Bitcoin). Affiché à gauche du titre.
  final Widget? titleLeading;
  final String amountFull;
  final String performanceText;
  final String periodLabel;
  final VoidCallback? onPeriodTap;
  final Color? foregroundPrimary;
  final Color? foregroundSecondary;
  /// Si false, la ligne performance / période n'est pas affichée.
  final bool showPerformance;

  /// Tailles proches de Revolut : gros montant, centimes en plus petit.
  static const double _titleFontSize = 14;
  static const double _amountMainFontSize = 44;
  static const double _amountCentsFontSize = 28;
  static const double _performanceFontSize = 14;
  /// Espacement serré type Revolut entre label, montant et performance.
  static const double _gapAfterTitle = 0;
  static const double _gapAfterAmount = 0;
  /// Hauteur de ligne du montant (1.0 = compact).
  static const double _amountLineHeight = 1.0;

  /// Sépare le montant en partie principale et centimes (ex. "146 807,71 €" -> "146 807" / ",71 €", "0 €" -> "0" / " €").
  static ({String main, String cents}) _parseAmount(String amountFull) {
    final s = amountFull.trim();
    final comma = s.indexOf(',');
    if (comma >= 0) {
      return (main: s.substring(0, comma).trim(), cents: s.substring(comma));
    }
    final dot = s.indexOf('.');
    if (dot >= 0) {
      return (main: s.substring(0, dot).trim(), cents: s.substring(dot));
    }
    // "0 €" ou "123 €" : partie entière + " €" en petit.
    final lastSpace = s.lastIndexOf(' ');
    if (lastSpace > 0) {
      return (main: s.substring(0, lastSpace).trim(), cents: s.substring(lastSpace));
    }
    return (main: s, cents: '');
  }

  @override
  Widget build(BuildContext context) {
    final parsed = _parseAmount(amountFull);
    final fg = foregroundPrimary ?? Colors.white;
    final fgSecondary = foregroundSecondary ?? Colors.white.withValues(alpha: 0.9);

    final titleText = Text(
      title,
      style: TextStyle(
        color: fgSecondary,
        fontSize: _titleFontSize,
        fontWeight: FontWeight.w500,
      ),
    );
    final titleWidget = titleLeading != null
        ? Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              titleLeading!,
              const SizedBox(width: 6),
              titleText,
            ],
          )
        : titleText;
    final amountWidget = Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Text(
          parsed.main,
          style: TextStyle(
            color: fg,
            fontSize: _amountMainFontSize,
            fontWeight: FontWeight.w800,
            height: _amountLineHeight,
          ),
        ),
        if (parsed.cents.isNotEmpty)
          Text(
            parsed.cents,
            style: TextStyle(
              color: fg,
              fontSize: _amountCentsFontSize,
              fontWeight: FontWeight.w800,
              height: _amountLineHeight,
            ),
          ),
      ],
    );
    const double _amountPaddingVertical = 4;
    final amountWithPadding = Padding(
      padding: const EdgeInsets.only(top: _amountPaddingVertical, bottom: _amountPaddingVertical),
      child: amountWidget,
    );
    final periodStyle = TextStyle(
      color: fgSecondary,
      fontSize: _performanceFontSize,
      fontWeight: FontWeight.w400,
    );
    final performanceWidget = onPeriodTap != null
        ? Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onPeriodTap,
              borderRadius: BorderRadius.circular(6),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('$performanceText · ', style: periodStyle),
                    Text(periodLabel, style: periodStyle),
                    const SizedBox(width: 2),
                    Icon(Icons.keyboard_arrow_down, color: fgSecondary, size: 18),
                  ],
                ),
              ),
            ),
          )
        : Text(
            '$performanceText · $periodLabel',
            style: periodStyle,
          );

    final children = <Widget>[
      titleWidget,
      SizedBox(height: _gapAfterTitle),
      amountWithPadding,
    ];
    if (childBelowAmount != null) {
      children.add(const SizedBox(height: 8));
      children.add(childBelowAmount!);
    }
    if (showPerformance) {
      children.add(SizedBox(height: _gapAfterAmount));
      children.add(performanceWidget);
    }
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: children,
    );
  }
}

class WalletHeader extends StatelessWidget {
  const WalletHeader({
    super.key,
    required this.progress,
    this.balanceTitle = 'Balance',
    this.balanceAmount = '0 €',
    this.performanceText = '0 %',
    this.periodLabel = 'All time',
    this.showPerformance = true,
    this.showAvatarDot = true,
    this.onAvatarTap,
    this.onNotificationTap,
    this.showNotificationDot = false,
    this.showLineChart = true,
    this.onPeriodTap,
    this.actionButtons,
    this.moduleHorizontalMargin,
    this.interactionOnly = false,
    this.theme = WalletHeaderTheme.dark,
    this.hideForegroundElements = false,
    this.showBackButton = false,
    this.onBackTap,
    this.balanceAssetIcon,
    this.balanceBelowAmount,
    this.showNavbar = true,
    this.showProfileInNavbar = true,
    this.showStatisticsInNavbar = true,
    this.showNotificationsInNavbar = true,
  });

  /// Widget affiché juste sous le montant Balance (ex. bouton IBAN avec chevron).
  final Widget? balanceBelowAmount;
  /// Logo de l’asset affiché à gauche du titre Balance (ex. € dans un disque bleu pour Euro, BTC pour Bitcoin).
  final Widget? balanceAssetIcon;
  /// Affiche la navbar visuelle. Si false, garde un espace réservé pour conserver la géométrie du header.
  final bool showNavbar;
  final bool showProfileInNavbar;
  final bool showStatisticsInNavbar;
  final bool showNotificationsInNavbar;

  /// Si true, n'affiche que la navbar et le fond (balance, période, line chart, boutons masqués).
  /// Utilisé en debug quand le Header 2 est masqué : ces éléments appartiennent au Header 2.
  final bool hideForegroundElements;

  /// Si true, la navbar affiche uniquement un bouton Retour à gauche (pas d'avatar, stat, notification).
  final bool showBackButton;
  /// Callback du bouton Retour lorsque [showBackButton] est true.
  final VoidCallback? onBackTap;

  final double progress;
  final String balanceTitle;
  final String balanceAmount;
  /// Montant ou pourcentage de performance (ex. "+2,5 %" ou "0 %").
  final String performanceText;
  /// Période de calcul de la perf (ex. "All time").
  final String periodLabel;
  /// Si false, la ligne performance / période sous le montant n'est pas affichée.
  final bool showPerformance;
  /// Conservé pour compatibilité (tests / code existant). Préférer [performanceText] et [periodLabel].
  @Deprecated('Use performanceText and periodLabel instead')
  String get accountButtonLabel => '$performanceText · $periodLabel';
  final bool showAvatarDot;
  final VoidCallback? onAvatarTap;
  /// Ouverture du centre de notifications (icône cloche).
  final VoidCallback? onNotificationTap;
  /// Affiche une pastille sur l’icône cloche (nouvelles notifications).
  final bool showNotificationDot;
  /// Affiche le module line chart entre Balance et les boutons. Si false, seul le Balance est centré.
  final bool showLineChart;
  /// Ouverture de la modale de sélection de période (performance / chart). Si null, le label période n’est pas cliquable.
  final VoidCallback? onPeriodTap;
  /// Boutons d’action (ex. Déposer, Envoyer) affichés en bas de la zone violette.
  final Widget? actionButtons;
  /// Marge horizontale du module boutons (même valeur que les autres modules, ex. carte My account). Si null, utilise la valeur par défaut du [ActionButtonModule].
  final double? moduleHorizontalMargin;
  /// Si true, le header est rendu transparent (Opacity 0) pour servir de couche d’interaction au-dessus du scroll.
  final bool interactionOnly;
  /// Thème visuel : dark (fond sombre, texte blanc) ou light (fond clair, texte sombre).
  final WalletHeaderTheme theme;

  Widget _buildNavbar(
    Color fgColor,
    Color barBg, {
    required bool isDark,
    required bool topBarOpaque,
  }) {
    final blurTint = isDark
        ? Colors.black.withValues(alpha: topBarOpaque ? 0.24 : 0.14)
        : Colors.white.withValues(alpha: topBarOpaque ? 0.56 : 0.28);
    final bar = Container(
      height: _navbarHeight,
      child: Stack(
        fit: StackFit.expand,
        children: [
          ClipRect(
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: _navbarBlurSigma,
                sigmaY: _navbarBlurSigma,
              ),
              child: Container(color: blurTint),
            ),
          ),
          if (barBg.opacity > 0) Container(color: barBg),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _navbarHorizontalMargin),
            child: Row(
              children: [
                if (showBackButton)
                  IconButton(
                    icon: Icon(Icons.arrow_back_ios_new_rounded, color: fgColor, size: 22),
                    onPressed: onBackTap,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                    style: IconButton.styleFrom(
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  )
                else ...[
                  if (showProfileInNavbar)
                    _TopBarAvatar(
                      foregroundColor: fgColor,
                      showDot: showAvatarDot,
                      onTap: onAvatarTap,
                    )
                  else
                    const SizedBox(width: 40, height: 40),
                  const Spacer(),
                  if (showStatisticsInNavbar)
                    _NavBarIconDisk(
                      icon: Icons.bar_chart_rounded,
                      foregroundColor: fgColor,
                      onPressed: () {},
                    ),
                  if (showStatisticsInNavbar && showNotificationsInNavbar)
                    const SizedBox(width: 8),
                  if (showNotificationsInNavbar)
                    _NavBarIconDisk(
                      icon: Icons.notifications_outlined,
                      foregroundColor: fgColor,
                      onPressed: onNotificationTap,
                      showDot: showNotificationDot,
                    ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
    return SafeArea(
      bottom: false,
      child: bar,
    );
  }

  Widget? _buildButtons() {
    if (actionButtons == null) return null;
    final margin = moduleHorizontalMargin ?? 0;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: margin * 2),
      child: ActionButtonModule(
        horizontalPadding: moduleHorizontalMargin != null ? 0 : null,
        child: actionButtons!,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final topBarOpaque = progress >= _collapseThreshold;
    final isDark = theme == WalletHeaderTheme.dark;
    final barBg = topBarOpaque
        ? (isDark ? AppColors.walletAppBarBg : Colors.white)
        : (isDark ? Colors.white.withValues(alpha: 0) : Colors.white.withValues(alpha: 0));
    final fgColor = topBarOpaque
        ? (isDark ? AppColors.walletAppBarFg : AppColors.textPrimary)
        : (isDark ? Colors.white : AppColors.textPrimary);
    final balanceFgPrimary = isDark ? Colors.white : AppColors.textPrimary;
    final balanceFgSecondary = isDark ? Colors.white.withValues(alpha: 0.9) : AppColors.textSecondary;
    final chartLineColor = isDark ? Colors.white : AppColors.textPrimary;

    final buttonsWidget = _buildButtons();
    Widget stack = Stack(
      fit: StackFit.expand,
      children: [
        Column(
          children: [
            debugLayoutBorder(
              label: 'Navbar',
              child: showNavbar
                  ? _buildNavbar(
                      fgColor,
                      barBg,
                      isDark: isDark,
                      topBarOpaque: topBarOpaque,
                    )
                  : SizedBox(
                      height: _navbarHeight + MediaQuery.paddingOf(context).top,
                    ),
            ),
            if (hideForegroundElements)
              const Expanded(child: SizedBox.shrink())
            else ...[
              Expanded(
                child: debugLayoutBorder(
                  label: 'Balance',
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final balanceModule = _BalanceModule(
                        title: balanceTitle,
                        amountFull: balanceAmount,
                        performanceText: performanceText,
                        periodLabel: periodLabel,
                        onPeriodTap: onPeriodTap,
                        foregroundPrimary: balanceFgPrimary,
                        foregroundSecondary: balanceFgSecondary,
                        showPerformance: showPerformance,
                        titleLeading: balanceAssetIcon,
                        childBelowAmount: balanceBelowAmount,
                      );
                      return Column(
                        children: [
                          Spacer(flex: 1),
                          balanceModule,
                          Spacer(flex: 1),
                        ],
                      );
                    },
                  ),
                ),
              ),
              if (showLineChart)
                debugLayoutBorder(
                  label: 'Line chart',
                  child: LineChartModule(
                    height: _stickyLineChartHeight,
                    strokeWidth: 3,
                    lineColor: chartLineColor,
                    paddingBottom: 0,
                  ),
                ),
              if (buttonsWidget != null) SizedBox(height: _buttonsStripHeight),
            ],
          ],
        ),
        if (buttonsWidget != null)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: debugLayoutBorder(
              label: 'Boutons',
              child: buttonsWidget,
            ),
          ),
      ],
    );
    if (interactionOnly) {
      return Opacity(opacity: 0, child: stack);
    }
    return stack;
  }
}

/// Header 2 : overlay par-dessus le Header 1, avec les zones interactives au premier plan.
/// Ordre des couches (arrière → premier plan) : base Header 2 → navbar → balance → période → line chart → boutons.
class WalletHeaderHitOverlay extends StatelessWidget {
  const WalletHeaderHitOverlay({
    super.key,
    required this.headerHeight,
    this.periodLabel = 'All time',
    this.onAvatarTap,
    this.onNotificationTap,
    this.onPeriodTap,
    this.onBalanceTap,
    this.onChartTap,
    this.onDeposit,
    this.onSend,
    this.onBuy,
    this.onMore,
    this.showBackButton = false,
    this.onBackTap,
  });

  final double headerHeight;
  final String periodLabel;
  final VoidCallback? onAvatarTap;
  final VoidCallback? onNotificationTap;
  final VoidCallback? onPeriodTap;
  final VoidCallback? onBalanceTap;
  final VoidCallback? onChartTap;
  final VoidCallback? onDeposit;
  final VoidCallback? onSend;
  final VoidCallback? onBuy;
  final VoidCallback? onMore;
  /// Si true, seule la zone Retour (gauche) est active dans la navbar de l'overlay.
  final bool showBackButton;
  final VoidCallback? onBackTap;

  static const double _navbarHeight = walletHeaderNavBarHeight;
  static const double _avatarWidth = 40;
  /// Même taille que _NavBarIconDisk (diskSize = 40) pour alignement zone clic / visuel.
  static const double _iconSize = 40;

  /// Même structure que le header : Spacer, bloc Balance (100px), gap 12, chart.
  /// Hauteur réelle du module Balance avec le bloc bleu : titre ~17 + montant ~52 + bloc période ~26 = 95px.
  /// Overlay 100px → commence 2.5px au-dessus du module réel. Bloc période à 69px du haut du module réel.
  /// En coords overlay : 69 - 2.5 = 66.5. Hauteur bloc bleu = 26 (padding 4+4 + ligne ~18).
  static const double _balanceModuleHeight = 100;
  static const double _gapBalanceChart = 12;
  /// Header : Spacer + balance + Spacer + gap + chart(50%) → balance dans le premier quart, pas au centre.
  static const double _balancePositionFactor = 0.25;
  static const double _periodRowOffsetFromTop = 67;
  static const double _periodRowHeight = 26;
  /// Largeur proche du bloc bleu "0% · All time" + caret pour alignement visuel (tap confortable).
  static const double _periodHitWidth = 180;

  /// Hauteur en bas du header pour la ligne de boutons (Déposer, Envoyer, etc.). Capturée par l'overlay au premier plan.
  static const double _actionButtonsStripHeight = 120;

  @override
  Widget build(BuildContext context) {
    final topPadding = MediaQuery.paddingOf(context).top;
    final bottomPadding = MediaQuery.paddingOf(context).bottom;
    // Stack : base IgnorePointer pour que tout tap non capté passe au scroll (titres, etc.).
    // Aligner sur le header : le header utilise SafeArea(top: false) pour les boutons, donc la zone
    // étendue (balance + période) est réduite d’autant en bas — on soustrait bottomPadding pour que
    // la zone période « 0% All time » soit au bon endroit.
    final expandedHeight = headerHeight - topPadding - _navbarHeight - _actionButtonsStripHeight - bottomPadding;
    final incompressibleHeight = _balanceModuleHeight + _gapBalanceChart;
    final balanceTop = topPadding + _navbarHeight + (expandedHeight - incompressibleHeight) * _balancePositionFactor;
    final periodTop = balanceTop + _periodRowOffsetFromTop;
    final chartTop = balanceTop + _balanceModuleHeight + _gapBalanceChart;
    final chartHeight = ((expandedHeight - _gapBalanceChart - _balanceModuleHeight) * 0.50).clamp(0.0, double.infinity);

    return SizedBox(
      height: headerHeight,
      width: double.infinity,
      child: Stack(
        children: [
          // 1 — Base Header 2 (taps passent au scroll si non captés)
          IgnorePointer(child: SizedBox.expand()),
          // 2 — Navbar au premier plan
          Positioned(
            top: topPadding,
            left: 0,
            right: 0,
            height: _navbarHeight,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: _navbarHorizontalMargin),
              child: Row(
                children: [
                  if (showBackButton)
                    if (onBackTap != null)
                      Semantics(
                        button: true,
                        label: 'Retour',
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: onBackTap,
                          child: const SizedBox(width: _avatarWidth, height: _navbarHeight),
                        ),
                      )
                    else
                      const SizedBox(width: _avatarWidth, height: _navbarHeight)
                  else ...[
                    if (onAvatarTap != null)
                      Semantics(
                        button: true,
                        label: 'Profil',
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: onAvatarTap,
                          child: const SizedBox(width: _avatarWidth, height: _navbarHeight),
                        ),
                      )
                    else
                      const SizedBox(width: _avatarWidth, height: _navbarHeight),
                    const Spacer(),
                    Semantics(
                      button: true,
                      label: 'Graphique',
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () {},
                        child: const SizedBox(width: _iconSize, height: _navbarHeight),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (onNotificationTap != null)
                      Semantics(
                        button: true,
                        label: 'Notifications',
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: onNotificationTap,
                          child: const SizedBox(width: _iconSize, height: _navbarHeight),
                        ),
                      )
                    else
                      const SizedBox(width: _iconSize, height: _navbarHeight),
                  ],
                ],
              ),
            ),
          ),
          // 3 — Module Balance au premier plan
          if (onBalanceTap != null)
            Positioned(
              top: balanceTop,
              left: 0,
              right: 0,
              height: _balanceModuleHeight,
              child: Center(
                child: Semantics(
                  button: true,
                  label: 'Balance',
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: onBalanceTap,
                    child: const SizedBox(width: 220, height: _balanceModuleHeight),
                  ),
                ),
              ),
            ),
          // 4 — Période (0% · All time) au premier plan
          if (onPeriodTap != null)
            Positioned(
              top: periodTop,
              left: 0,
              right: 0,
              height: _periodRowHeight,
              child: Center(
                child: Semantics(
                  button: true,
                  label: 'Période $periodLabel',
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: onPeriodTap,
                    child: SizedBox(
                      width: _periodHitWidth,
                      height: _periodRowHeight,
                    ),
                  ),
                ),
              ),
            ),
          // Bande des boutons d’action (Déposer, Envoyer, Acheter, Plus) — Header 2 au premier plan
          // Alignée sur le header : le header utilise SafeArea(top: false) donc les boutons sont au-dessus du safe inset.
          if (onChartTap != null && chartHeight > 0)
            Positioned(
              top: chartTop,
              left: 0,
              right: 0,
              height: chartHeight,
              child: Semantics(
                button: true,
                label: 'Graphique de performance',
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: onChartTap,
                  child: const SizedBox.expand(),
                ),
              ),
            ),
          Positioned(
            left: 0,
            right: 0,
            bottom: MediaQuery.paddingOf(context).bottom,
            height: _actionButtonsStripHeight,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: _navbarHorizontalMargin),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: _navbarHorizontalMargin, vertical: 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  mainAxisSize: MainAxisSize.max,
                  children: [
                    _overlayActionZone(onTap: onDeposit, semanticsLabel: 'Déposer'),
                    _overlayActionZone(onTap: onSend, semanticsLabel: 'Envoyer'),
                    _overlayActionZone(onTap: onBuy, semanticsLabel: 'Acheter'),
                    _overlayActionZone(onTap: onMore, semanticsLabel: 'Plus'),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Taille du bouton rond (alignée sur [ButtonRounded] dans le Header 1).
  static const double _actionButtonSize = 60;

  Widget _overlayActionZone({required VoidCallback? onTap, required String semanticsLabel}) {
    if (onTap == null) return const SizedBox.shrink();
    return Center(
      child: Semantics(
        button: true,
        label: semanticsLabel,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            customBorder: const CircleBorder(),
            splashColor: Colors.white.withValues(alpha: 0.25),
            highlightColor: Colors.white.withValues(alpha: 0.15),
            child: const SizedBox(width: _actionButtonSize, height: _actionButtonSize),
          ),
        ),
      ),
    );
  }
}

/// Navbar seule (avatar + icônes). À positionner en hauteur fixe [walletHeaderNavBarHeight] pour qu’elle reste fixe au hot refresh.
class WalletHeaderNavBar extends StatelessWidget {
  const WalletHeaderNavBar({
    super.key,
    required this.progress,
    this.showProfile = true,
    this.showBackButton = false,
    this.showStatistics = true,
    this.showNotifications = true,
    this.showAvatarDot = true,
    this.onAvatarTap,
    this.onBackTap,
    this.onNotificationTap,
    this.showNotificationDot = false,
    this.leadingMode,
    this.customRightActions,
  });

  final double progress;
  final bool showProfile;
  final bool showBackButton;
  final bool showStatistics;
  final bool showNotifications;
  final bool showAvatarDot;
  final VoidCallback? onAvatarTap;
  final VoidCallback? onBackTap;
  final VoidCallback? onNotificationTap;
  final bool showNotificationDot;
  /// Mode leading personnalisé. Si null, utilise le comportement legacy (showBackButton/showProfile).
  final WalletHeaderNavLeadingMode? leadingMode;
  /// Actions droites personnalisées. Si non null, remplace le comportement legacy (statistics/notifications).
  final List<WalletHeaderNavAction>? customRightActions;

  @override
  Widget build(BuildContext context) {
    final topInset = MediaQuery.paddingOf(context).top;
    final topBarOpaque = progress >= _collapseThreshold;
    final barBg = topBarOpaque
        ? AppColors.walletAppBarBg.withValues(alpha: 0.08)
        : Colors.white.withValues(alpha: 0);
    final blurTint = Colors.black.withValues(alpha: topBarOpaque ? 0.24 : 0.14);
    final fgColor = topBarOpaque ? AppColors.walletAppBarFg : Colors.white;
    final useCustomLeading = leadingMode != null;
    final useCustomRightActions = customRightActions != null;

    Widget buildLeading() {
      if (useCustomLeading) {
        switch (leadingMode!) {
          case WalletHeaderNavLeadingMode.back:
            return _NavBarIconDisk(
              icon: Icons.arrow_back_ios_new_rounded,
              foregroundColor: fgColor,
              onPressed: onBackTap,
              iconSize: 20,
            );
          case WalletHeaderNavLeadingMode.profile:
            return _TopBarAvatar(
              foregroundColor: fgColor,
              showDot: showAvatarDot,
              onTap: onAvatarTap,
            );
          case WalletHeaderNavLeadingMode.none:
            return const SizedBox(width: 40, height: 40);
        }
      }

      if (showBackButton) {
        return _NavBarIconDisk(
          icon: Icons.arrow_back_ios_new_rounded,
          foregroundColor: fgColor,
          onPressed: onBackTap,
          iconSize: 20,
        );
      }
      if (showProfile) {
        return _TopBarAvatar(
          foregroundColor: fgColor,
          showDot: showAvatarDot,
          onTap: onAvatarTap,
        );
      }
      return const SizedBox(width: 40, height: 40);
    }

    List<Widget> buildRightActions() {
      if (useCustomRightActions) {
        final actions = customRightActions!;
        if (actions.isEmpty) return const [];
        final out = <Widget>[];
        for (int i = 0; i < actions.length; i++) {
          final action = actions[i];
          out.add(
            _NavBarIconDisk(
              icon: action.icon,
              foregroundColor: action.foregroundColor ?? fgColor,
              onPressed: action.onPressed,
              showDot: action.showDot,
              iconSize: action.iconSize,
            ),
          );
          if (i < actions.length - 1) {
            out.add(const SizedBox(width: 8));
          }
        }
        return out;
      }

      final out = <Widget>[];
      if (showStatistics) {
        out.add(
          _NavBarIconDisk(
            icon: Icons.bar_chart_rounded,
            foregroundColor: fgColor,
            onPressed: () {},
          ),
        );
      }
      if (showStatistics && showNotifications) {
        out.add(const SizedBox(width: 8));
      }
      if (showNotifications) {
        out.add(
          _NavBarIconDisk(
            icon: Icons.notifications_outlined,
            foregroundColor: fgColor,
            onPressed: onNotificationTap,
            showDot: showNotificationDot,
          ),
        );
      }
      return out;
    }

    return SizedBox(
      height: _navbarHeight + topInset,
      child: Stack(
        fit: StackFit.expand,
        children: [
          ClipRect(
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: _navbarBlurSigma,
                sigmaY: _navbarBlurSigma,
              ),
              child: Container(color: blurTint),
            ),
          ),
          if (barBg.opacity > 0) Container(color: barBg),
          Padding(
            padding: EdgeInsets.only(
              top: topInset,
              left: _navbarHorizontalMargin,
              right: _navbarHorizontalMargin,
            ),
            child: SizedBox(
              height: _navbarHeight,
              child: Row(
                children: [
                  buildLeading(),
                  const Spacer(),
                  ...buildRightActions(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

enum WalletHeaderNavLeadingMode {
  back,
  profile,
  none,
}

class WalletHeaderNavAction {
  const WalletHeaderNavAction({
    required this.icon,
    this.onPressed,
    this.showDot = false,
    this.iconSize = 24,
    this.foregroundColor,
  });

  final IconData icon;
  final VoidCallback? onPressed;
  final bool showDot;
  final double iconSize;
  final Color? foregroundColor;
}

/// Partie centrale + boutons (gradient + Balance + boutons). À animer en hauteur pour l’effet d’étirement au centre au hot refresh.
class WalletHeaderBody extends StatelessWidget {
  const WalletHeaderBody({
    super.key,
    required this.progress,
    this.balanceTitle = 'Balance',
    this.balanceAmount = '0 €',
    this.balanceAssetIcon,
    this.performanceText = '0 %',
    this.periodLabel = 'All time',
    this.actionButtons,
    this.moduleHorizontalMargin,
  });

  final double progress;
  final String balanceTitle;
  final String balanceAmount;
  /// Logo de l’asset à gauche du titre (ex. € pour Euro, BTC pour Bitcoin). Optionnel.
  final Widget? balanceAssetIcon;
  final String performanceText;
  final String periodLabel;
  final Widget? actionButtons;
  final double? moduleHorizontalMargin;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                _headerGradientStart,
                _headerGradientMid,
                _headerGradientEnd,
              ],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
        ),
        Column(
          children: [
            Expanded(
              child: Center(
                child: _BalanceModule(
                    title: balanceTitle,
                    amountFull: balanceAmount,
                    performanceText: performanceText,
                    periodLabel: periodLabel,
                    titleLeading: balanceAssetIcon,
                  ),
                ),
              ),
            if (actionButtons != null) _buildButtons(context)!,
          ],
        ),
      ],
    );
  }

  Widget? _buildButtons(BuildContext context) {
    if (actionButtons == null) return null;
    final content = Padding(
      padding: EdgeInsets.symmetric(horizontal: moduleHorizontalMargin ?? 0),
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: moduleHorizontalMargin ?? 0),
        child: ActionButtonModule(
          horizontalPadding: moduleHorizontalMargin != null ? 0 : null,
          child: actionButtons!,
        ),
      ),
    );
    return SafeArea(
      top: false,
      child: content,
    );
  }
}

/// Icône navbar dans un disque style Revolut (même rendu que les boutons d'action, diamètre adapté à l'icône).
class _NavBarIconDisk extends StatelessWidget {
  const _NavBarIconDisk({
    required this.icon,
    required this.foregroundColor,
    this.onPressed,
    this.showDot = false,
    this.diskSize = 40,
    this.iconSize = 24,
  });

  final IconData icon;
  final Color foregroundColor;
  final VoidCallback? onPressed;
  final bool showDot;
  final double diskSize;
  final double iconSize;

  static const double _glassBlurSigma = 20;

  @override
  Widget build(BuildContext context) {
    final radius = diskSize / 2;
    final disk = SizedBox(
      width: diskSize,
      height: diskSize,
      child: DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.22),
              blurRadius: 12,
              offset: const Offset(0, 5),
            ),
            BoxShadow(
              color: Colors.white.withValues(alpha: 0.16),
              blurRadius: 2,
              offset: const Offset(0, -1),
            ),
          ],
        ),
        child: ClipOval(
          child: Stack(
            fit: StackFit.expand,
            children: [
              BackdropFilter(
                filter: ImageFilter.blur(
                  sigmaX: _glassBlurSigma,
                  sigmaY: _glassBlurSigma,
                ),
                child: Container(color: Colors.white.withValues(alpha: 0.08)),
              ),
              DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.white.withValues(alpha: 0.34),
                      Colors.white.withValues(alpha: 0.18),
                    ],
                  ),
                ),
              ),
              // Contour externe lumineux.
              DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.56),
                    width: 1.4,
                  ),
                ),
              ),
              // Contour interne pour l'effet "verre épais".
              Padding(
                padding: const EdgeInsets.all(1.6),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.14),
                      width: 1,
                    ),
                  ),
                ),
              ),
              // Reflet supérieur façon Apple glass.
              Align(
                alignment: Alignment.topCenter,
                child: Container(
                  height: radius * 0.9,
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.white.withValues(alpha: 0.32),
                        Colors.white.withValues(alpha: 0),
                      ],
                    ),
                  ),
                ),
              ),
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: onPressed,
                  customBorder: const CircleBorder(),
                  splashColor: Colors.white.withValues(alpha: 0.18),
                  highlightColor: Colors.white.withValues(alpha: 0.08),
                  child: Icon(icon, size: iconSize, color: foregroundColor),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (!showDot) return disk;
    return Stack(
      clipBehavior: Clip.none,
      children: [
        disk,
        Positioned(
          top: 4,
          right: 4,
          child: Container(
            width: 10,
            height: 10,
            decoration: const BoxDecoration(
              color: Color(0xFF4FC3F7),
              shape: BoxShape.circle,
            ),
          ),
        ),
      ],
    );
  }
}

class _TopBarAvatar extends StatelessWidget {
  const _TopBarAvatar({
    required this.foregroundColor,
    this.showDot = true,
    this.onTap,
  });

  final Color foregroundColor;
  final bool showDot;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    const double size = 40;
    final radius = size / 2;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(radius),
      child: SizedBox(
        width: size,
        height: size,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            DecoratedBox(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.22),
                    blurRadius: 12,
                    offset: const Offset(0, 5),
                  ),
                  BoxShadow(
                    color: Colors.white.withValues(alpha: 0.16),
                    blurRadius: 2,
                    offset: const Offset(0, -1),
                  ),
                ],
              ),
              child: ClipOval(
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    BackdropFilter(
                      filter: ImageFilter.blur(
                        sigmaX: _NavBarIconDisk._glassBlurSigma,
                        sigmaY: _NavBarIconDisk._glassBlurSigma,
                      ),
                      child: Container(color: Colors.white.withValues(alpha: 0.08)),
                    ),
                    DecoratedBox(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            Colors.white.withValues(alpha: 0.34),
                            Colors.white.withValues(alpha: 0.18),
                          ],
                        ),
                      ),
                    ),
                    DecoratedBox(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.56),
                          width: 1.4,
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(1.6),
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.14),
                            width: 1,
                          ),
                        ),
                      ),
                    ),
                    Align(
                      alignment: Alignment.topCenter,
                      child: Container(
                        height: radius * 0.9,
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              Colors.white.withValues(alpha: 0.32),
                              Colors.white.withValues(alpha: 0),
                            ],
                          ),
                        ),
                      ),
                    ),
                    Center(
                      child: Text(
                        'JA',
                        style: TextStyle(
                          color: foregroundColor,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (showDot)
              Positioned(
                top: 0,
                right: 0,
                child: Container(
                  width: 10,
                  height: 10,
                  decoration: const BoxDecoration(
                    color: Color(0xFF4FC3F7),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

