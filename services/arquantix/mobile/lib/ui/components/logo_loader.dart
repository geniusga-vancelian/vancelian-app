import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// Loader affichant le logo Arquantix en tout petit avec une animation de rotation.
class LogoLoader extends StatefulWidget {
  const LogoLoader({
    super.key,
    this.size = 24,
    this.color,
  });

  /// Taille du logo (hauteur en px).
  final double size;
  /// Couleur du logo (null = noir).
  final Color? color;

  @override
  State<LogoLoader> createState() => _LogoLoaderState();
}

class _LogoLoaderState extends State<LogoLoader>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? const Color(0xFF1a1a1a);
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: RotationTransition(
        turns: _controller,
        child: SvgPicture.asset(
          'assets/logo-black-icon.svg',
          width: widget.size,
          height: widget.size,
          colorFilter: ColorFilter.mode(color, BlendMode.srcIn),
        ),
      ),
    );
  }
}
