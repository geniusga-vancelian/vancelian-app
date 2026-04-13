import 'package:flutter/foundation.dart';

/// Traces debug (kDebugMode uniquement) : mesurer le délai entre un tap et le
/// premier frame d’une route cible. Activer en lançant avec :
/// `--dart-define=TRACE_JANK=true`
///
/// Usage :
/// - [tap] au début du onPressed avant [Navigator.push]
/// - [markRouteFirstFrame] dans initState de l’écran poussé (post-frame).
/// - Comparer 1er vs 2e push : les logs indiquent `#n` pour chaque [tap].
///
/// Modales : même API avec un label du type `modal_phone_picker` + premier frame
/// dans le builder (voir [markModalFirstFrame]).
class JankTrace {
  JankTrace._();

  static const bool _enabled =
      kDebugMode && bool.fromEnvironment('TRACE_JANK', defaultValue: false);

  static Stopwatch? _sw;
  static String? _label;
  static final Map<String, int> _tapCounts = {};

  static void tap(String label) {
    if (!_enabled) return;
    final n = (_tapCounts[label] ?? 0) + 1;
    _tapCounts[label] = n;
    _label = label;
    _sw = Stopwatch()..start();
    debugPrint('[TRACE_JANK] tap: $label (#$n)');
  }

  static void markRouteFirstFrame(String routeName) {
    if (!_enabled || _sw == null) return;
    debugPrint(
      '[TRACE_JANK] first frame $routeName: ${_sw!.elapsedMilliseconds}ms after tap ($_label)',
    );
    _sw = null;
    _label = null;
  }

  /// Après [tap] avec un label `modal_*`, appeler depuis le premier frame du
  /// contenu de la modale (ex. [addPostFrameCallback] dans [initState] du sheet).
  static void markModalFirstFrame(String modalName) {
    markRouteFirstFrame(modalName);
  }

  /// Durée totale du warm-up Login0 + détail phases (uniquement si `TRACE_JANK=true`).
  static void warmupComplete({
    required int totalMs,
    int? uiMs,
    int? overlayMs,
    int? storageMs,
  }) {
    if (!_enabled) return;
    debugPrint(
      '[TRACE_JANK] warmup_complete: ${totalMs}ms '
      '(ui=${uiMs ?? '-'}ms overlay=${overlayMs ?? '-'}ms storage=${storageMs ?? '-'}ms)',
    );
  }

  static Stopwatch? _phoneFocusSw;
  static bool _phoneFocusTraceDone = false;

  /// Premier focus sur le champ téléphone (login) — mesure jusqu’au frame suivant.
  static void phoneFieldFocusStart() {
    if (!_enabled || _phoneFocusTraceDone) return;
    if (_phoneFocusSw != null) return;
    _phoneFocusSw = Stopwatch()..start();
    debugPrint('[TRACE_JANK] phone_field_focus_start');
  }

  static void phoneFieldFocusFirstFrame() {
    if (!_enabled || _phoneFocusSw == null) return;
    _phoneFocusTraceDone = true;
    debugPrint(
      '[TRACE_JANK] phone_field_focus_first_frame: ${_phoneFocusSw!.elapsedMilliseconds}ms',
    );
    _phoneFocusSw = null;
  }
}
