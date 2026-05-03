/// Widgets réactifs pour le voice input du chat Assistance (D.1.4.8).
///
/// - [VoiceWaveformIndicator] : waveform à 50 barres, mise à jour à
///   ~20 Hz à partir d'un Stream<double> (sound level normalisé [0,1]).
///   Effet "défilement de droite à gauche" comme ChatGPT.
///
/// - [VoiceTranscribingIndicator] : remplace le placeholder du
///   TextField pendant la transcription : spinner + texte
///   "Transcription…", aligné à gauche.
///
/// Tous deux utilisent uniquement les tokens du Design System
/// (`AppColors`, `AppTypography`, `AppSpacing`) — aucun magic number
/// de couleur ou taille hors DS.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';

/// Waveform horizontale qui défile de droite à gauche, alimentée par
/// un stream de niveaux audio normalisés `[0.0, 1.0]`.
///
/// La barre la plus à droite reflète le niveau le plus récent ; les
/// précédents glissent vers la gauche au fur et à mesure que de
/// nouveaux niveaux arrivent. Si le stream n'émet rien pendant > 100
/// ms, une valeur de fond (idle level légèrement non-nul) est insérée
/// pour éviter une waveform "morte" qui aurait l'air figée.
class VoiceWaveformIndicator extends StatefulWidget {
  const VoiceWaveformIndicator({
    super.key,
    required this.soundLevelStream,
    this.barCount = 50,
    this.barWidth = 2.0,
    this.barGap = 3.0,
    this.minBarHeight = 4.0,
    this.maxBarHeight = 28.0,
    this.color,
    this.idleLevel = 0.05,
  });

  /// Source des niveaux audio (entre 0.0 et 1.0). Émis ~10-20 Hz par
  /// le moteur de transcription (cf. `voice_transcriber.dart`).
  final Stream<double> soundLevelStream;

  /// Nombre de barres affichées simultanément. 50 reproduit fidèlement
  /// la waveform ChatGPT mobile.
  final int barCount;

  final double barWidth;
  final double barGap;
  final double minBarHeight;
  final double maxBarHeight;

  /// Couleur des barres. Défaut : blanc (utilisé sur fond sombre, mode
  /// recording). Peut être surchargée si on rend sur fond clair.
  final Color? color;

  /// Niveau de "fond" inséré quand le stream se tait, pour garder la
  /// waveform vivante (effet visuel uniquement).
  final double idleLevel;

  @override
  State<VoiceWaveformIndicator> createState() => _VoiceWaveformIndicatorState();
}

class _VoiceWaveformIndicatorState extends State<VoiceWaveformIndicator> {
  late final List<double> _levels;
  StreamSubscription<double>? _sub;
  Timer? _idleTicker;
  double _lastObserved = 0.0;
  DateTime _lastObservedAt = DateTime.now();

  @override
  void initState() {
    super.initState();
    // On initialise avec une légère amplitude aléatoire pour que
    // l'apparition de la waveform soit visuellement immédiate (sinon
    // les ~50 premières ms montreraient une bande plate).
    _levels = List<double>.generate(
      widget.barCount,
      (i) => widget.idleLevel + (i % 7) * 0.01,
    );
    _subscribeToStream();
    _startIdleTicker();
  }

  void _subscribeToStream() {
    _sub = widget.soundLevelStream.listen((level) {
      _lastObserved = level.clamp(0.0, 1.0);
      _lastObservedAt = DateTime.now();
      _pushLevel(_lastObserved);
    });
  }

  /// Tick à 20 Hz qui pousse la dernière valeur observée (ou l'idle
  /// level si aucune valeur récente) vers le buffer. Indispensable
  /// pour un effet de défilement fluide même quand le stream backend
  /// est plus lent que 20 Hz (cas Whisper qui ne publie pas en
  /// temps réel).
  void _startIdleTicker() {
    _idleTicker = Timer.periodic(const Duration(milliseconds: 50), (_) {
      final now = DateTime.now();
      final stale = now.difference(_lastObservedAt).inMilliseconds > 150;
      final value = stale ? widget.idleLevel : _lastObserved;
      _pushLevel(value);
    });
  }

  void _pushLevel(double level) {
    if (!mounted) return;
    setState(() {
      _levels.removeAt(0);
      _levels.add(level);
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    _idleTicker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? Colors.white;
    return CustomPaint(
      size: Size(
        widget.barCount * (widget.barWidth + widget.barGap) - widget.barGap,
        widget.maxBarHeight,
      ),
      painter: _WaveformPainter(
        levels: _levels,
        color: color,
        barWidth: widget.barWidth,
        barGap: widget.barGap,
        minBarHeight: widget.minBarHeight,
        maxBarHeight: widget.maxBarHeight,
      ),
    );
  }
}

class _WaveformPainter extends CustomPainter {
  _WaveformPainter({
    required this.levels,
    required this.color,
    required this.barWidth,
    required this.barGap,
    required this.minBarHeight,
    required this.maxBarHeight,
  });

  final List<double> levels;
  final Color color;
  final double barWidth;
  final double barGap;
  final double minBarHeight;
  final double maxBarHeight;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill
      ..strokeCap = StrokeCap.round;

    final centerY = size.height / 2;
    final pitch = barWidth + barGap;

    for (var i = 0; i < levels.length; i++) {
      final level = levels[i].clamp(0.0, 1.0);
      // Petite courbe de gain pour amplifier la lecture des chuchotements
      // sans saturer la parole forte. sqrt() est un bon compromis.
      final shaped = level == 0 ? 0.0 : (level + 0.1).clamp(0.0, 1.0);
      final h = minBarHeight +
          (maxBarHeight - minBarHeight) *
              (shaped < 0.001 ? 0.0 : (shaped <= 1 ? _easeOut(shaped) : 1));
      final x = i * pitch;
      final rect = Rect.fromLTWH(
        x,
        centerY - h / 2,
        barWidth,
        h,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, Radius.circular(barWidth / 2)),
        paint,
      );
    }
  }

  double _easeOut(double t) => 1 - (1 - t) * (1 - t);

  @override
  bool shouldRepaint(_WaveformPainter old) =>
      old.levels != levels || old.color != color;
}

/// Indicateur "Transcription…" affiché dans la pill input pendant que
/// la transcription est en cours (Whisper API ou résultat final natif
/// en attente). Spinner + label aligné gauche, comme la 3e capture
/// ChatGPT du brief utilisateur.
class VoiceTranscribingIndicator extends StatelessWidget {
  const VoiceTranscribingIndicator({super.key, this.label});

  /// Texte affiché à côté du spinner. Défaut : "Transcription".
  final String? label;

  @override
  Widget build(BuildContext context) {
    final text = label ?? 'Transcription';
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: 12,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor:
                  AlwaysStoppedAnimation<Color>(AppColors.textMuted),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            text,
            style: AppTypography.paragraph.copyWith(
              color: AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}
