import 'package:flutter/animation.dart';

/// Atome : durées et courbes d'animation du design system.
class AppMotion {
  AppMotion._();

  // ── Durées ──

  static const Duration fast = Duration(milliseconds: 150);
  static const Duration base = Duration(milliseconds: 250);
  static const Duration slow = Duration(milliseconds: 400);

  // ── Courbes (easing) ──

  static const Curve standard = Curves.easeInOut;
}
