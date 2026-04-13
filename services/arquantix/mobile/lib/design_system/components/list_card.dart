import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Rounded-square icon container for [ListCard].
///
/// Figma: default 36×36, radius 10, bg #E5E5EA, padding 10.
class IconContainer extends StatelessWidget {
  const IconContainer({
    super.key,
    required this.child,
    this.size = IconContainerSize.md,
    this.backgroundColor,
    this.borderRadius = 10,
  });

  final Widget child;
  final IconContainerSize size;
  final Color? backgroundColor;
  final double borderRadius;

  double get _dimension => switch (size) {
        IconContainerSize.sm => 28,
        IconContainerSize.md => 36,
        IconContainerSize.lg => 44,
      };

  @override
  Widget build(BuildContext context) {
    return Container(
      width: _dimension,
      height: _dimension,
      decoration: BoxDecoration(
        color: backgroundColor ?? const Color(0xFFE5E5EA),
        borderRadius: BorderRadius.circular(borderRadius),
      ),
      alignment: Alignment.center,
      child: child,
    );
  }
}

enum IconContainerSize { sm, md, lg }

/// Small chevron-right indicator for list rows.
///
/// Figma: 12×12, stroke #AEAEB2.
class ChevronRight extends StatelessWidget {
  const ChevronRight({
    super.key,
    this.color = const Color(0xFFAEAEB2),
    this.size = 12,
  });

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Icon(
      Icons.chevron_right_rounded,
      size: size + 4,
      color: color,
    );
  }
}

/// Standalone list card with icon, title, optional description and chevron.
///
/// Figma specs:
/// - Radius 16, padding 16, white bg
/// - Shadow: 0 0 20 -10 rgba(0,0,0,0.12)
/// - Title: 15px semi-bold, black, tracking -0.23
/// - Description: 12px regular, #8E8E93
class ListCard extends StatelessWidget {
  const ListCard({
    super.key,
    required this.icon,
    required this.title,
    this.description,
    this.onTap,
    this.showChevron = true,
    this.hasShadow = true,
    this.backgroundColor,
  });

  final Widget icon;
  final String title;
  final String? description;
  final VoidCallback? onTap;
  final bool showChevron;
  final bool hasShadow;
  final Color? backgroundColor;

  static const double _radius = 16;
  static const double _padding = 16;
  static const double _gap = 16;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(_padding),
        decoration: BoxDecoration(
          color: backgroundColor ?? AppColors.cardBackground,
          borderRadius: BorderRadius.circular(_radius),
          boxShadow: hasShadow
              ? const [
                  BoxShadow(
                    color: Color(0x1F000000),
                    blurRadius: 20,
                    spreadRadius: -10,
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            icon,
            const SizedBox(width: _gap),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: AppTypography.bodyEmphasized.copyWith(
                      fontSize: 15,
                      height: 20 / 15,
                      letterSpacing: -0.23,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (description != null)
                    Text(
                      description!,
                      style: AppTypography.itemSupporting.copyWith(
                        color: const Color(0xFF8E8E93),
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            ),
            if (showChevron) ...[
              const SizedBox(width: 8),
              const ChevronRight(),
            ],
          ],
        ),
      ),
    );
  }
}
