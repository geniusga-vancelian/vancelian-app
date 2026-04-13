import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Variante visuelle du [AppToast].
enum AppToastVariant {
  /// Fond blanc, texte noir.
  light,

  /// Fond noir, texte blanc.
  dark,

  /// Fond warning (#FF8D28), texte blanc.
  warning,
}

/// Layout du [AppToast].
enum AppToastLayout {
  /// Icon + texte + bouton sur une seule ligne.
  horizontal,

  /// Icon + texte en haut, bouton en bas aligné à droite.
  vertical,
}

/// Notification multi-ligne avec titre et sous-titre.
///
/// Figma spec:
/// - Min height: 47px
/// - Border radius: 16px
/// - Shadow: 0px 0px 20px rgba(0,0,0,0.12)
/// - Padding: 16px left, 8px right, 8px vertical
/// - Gap: 8px
/// - Text gap: 4px (entre titre et sous-titre)
/// - Icon: 24px
/// - Title: Inter SemiBold 13px, line-height 18, tracking -0.08
/// - Subtitle: Inter Regular 13px, line-height 18, tracking -0.08
class AppToast extends StatelessWidget {
  const AppToast({
    super.key,
    required this.title,
    this.subtitle,
    this.variant = AppToastVariant.light,
    this.layout = AppToastLayout.horizontal,
    this.icon,
    this.actionButton,
    this.onTap,
  });

  final String title;
  final String? subtitle;
  final AppToastVariant variant;
  final AppToastLayout layout;
  final Widget? icon;
  final Widget? actionButton;
  final VoidCallback? onTap;

  static const double _minHeight = 47;
  static const double _radius = 16;

  static const _shadow = BoxShadow(
    color: Color(0x1F000000),
    blurRadius: 20,
  );

  static const _titleStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w600,
    height: 18 / 13,
    letterSpacing: -0.08,
  );

  static const _subtitleStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    height: 18 / 13,
    letterSpacing: -0.08,
  );

  Color get _backgroundColor => switch (variant) {
        AppToastVariant.light => AppColors.white,
        AppToastVariant.dark => AppColors.black,
        AppToastVariant.warning => AppColors.semanticWarning,
      };

  Color get _textColor => switch (variant) {
        AppToastVariant.light => AppColors.black,
        AppToastVariant.dark => AppColors.white,
        AppToastVariant.warning => AppColors.white,
      };

  @override
  Widget build(BuildContext context) {
    final titleS = GoogleFonts.inter(textStyle: _titleStyle);
    final subtitleS = GoogleFonts.inter(textStyle: _subtitleStyle);

    final textContent = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(title, style: titleS.copyWith(color: _textColor)),
        if (subtitle != null) ...[
          const SizedBox(height: 4),
          Text(subtitle!, style: subtitleS.copyWith(color: _textColor)),
        ],
      ],
    );

    final iconAndText = Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (icon != null) ...[
          icon!,
          const SizedBox(width: 8),
        ],
        Expanded(child: textContent),
      ],
    );

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        constraints: const BoxConstraints(minHeight: _minHeight),
        decoration: BoxDecoration(
          color: _backgroundColor,
          borderRadius: BorderRadius.circular(_radius),
          boxShadow: const [_shadow],
        ),
        padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
        child: layout == AppToastLayout.vertical
            ? _buildVertical(iconAndText)
            : _buildHorizontal(iconAndText),
      ),
    );
  }

  Widget _buildHorizontal(Widget iconAndText) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(child: iconAndText),
        if (actionButton != null) ...[
          const SizedBox(width: 8),
          actionButton!,
        ],
      ],
    );
  }

  Widget _buildVertical(Widget iconAndText) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        iconAndText,
        if (actionButton != null) ...[
          const SizedBox(height: 8),
          actionButton!,
        ],
      ],
    );
  }
}
