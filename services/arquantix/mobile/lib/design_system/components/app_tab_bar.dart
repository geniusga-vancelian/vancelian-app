import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Data for a single tab in [AppTabBar].
class AppTabBarItemData {
  const AppTabBarItemData({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;
}

/// iOS-style bottom tab bar with glassmorphism and sliding pill animation.
///
/// Pill-shaped glass bar containing overlapping tabs, plus an optional
/// circular glass action button (e.g. search).
///
/// When the selected tab changes, a white pill slides smoothly
/// to the new position, and icon/label colors cross-fade.
///
/// Figma tokens:
/// - Bar: 54px height, radius 40, bg rgba(235,235,245,0.3), blur 12
/// - Active tab: bg white, text/icon #6155F5
/// - Inactive tab: transparent, text/icon black
/// - Item overlap: -10px
/// - Action button: 52×52, same glass bg
/// - Label: SemiBold 11px / lh 12 / w 54
/// - Icon: 20px
/// - Gap icon↔label: 2px
/// - Gap bar↔action: 8px
/// - Container: px 16, pb 8
class AppTabBar extends StatelessWidget {
  const AppTabBar({
    super.key,
    required this.items,
    required this.selectedIndex,
    required this.onTap,
    this.actionIcon,
    this.onActionTap,
    this.activeColor,
    this.inactiveColor,
  });

  final List<AppTabBarItemData> items;
  final int selectedIndex;
  final ValueChanged<int> onTap;
  final IconData? actionIcon;
  final VoidCallback? onActionTap;
  final Color? activeColor;
  final Color? inactiveColor;

  static const double barHeight = 54;
  static const double _barRadius = 40;
  static const double _blur = 12;
  static const double _actionSize = 52;
  static const double _iconSize = 20;
  static const double _barActionGap = 8;
  static const double _itemOverlap = 10;
  static const double containerPaddingBottom = 8;
  static const double _containerPaddingH = 16;

  /// rgba(235, 235, 245, 0.3) — Figma glass background.
  static const Color _glassBg = Color(0x4DEBEBF5);

  static double totalHeight(double bottomSafeArea) =>
      barHeight + containerPaddingBottom + bottomSafeArea;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        _containerPaddingH,
        0,
        _containerPaddingH,
        containerPaddingBottom,
      ),
      child: Row(
        children: [
          Expanded(child: _buildBar()),
          if (actionIcon != null) ...[
            const SizedBox(width: _barActionGap),
            _buildAction(),
          ],
        ],
      ),
    );
  }

  Widget _buildBar() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(_barRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
        child: Container(
          height: barHeight,
          decoration: BoxDecoration(
            color: _glassBg,
            borderRadius: BorderRadius.circular(_barRadius),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final totalOverlapPx = _itemOverlap * (items.length - 1);
              final itemWidth =
                  (constraints.maxWidth + totalOverlapPx) / items.length;
              final activeIdx = selectedIndex.clamp(0, items.length - 1);
              final activeLeft = activeIdx * (itemWidth - _itemOverlap);

              return Stack(
                clipBehavior: Clip.none,
                children: [
                  AnimatedPositioned(
                    duration: AppMotion.base,
                    curve: AppMotion.standard,
                    left: activeLeft,
                    width: itemWidth,
                    top: 0,
                    bottom: 0,
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(_barRadius),
                      ),
                    ),
                  ),
                  for (int i = 0; i < items.length; i++)
                    Positioned(
                      left: i * (itemWidth - _itemOverlap),
                      width: itemWidth,
                      top: 0,
                      bottom: 0,
                      child: _TabItem(
                        icon: items[i].icon,
                        label: items[i].label,
                        isActive: i == activeIdx,
                        activeColor: activeColor ?? AppColors.indigo,
                        inactiveColor: inactiveColor ?? AppColors.black,
                        onTap: () => onTap(i),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildAction() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(_barRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
        child: Material(
          color: _glassBg,
          borderRadius: BorderRadius.circular(_barRadius),
          child: InkWell(
            onTap: onActionTap,
            borderRadius: BorderRadius.circular(_barRadius),
            child: SizedBox(
              width: _actionSize,
              height: _actionSize,
              child: Center(
                child: Icon(
                  actionIcon,
                  size: _iconSize,
                  color: inactiveColor ?? AppColors.black,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Single tab item — transparent background, animated color.
/// The active pill is rendered separately in the parent [Stack].
class _TabItem extends StatelessWidget {
  const _TabItem({
    required this.icon,
    required this.label,
    required this.isActive,
    required this.activeColor,
    required this.inactiveColor,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool isActive;
  final Color activeColor;
  final Color inactiveColor;
  final VoidCallback onTap;

  static const double _iconSize = 20;
  static const double _iconLabelGap = 2;

  @override
  Widget build(BuildContext context) {
    final targetColor = isActive ? activeColor : inactiveColor;

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: targetColor),
        duration: AppMotion.base,
        curve: AppMotion.standard,
        builder: (context, color, _) {
          return Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: _iconSize, color: color),
              const SizedBox(height: _iconLabelGap),
              Text(
                label,
                style: AppTypography.labelEmphasized.copyWith(color: color),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
              ),
            ],
          );
        },
      ),
    );
  }
}
