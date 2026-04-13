import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Circular button used inside [SheetTitleBar].
///
/// Figma spec:
///   - Close button: white bg, shadow 0 0 20px rgba(0,0,0,0.12), radius 40px, 40x40px
///   - Add button: #6155F5 bg, same shadow/radius, white + icon
class SheetCircleButton extends StatelessWidget {
  const SheetCircleButton({
    super.key,
    required this.icon,
    this.backgroundColor = Colors.white,
    this.iconColor = const Color(0xFF727272),
    this.onTap,
  });

  final IconData icon;
  final Color backgroundColor;
  final Color iconColor;
  final VoidCallback? onTap;

  /// White-background close / dismiss variant.
  const SheetCircleButton.leading({
    super.key,
    this.icon = Icons.close_rounded,
    this.backgroundColor = Colors.white,
    this.iconColor = const Color(0xFF727272),
    this.onTap,
  });

  /// Indigo (primary) action variant – "add" button.
  const SheetCircleButton.trailing({
    super.key,
    required this.icon,
    this.backgroundColor = AppColors.indigo,
    this.iconColor = Colors.white,
    this.onTap,
  });

  static const double _size = 40;
  static const double _iconSize = 24;

  static const _shadow = BoxShadow(
    color: Color(0x1F000000),
    blurRadius: 20,
  );

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: _size,
        height: _size,
        decoration: BoxDecoration(
          color: backgroundColor,
          shape: BoxShape.circle,
          boxShadow: const [_shadow],
        ),
        alignment: Alignment.center,
        child: Icon(icon, size: _iconSize, color: iconColor),
      ),
    );
  }
}

/// Title bar for bottom sheets — centered title with optional circle buttons.
///
/// Figma spec:
/// - Title: 20px, w600, letterSpacing -0.45, color #1A1A1A
/// - Horizontal padding: 16px
/// - Leading / trailing: [SheetCircleButton] (44×44)
class SheetTitleBar extends StatelessWidget {
  const SheetTitleBar({
    super.key,
    this.title = '',
    this.leadingButton,
    this.trailingButton,
  });

  final String title;
  final Widget? leadingButton;
  final Widget? trailingButton;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      child: SizedBox(
        height: 60,
        child: Stack(
          alignment: Alignment.center,
          children: [
            if (title.isNotEmpty)
              Text(
                title,
                style: AppTypography.headerAppbar.copyWith(
                  color: const Color(0xFF1A1A1A),
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (leadingButton != null)
                  leadingButton!
                else
                  const SizedBox(width: 40),
                if (trailingButton != null)
                  trailingButton!
                else
                  const SizedBox(width: 40),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
