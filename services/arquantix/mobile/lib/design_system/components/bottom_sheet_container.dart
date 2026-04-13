import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/grabber.dart';

/// Marge horizontale des feuilles « flottantes » (overlay : succès trade, erreur OTP, [Modale]).
const double kFloatingSheetHorizontalInset = 7;

/// Marge basse par rapport au bord de l’écran pour ces feuilles.
const double kFloatingSheetBottomInset = 8;

/// Reusable container shell for all DS bottom sheets.
///
/// Figma spec:
/// - `borderRadius`: top 32, bottom 60
/// - `backgroundColor`: white (cardBackground)
/// - `padding`: bottom 40
/// - `gap`: 24px between children (Figma `BottomSheet`)
/// - Includes [Grabber] at the very top
class BottomSheetContainer extends StatelessWidget {
  const BottomSheetContainer({
    super.key,
    this.toolbar,
    this.children = const [],
    this.backgroundColor,
    this.showGrabber = true,
  });

  /// Optional toolbar widget rendered between the grabber and children.
  final Widget? toolbar;

  /// Content widgets separated by 16px gaps.
  final List<Widget> children;

  /// Defaults to [AppColors.cardBackground].
  final Color? backgroundColor;

  /// Whether to show the drag handle at the top.
  final bool showGrabber;

  static const _topRadius = Radius.circular(32);
  static const _bottomRadius = Radius.circular(60);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: backgroundColor ?? AppColors.cardBackground,
        borderRadius: const BorderRadius.only(
          topLeft: _topRadius,
          topRight: _topRadius,
          bottomLeft: _bottomRadius,
          bottomRight: _bottomRadius,
        ),
      ),
      padding: const EdgeInsets.only(bottom: AppSpacing.s10),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showGrabber) const Grabber(),
          if (toolbar != null) toolbar!,
          for (int i = 0; i < children.length; i++) ...[
            if (i > 0 || toolbar != null) const SizedBox(height: AppSpacing.s6),
            children[i],
          ],
        ],
      ),
    );
  }
}
