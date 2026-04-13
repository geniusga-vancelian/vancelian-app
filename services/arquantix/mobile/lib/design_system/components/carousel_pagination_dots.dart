import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';

/// Bullets de pagination pour carrousels (même rendu que l’ancien module marketing sliding).
class CarouselPaginationDots extends StatelessWidget {
  const CarouselPaginationDots({
    super.key,
    required this.count,
    required this.activeIndex,
    this.dotSize = 8,
    this.dotSpacing = 6,
  });

  final int count;
  final int activeIndex;
  final double dotSize;
  final double dotSpacing;

  @override
  Widget build(BuildContext context) {
    if (count <= 1) return const SizedBox.shrink();
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(
        count,
        (index) => _Dot(
          isActive: index == activeIndex,
          size: dotSize,
          spacing: dotSpacing,
        ),
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({
    required this.isActive,
    required this.size,
    required this.spacing,
  });

  final bool isActive;
  final double size;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      margin: EdgeInsets.symmetric(horizontal: spacing / 2),
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: isActive
            ? AppColors.textPrimary
            : AppColors.textPrimary.withValues(alpha: 0.25),
      ),
    );
  }
}
