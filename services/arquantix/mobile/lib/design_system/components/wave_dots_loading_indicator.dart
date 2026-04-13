import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Six pastilles avec clignotement en « vague » de gauche à droite, en boucle.
class WaveDotsLoadingIndicator extends StatefulWidget {
  const WaveDotsLoadingIndicator({
    super.key,
    this.dotCount = 6,
    this.color = Colors.white,
    this.dotSize = 8,
    this.spacing = 10,
    this.period = const Duration(milliseconds: 1400),
  });

  final int dotCount;
  final Color color;
  final double dotSize;
  final double spacing;
  final Duration period;

  @override
  State<WaveDotsLoadingIndicator> createState() =>
      _WaveDotsLoadingIndicatorState();
}

class _WaveDotsLoadingIndicatorState extends State<WaveDotsLoadingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: widget.period)
      ..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.dotCount;
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final t = _controller.value;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(n, (i) {
            // Phase décalée : vague qui se propage vers la droite (boucle).
            final wave = (t * 2 * math.pi) - (i * 2 * math.pi / n);
            final pulse = (math.sin(wave) + 1) / 2;
            final opacity = 0.22 + 0.78 * pulse;
            return Padding(
              padding: EdgeInsets.only(
                right: i < n - 1 ? widget.spacing : 0,
              ),
              child: Opacity(
                opacity: opacity.clamp(0.15, 1.0),
                child: Container(
                  width: widget.dotSize,
                  height: widget.dotSize,
                  decoration: BoxDecoration(
                    color: widget.color,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: widget.color.withValues(alpha: 0.45),
                        blurRadius: 6,
                        spreadRadius: 0,
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}
