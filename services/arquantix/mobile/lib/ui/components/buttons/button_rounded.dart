import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_typography.dart';

/// Variant du bouton rond : primaire (fond noir, icône blanche), secondaire (fond gris clair, icône noire),
/// hero (header dark, glass + blanc), heroLight (header light, glass + sombre),
/// heroPrimary (pill indigo + blanc, bouton d'action principal sur fond hero).
enum ButtonRoundedVariant {
  primary,
  secondary,
  hero,
  heroLight,
  heroPrimary,
}

/// Atome : bouton circulaire avec icône + label en dessous (style Revolut).
/// Ripple limité au cercle ; animation scale au toucher (0.96) ; désactivé si [onTap] null.
class ButtonRounded extends StatefulWidget {
  const ButtonRounded({
    super.key,
    required this.icon,
    required this.label,
    this.onTap,
    this.variant = ButtonRoundedVariant.secondary,
    this.size = 60,
    this.iconSize = 24,
    this.semanticLabel,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final ButtonRoundedVariant variant;
  final double size;
  final double iconSize;
  final String? semanticLabel;

  static const double _labelTopSpacing = 8;
  static const Duration _pressDuration = Duration(milliseconds: 120);
  static const double _pressScale = 0.96;

  @override
  State<ButtonRounded> createState() => _ButtonRoundedState();
}

class _ButtonRoundedState extends State<ButtonRounded> {
  bool _pressed = false;

  bool get _isPill => widget.variant == ButtonRoundedVariant.heroPrimary;
  double get _effectiveHeight => _isPill ? widget.size * 0.88 : widget.size;
  double _effectiveWidth(BuildContext context) {
    if (!_isPill) return widget.size;
    return MediaQuery.sizeOf(context).width * 0.25;
  }
  double get _effectiveIconSize =>
      _isPill ? widget.iconSize * 1.35 : widget.iconSize;

  Color _backgroundColor() {
    switch (widget.variant) {
      case ButtonRoundedVariant.primary:
        return AppColors.actionPrimaryBg;
      case ButtonRoundedVariant.secondary:
        return AppColors.actionSecondaryBg;
      case ButtonRoundedVariant.hero:
      case ButtonRoundedVariant.heroLight:
        return Colors.white.withValues(alpha: 0.12);
      case ButtonRoundedVariant.heroPrimary:
        return AppColors.actionHeroPrimaryBg;
    }
  }

  Widget _buildButtonDecoration(BuildContext context) {
    final isGlass = widget.variant == ButtonRoundedVariant.hero ||
        widget.variant == ButtonRoundedVariant.heroLight;

    if (widget.variant == ButtonRoundedVariant.heroPrimary) {
      final w = _effectiveWidth(context);
      final h = _effectiveHeight;
      final radius = BorderRadius.circular(h / 2);
      final base = _backgroundColor();
      return Container(
        width: w,
        height: h,
        decoration: BoxDecoration(
          borderRadius: radius,
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color.lerp(base, Colors.white, 0.08)!,
              base,
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Icon(
          widget.icon,
          size: _effectiveIconSize,
          color: _iconColor(),
        ),
      );
    }

    if (isGlass) {
      return Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white.withValues(alpha: 0.50),
        ),
        child: Icon(
          widget.icon,
          size: widget.iconSize,
          color: _iconColor(),
        ),
      );
    }

    return Container(
      width: widget.size,
      height: widget.size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _backgroundColor(),
      ),
      child: Icon(
        widget.icon,
        size: widget.iconSize,
        color: _iconColor(),
      ),
    );
  }

  Color _iconColor() {
    switch (widget.variant) {
      case ButtonRoundedVariant.primary:
        return AppColors.actionPrimaryIcon;
      case ButtonRoundedVariant.secondary:
        return AppColors.actionSecondaryIcon;
      case ButtonRoundedVariant.hero:
      case ButtonRoundedVariant.heroPrimary:
        return const Color(0xFFFFFFFF);
      case ButtonRoundedVariant.heroLight:
        return AppColors.textPrimary;
    }
  }

  TextStyle _labelStyle() {
    switch (widget.variant) {
      case ButtonRoundedVariant.heroPrimary:
        return AppTypography.actionLabel.copyWith(
          color: const Color(0xFFFFFFFF),
          fontWeight: FontWeight.w600,
          fontSize: 14,
        );
      case ButtonRoundedVariant.hero:
        return AppTypography.actionLabel.copyWith(
          color: const Color(0xFFFFFFFF),
          fontWeight: FontWeight.w600,
        );
      case ButtonRoundedVariant.heroLight:
        return AppTypography.actionLabel.copyWith(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w600,
        );
      default:
        return AppTypography.actionLabel.copyWith(color: AppColors.actionLabel);
    }
  }

  @override
  Widget build(BuildContext context) {
    final semantic = widget.semanticLabel ?? widget.label;
    final enabled = widget.onTap != null;

    final w = _effectiveWidth(context);
    final h = _effectiveHeight;
    final column = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedScale(
          scale: _pressed ? ButtonRounded._pressScale : 1.0,
          duration: ButtonRounded._pressDuration,
          curve: Curves.easeOut,
          child: SizedBox(
            width: w,
            height: h,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: enabled ? widget.onTap : null,
                onTapDown: enabled ? (_) => setState(() => _pressed = true) : null,
                onTapUp: enabled ? (_) => setState(() => _pressed = false) : null,
                onTapCancel: enabled ? () => setState(() => _pressed = false) : null,
                borderRadius: BorderRadius.circular(h / 2),
                customBorder: _isPill
                    ? RoundedRectangleBorder(borderRadius: BorderRadius.circular(h / 2))
                    : const CircleBorder(),
                child: _buildButtonDecoration(context),
              ),
            ),
          ),
        ),
        const SizedBox(height: ButtonRounded._labelTopSpacing),
        Text(
          widget.label,
          style: _labelStyle(),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
        ),
      ],
    );

    final result = Semantics(
      label: semantic,
      button: true,
      enabled: enabled,
      child: enabled ? column : Opacity(opacity: 0.5, child: column),
    );

    return result;
  }
}
