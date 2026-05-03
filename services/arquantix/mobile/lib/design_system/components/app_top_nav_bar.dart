import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../atoms/kalai_icons.dart';
import 'app_back_button.dart';
import 'kalai_icon.dart';

/// Type de contenu à gauche de la barre : retour ou profil (avatar).
enum AppTopNavBarLeading {
  back,
  profile,
  close,
}

/// Action à droite de la barre : icône dans un disque (style dashboard).
class AppTopNavBarAction {
  const AppTopNavBarAction({
    required this.icon,
    this.onPressed,
    this.showDot = false,
    this.iconColor,
  });
  final IconData icon;
  final VoidCallback? onPressed;
  final bool showDot;
  final Color? iconColor;
}

/// Figma `TopAppBar` : zone d’action 40×40, icône 24.
const double _diskSizeStandard = 40;
const double _iconSizeStandard = 24;
const double _diskSizeDashboard = 40;
const double _iconSizeDashboard = 24;

/// Barre de navigation supérieure réutilisable.
///
/// En mode dashboard ([useDashboardStyle] = true), tous les boutons utilisent
/// le composant DS [AppBackButton]. En mode standard, un simple disque opaque.
class AppTopNavBar extends StatelessWidget implements PreferredSizeWidget {
  const AppTopNavBar({
    super.key,
    required this.leadingType,
    this.title,
    this.onBackTap,
    this.onCloseTap,
    this.onProfileTap,
    this.profileInitials = 'JA',
    this.showProfileDot = false,
    this.actions = const [],
    this.backgroundColor,
    this.foregroundColor,
    this.useDashboardStyle = false,
    this.centerTitle = true,
    this.titleTextStyle,
    this.titleMaxLines = 1,
    this.titleOpacity = 1.0,
    this.closeLabel = 'Fermer',
  });

  final AppTopNavBarLeading leadingType;
  final String? title;
  final VoidCallback? onBackTap;
  final VoidCallback? onCloseTap;
  final VoidCallback? onProfileTap;
  final String profileInitials;
  final bool showProfileDot;
  final List<AppTopNavBarAction> actions;
  final Color? backgroundColor;
  final Color? foregroundColor;
  final bool useDashboardStyle;
  final bool centerTitle;
  final TextStyle? titleTextStyle;
  final int titleMaxLines;
  final double titleOpacity;
  final String closeLabel;

  /// Hauteur Figma `TopAppBar` : 60px.
  @override
  Size get preferredSize => const Size.fromHeight(60);

  @override
  Widget build(BuildContext context) {
    final bg = backgroundColor ?? AppColors.pageBackground;
    final fg = foregroundColor ?? AppColors.textPrimary;
    final diskSize = useDashboardStyle ? _diskSizeDashboard : _diskSizeStandard;

    const double navBarHorizontalMargin = AppSpacing.lg;
    return AppBar(
      toolbarHeight: 60,
      backgroundColor: bg,
      elevation: 0,
      scrolledUnderElevation: 0,
      leadingWidth: navBarHorizontalMargin + diskSize,
      leading: Padding(
        padding: const EdgeInsets.only(left: navBarHorizontalMargin),
        child: Center(child: _buildLeading(context, fg, diskSize)),
      ),
      title: title != null
          ? Opacity(
              opacity: titleOpacity.clamp(0.0, 1.0),
              child: Text(
                title!,
                style: titleTextStyle ??
                    AppTypography.headerAppbar.copyWith(color: fg),
                maxLines: titleMaxLines,
                overflow: TextOverflow.ellipsis,
              ),
            )
          : null,
      centerTitle: centerTitle,
      actions: actions.isEmpty
          ? null
          : [
              ...actions.map((a) => Padding(
                    padding: const EdgeInsets.only(right: navBarHorizontalMargin),
                    child: Center(child: _buildAction(context, a, fg, diskSize)),
                  )),
            ],
    );
  }

  // ─────────────── Leading ───────────────

  Widget _buildLeading(BuildContext context, Color fg, double diskSize) {
    switch (leadingType) {
      case AppTopNavBarLeading.back:
        return _buildNavButton(
          context,
          kalaiIcon: KalaiIcons.arrowLeft,
          fg: fg,
          diskSize: diskSize,
          onTap: onBackTap ?? () => Navigator.of(context).pop(),
        );
      case AppTopNavBarLeading.profile:
        return _buildProfile(context, fg, diskSize);
      case AppTopNavBarLeading.close:
        return _buildNavButton(
          context,
          kalaiIcon: KalaiIcons.clear,
          fg: fg,
          diskSize: diskSize,
          onTap: onCloseTap ?? () => Navigator.of(context).pop(),
        );
    }
  }

  // ─────────────── Unified nav button ───────────────

  Widget _buildNavButton(
    BuildContext context, {
    IconData? icon,
    String? kalaiIcon,
    required Color fg,
    Color? iconColor,
    required double diskSize,
    VoidCallback? onTap,
  }) {
    assert(
      icon != null || kalaiIcon != null,
      'Fournir soit `icon` (Material) soit `kalaiIcon` (KALAI).',
    );
    final effectiveIconColor = iconColor ?? fg;
    final iconWidget = kalaiIcon != null
        ? KalaiIcon(kalaiIcon,
            color: effectiveIconColor, size: _iconSizeDashboard)
        : Icon(icon, color: effectiveIconColor, size: _iconSizeDashboard);
    if (useDashboardStyle) {
      return AppBackButton(
        child: iconWidget,
        size: diskSize,
        onPressed: onTap,
        variant: AppBackButtonVariant.glass,
      );
    }
    return _standardDisk(
      iconWidget: iconWidget,
      fg: fg,
      diskSize: diskSize,
      onTap: onTap,
    );
  }

  // ─────────────── Actions ───────────────

  Widget _buildAction(
    BuildContext context,
    AppTopNavBarAction action,
    Color fg,
    double diskSize,
  ) {
    // [fg] sert au fond du disque (cohérent avec retour / autres actions).
    // [action.iconColor] ne colore que l’icône (ex. étoile favori), sans changer le disque.
    final button = _buildNavButton(
      context,
      icon: action.icon,
      fg: fg,
      iconColor: action.iconColor,
      diskSize: diskSize,
      onTap: action.onPressed,
    );

    if (!action.showDot) return button;
    return Stack(
      clipBehavior: Clip.none,
      children: [
        button,
        Positioned(
          top: 2,
          right: 2,
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

  // ─────────────── Profile ───────────────

  Widget _buildProfile(BuildContext context, Color fg, double diskSize) {
    if (useDashboardStyle) {
      final avatar = AppBackButton(
        child: Text(
          profileInitials,
          style: TextStyle(
            color: fg,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        size: diskSize,
        onPressed: onProfileTap,
        variant: AppBackButtonVariant.glass,
      );
      if (!showProfileDot) return avatar;
      return Stack(
        clipBehavior: Clip.none,
        children: [
          avatar,
          Positioned(
            top: 2,
            right: 2,
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

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onProfileTap,
        borderRadius: BorderRadius.circular(diskSize / 2),
        customBorder: const CircleBorder(),
        child: SizedBox(
          width: diskSize,
          height: diskSize,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Center(
                child: CircleAvatar(
                  radius: diskSize / 2,
                  backgroundColor: fg.withValues(alpha: 0.2),
                  child: Text(
                    profileInitials,
                    style: TextStyle(
                      color: fg,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              if (showProfileDot)
                Positioned(
                  top: 2,
                  right: 2,
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
      ),
    );
  }

  // ─────────────── Standard opaque disk (non-dashboard) ───────────────

  Widget _standardDisk({
    required Widget iconWidget,
    required Color fg,
    required double diskSize,
    VoidCallback? onTap,
  }) {
    // Toujours dériver le fond du disque du ton de la barre ([fg]), pas de la couleur d’icône.
    final isLightFg = fg.computeLuminance() > 0.5;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(diskSize / 2),
        customBorder: const CircleBorder(),
        child: Container(
          width: diskSize,
          height: diskSize,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isLightFg
                ? Colors.white.withValues(alpha: 0.22)
                : AppColors.cardBackground,
          ),
          alignment: Alignment.center,
          // L'icône fournie est déjà dimensionnée (KalaiIcon ou Icon, _iconSizeDashboard).
          // Pour la variante non-dashboard on conserve une taille standard via FittedBox
          // pour ne pas casser la mise en page existante.
          child: SizedBox(
            width: _iconSizeStandard,
            height: _iconSizeStandard,
            child: FittedBox(fit: BoxFit.contain, child: iconWidget),
          ),
        ),
      ),
    );
  }
}
