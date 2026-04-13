import 'dart:ui' as ui;

import 'package:flutter/painting.dart';

/// Pré-compile des shaders Skia courants (coins arrondis, dégradés, flou léger)
/// au démarrage via [PaintingBinding.shaderWarmUp], pour réduire le jank sur la
/// première transition / feuille / animation.
///
/// À assigner **avant** [WidgetsFlutterBinding.ensureInitialized]. Inefficace sur web
/// (voir [ShaderWarmUp.execute]).
///
/// Réf. : https://docs.flutter.dev/perf/shader
class ArquantixShaderWarmUp extends ShaderWarmUp {
  const ArquantixShaderWarmUp();

  @override
  Future<void> warmUpOnCanvas(ui.Canvas canvas) async {
    // Formes type boutons / champs (Material)
    final rrect = ui.RRect.fromRectAndRadius(
      const ui.Rect.fromLTWH(8, 8, 84, 84),
      const ui.Radius.circular(16),
    );
    canvas.drawRRect(
      rrect,
      ui.Paint()..color = const ui.Color(0xFFF5F5F5),
    );

    canvas.save();
    canvas.clipRRect(rrect);
    canvas.drawPaint(ui.Paint()..color = const ui.Color(0xFFFFFFFF));
    canvas.restore();

    // Cercles (avatars, drapeaux)
    canvas.drawCircle(
      const ui.Offset(50, 50),
      22,
      ui.Paint()..color = const ui.Color(0xFF4F46E5),
    );

    // Dégradé (hero / overlays)
    final grad = ui.Gradient.linear(
      ui.Offset.zero,
      const ui.Offset(100, 100),
      const [ui.Color(0xFFFFFFFF), ui.Color(0x1A4F46E5)],
    );
    canvas.drawRect(
      const ui.Rect.fromLTWH(0, 0, 100, 100),
      ui.Paint()..shader = grad,
    );

    // Flou type backdrop / feuilles (coûteux au premier usage)
    final blur = ui.ImageFilter.blur(sigmaX: 6, sigmaY: 6);
    canvas.saveLayer(
      const ui.Rect.fromLTWH(0, 0, 100, 100),
      ui.Paint()..imageFilter = blur,
    );
    canvas.drawColor(const ui.Color(0x22000000), ui.BlendMode.srcOver);
    canvas.restore();
  }
}
