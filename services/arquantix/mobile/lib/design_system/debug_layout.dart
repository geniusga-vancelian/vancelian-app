import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Active le détourage blanc des zones de layout pour debug. Par défaut = false.
bool get debugLayoutBorders => _debugLayoutBorders;
bool _debugLayoutBorders = false;
set debugLayoutBorders(bool value) {
  _debugLayoutBorders = value;
}

/// Entoure [child] d'un contour blanc et affiche [label] en petit en haut à gauche quand [debugLayoutBorders] est true.
Widget debugLayoutBorder({
  required Widget child,
  required String label,
}) {
  if (!_debugLayoutBorders) return child;
  return Container(
    decoration: BoxDecoration(
      border: Border.all(color: Colors.white, width: 2),
    ),
    child: Stack(
      clipBehavior: Clip.none,
      children: [
        child,
        Positioned(
          top: 4,
          left: 4,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            color: Colors.black54,
            child: Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 10),
            ),
          ),
        ),
      ],
    ),
  );
}
