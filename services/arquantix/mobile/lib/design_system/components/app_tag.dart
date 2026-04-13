import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Tag variant for [AppTag].
enum AppTagVariant { article, performance, semantic, image }

/// Trend direction for the performance variant.
enum AppTagTrend { up, down, none }

/// Tag/label component with 4 variants matching Figma spec.
///
/// Figma spec:
///   - Border-radius: 8px, padding: 6px horizontal / 8px vertical
///   - Font: Inter SemiBold 11px, tracking 0.06px
///   - Backdrop blur: 12px
///   - Article: white bg, black text, optional red dot (4px)
///   - Performance: rgba(235,235,245,0.3) bg, white text, trend icon
///   - Semantic: custom bg/text color, optional +/- icons
///   - Image: rgba(60,60,67,0.6) bg, white text
class AppTag extends StatelessWidget {
  const AppTag({
    super.key,
    required this.label,
    this.variant = AppTagVariant.article,
    this.color,
    this.textColor,
    this.showDot = false,
    this.trend = AppTagTrend.none,
    this.value,
    this.showIcon = false,
  });

  final String label;
  final AppTagVariant variant;
  final Color? color;
  final Color? textColor;
  final bool showDot;
  final AppTagTrend trend;
  final String? value;
  final bool showIcon;

  static const _trendUp = Color(0xFF34C759);
  static const _trendDown = Color(0xFFFF3B30);

  Color get _bgColor {
    switch (variant) {
      case AppTagVariant.article:
        return Colors.white;
      case AppTagVariant.performance:
        return const Color(0x4DEBEBF5);
      case AppTagVariant.semantic:
        return color ?? const Color(0xFF6155F5);
      case AppTagVariant.image:
        return const Color(0x993C3C43);
    }
  }

  Color get _fgColor {
    switch (variant) {
      case AppTagVariant.article:
        return textColor ?? Colors.black;
      case AppTagVariant.performance:
        return Colors.white;
      case AppTagVariant.semantic:
        return textColor ?? Colors.white;
      case AppTagVariant.image:
        return Colors.white;
    }
  }

  bool get _useBlur =>
      variant == AppTagVariant.performance || variant == AppTagVariant.image;

  @override
  Widget build(BuildContext context) {
    Widget child = Container(
      decoration: BoxDecoration(
        color: _bgColor,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot && variant == AppTagVariant.article) ...[
            Container(
              width: 4,
              height: 4,
              decoration: const BoxDecoration(
                color: Color(0xFFFF3B30),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
          ],
          if (variant == AppTagVariant.performance && trend != AppTagTrend.none) ...[
            Icon(
              trend == AppTagTrend.up
                  ? Icons.arrow_upward_rounded
                  : Icons.arrow_downward_rounded,
              size: 12,
              color: trend == AppTagTrend.up ? _trendUp : _trendDown,
            ),
            const SizedBox(width: 2),
          ],
          if (showIcon && variant == AppTagVariant.semantic) ...[
            Icon(Icons.add_rounded, size: 12, color: _fgColor),
            const SizedBox(width: 2),
          ],
          Text(
            value != null ? '$label $value' : label,
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              height: 13 / 11,
              letterSpacing: 0.06,
              color: _fgColor,
            ),
          ),
        ],
      ),
    );

    if (_useBlur) {
      child = ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: child,
        ),
      );
    }

    return child;
  }
}
