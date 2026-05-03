import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/kalai_icons.dart';
import 'kalai_icon.dart';

/// Variante visuelle du [AppSnackbar].
enum AppSnackbarVariant {
  /// Fond blanc, texte noir, icône action #C7C7CC.
  light,

  /// Fond noir, texte blanc, icône action #48484A.
  dark,

  /// Fond warning (#FF8D28), texte blanc, icône action #FFF4E9.
  warning,
}

/// Action trailing du [AppSnackbar].
enum AppSnackbarAction {
  /// Chevron droit (navigation).
  chevron,

  /// Croix (dismiss).
  close,
}

/// Notification single-ligne en forme de pill.
///
/// Figma spec:
/// - Min height: 47px
/// - Border radius: 9999px (pill)
/// - Shadow: 0px 0px 20px rgba(0,0,0,0.12)
/// - Padding: 16px left, 8px right, 8px vertical
/// - Gap: 8px
/// - Inter Regular 13px, line-height 18, tracking -0.08
class AppSnackbar extends StatelessWidget {
  const AppSnackbar({
    super.key,
    required this.text,
    this.variant = AppSnackbarVariant.light,
    this.action,
    this.icon,
    this.actionButton,
    this.onActionTap,
    this.onTap,
  });

  final String text;
  final AppSnackbarVariant variant;
  final AppSnackbarAction? action;
  final Widget? icon;
  final Widget? actionButton;
  final VoidCallback? onActionTap;
  final VoidCallback? onTap;

  static const double _minHeight = 47;
  static const double _pillRadius = 9999;

  static const _shadow = BoxShadow(
    color: Color(0x1F000000),
    blurRadius: 20,
  );

  static const _textStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    height: 18 / 13,
    letterSpacing: -0.08,
  );

  Color get _backgroundColor => switch (variant) {
        AppSnackbarVariant.light => AppColors.white,
        AppSnackbarVariant.dark => AppColors.black,
        AppSnackbarVariant.warning => AppColors.semanticWarning,
      };

  Color get _textColor => switch (variant) {
        AppSnackbarVariant.light => AppColors.black,
        AppSnackbarVariant.dark => AppColors.white,
        AppSnackbarVariant.warning => AppColors.white,
      };

  Color get _actionIconColor => switch (variant) {
        AppSnackbarVariant.light => const Color(0xFFC7C7CC),
        AppSnackbarVariant.dark => const Color(0xFF48484A),
        AppSnackbarVariant.warning => AppColors.semanticWarningLight,
      };

  @override
  Widget build(BuildContext context) {
    final style = GoogleFonts.inter(textStyle: _textStyle);

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        constraints: const BoxConstraints(minHeight: _minHeight),
        decoration: BoxDecoration(
          color: _backgroundColor,
          borderRadius: BorderRadius.circular(_pillRadius),
          boxShadow: const [_shadow],
        ),
        padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
        child: Row(
          children: [
            if (icon != null) ...[
              icon!,
              const SizedBox(width: 8),
            ],
            Expanded(
              child: Text(
                text,
                style: style.copyWith(color: _textColor),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (actionButton != null) ...[
              const SizedBox(width: 8),
              actionButton!,
            ],
            if (action != null && actionButton == null) ...[
              const SizedBox(width: 8),
              _buildActionIcon(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionIcon() {
    final assetPath = switch (action!) {
      AppSnackbarAction.chevron => KalaiIcons.chevronRight,
      AppSnackbarAction.close => KalaiIcons.clear,
    };

    return GestureDetector(
      onTap: onActionTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 16,
        height: 16,
        child: KalaiIcon(assetPath, size: 16, color: _actionIconColor),
      ),
    );
  }
}
