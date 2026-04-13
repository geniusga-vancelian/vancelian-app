import 'package:flutter/material.dart';

/// Bottom sheet drag handle — 36×5 px pill, centered.
///
/// Figma spec: container 16px tall, bar starts at paddingTop 5,
/// bar color #CCCCCC, borderRadius 100.
class Grabber extends StatelessWidget {
  const Grabber({super.key});

  static const double _barWidth = 36;
  static const double _barHeight = 5;
  static const double _containerHeight = 16;
  static const double _topPadding = 5;
  static const Color _color = Color(0xFFCCCCCC);

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: _containerHeight,
      child: Padding(
        padding: const EdgeInsets.only(top: _topPadding),
        child: Center(
          child: Container(
            width: _barWidth,
            height: _barHeight,
            decoration: BoxDecoration(
              color: _color,
              borderRadius: BorderRadius.circular(100),
            ),
          ),
        ),
      ),
    );
  }
}
