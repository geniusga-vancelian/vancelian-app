import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// iOS-style toggle switch.
///
/// Figma specs:
/// - Width 64, height 28
/// - Active: bg indigo (#6155F5), knob right
/// - Inactive: bg #C7C7CC, knob left
/// - Knob: white, 24px height, width 39px, borderRadius 100
/// - Padding: 2px
/// - Animation: 200ms ease
class AppToggleSwitch extends StatelessWidget {
  const AppToggleSwitch({
    super.key,
    required this.value,
    required this.onChanged,
    this.activeColor,
    this.inactiveColor,
    this.disabled = false,
  });

  final bool value;
  final ValueChanged<bool> onChanged;
  final Color? activeColor;
  final Color? inactiveColor;
  final bool disabled;

  static const double _width = 64;
  static const double _height = 28;
  static const double _knobWidth = 39;
  static const double _knobHeight = 24;
  static const double _padding = 2;

  @override
  Widget build(BuildContext context) {
    final bgColor = value
        ? (activeColor ?? AppColors.indigo)
        : (inactiveColor ?? const Color(0xFFC7C7CC));

    final knobOffset = value ? _width - _knobWidth - _padding * 2 : 0.0;

    return GestureDetector(
      onTap: disabled ? null : () => onChanged(!value),
      child: AnimatedContainer(
        duration: AppMotion.base,
        curve: AppMotion.standard,
        width: _width,
        height: _height,
        padding: const EdgeInsets.all(_padding),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(100),
        ),
        child: Stack(
          children: [
            AnimatedPositioned(
              duration: AppMotion.base,
              curve: AppMotion.standard,
              left: knobOffset,
              top: 0,
              bottom: 0,
              child: Container(
                width: _knobWidth,
                height: _knobHeight,
                decoration: BoxDecoration(
                  color: AppColors.white,
                  borderRadius: BorderRadius.circular(100),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
