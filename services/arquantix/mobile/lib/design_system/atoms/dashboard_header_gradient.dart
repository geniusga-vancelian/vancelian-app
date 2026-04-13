import 'package:flutter/material.dart';

/// Dégradé header dashboard / activation (Figma) : ligne **bas-gauche → haut-droite**, 3 stops.
///
/// Figma : 0 % bas-gauche `#000000`, 50 % `#12075C`, 100 % haut-droite `#111111`.
/// Flutter : première couleur sur [begin] (`bottomLeft`), dernière sur [end] (`topRight`).
abstract final class DashboardHeaderGradient {
  const DashboardHeaderGradient._();

  static const BoxDecoration decoration = BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.bottomLeft,
      end: Alignment.topRight,
      stops: [0, 0.5, 1],
      colors: [
        Color(0xFF000000),
        Color(0xFF12075C),
        Color(0xFF111111),
      ],
    ),
  );
}
