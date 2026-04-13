import 'dart:async';

import 'package:circle_flags/circle_flags.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../features/security/passcode/data/session_service.dart';
import 'jank_trace.dart';
import 'startup/first_frame_interaction_primer.dart';
import 'startup/registration_surface_primer.dart';

/// Warm-up **non bloquant** pendant Login0 (splash / animation logo) pour déplacer
/// hors du premier tap : polices, drapeaux SVG, premier accès Keychain (email mémorisé).
///
/// - Idempotent : une seule exécution utile par phase et par processus.
/// - Borné : timeouts sur les lectures async ; rend la main entre phases.
/// - Priorisé : (1) polices / drapeaux, (2) primer overlay (gabarit feuille DS hors écran),
///   (3) stockage sécurisé best-effort.
class AppWarmupService {
  AppWarmupService._();
  static final AppWarmupService instance = AppWarmupService._();

  bool _uiDone = false;
  bool _overlayPrimeDone = false;
  bool _storageDone = false;
  bool _running = false;

  /// Appel sûr depuis n’importe quel frame (Welcome, intro logo, secours LoginPhone).
  Future<void> scheduleDuringIntro(BuildContext context) async {
    if (!context.mounted) return;
    if (_uiDone && _overlayPrimeDone && _storageDone) return;
    if (_running) return;
    _running = true;
    final sw = Stopwatch()..start();
    int? uiMs;
    int? overlayMs;
    int? storageMs;
    try {
      if (!_uiDone) {
        final uiSw = Stopwatch()..start();
        await _runUiPhase();
        uiMs = uiSw.elapsedMilliseconds;
        _uiDone = true;
      }
      // Cède au pipeline de rendu avant overlay primer.
      await Future<void>.delayed(Duration.zero);
      if (!context.mounted) return;
      if (!_overlayPrimeDone) {
        final ovSw = Stopwatch()..start();
        await FirstFrameInteractionPrimer.prime(context);
        if (context.mounted) {
          await RegistrationSurfacePrimer.prime(context);
        }
        overlayMs = ovSw.elapsedMilliseconds;
        _overlayPrimeDone = true;
      }
      await Future<void>.delayed(Duration.zero);
      if (!context.mounted) return;
      if (!_storageDone) {
        final stSw = Stopwatch()..start();
        await _runStoragePhase();
        storageMs = stSw.elapsedMilliseconds;
        _storageDone = true;
      }
    } catch (_) {
      // Best-effort : le premier écran utilisateur pourra retenter implicitement.
    } finally {
      _running = false;
    }
    final total = sw.elapsedMilliseconds;
    if (kDebugMode) {
      debugPrint(
        '[AppWarmup] done ${total}ms '
        '(ui=${uiMs ?? '-'}ms overlay=${overlayMs ?? '-'}ms storage=${storageMs ?? '-'}ms)',
      );
    }
    JankTrace.warmupComplete(
      totalMs: total,
      uiMs: uiMs,
      overlayMs: overlayMs,
      storageMs: storageMs,
    );
  }

  /// Polices Inter + drapeaux [CircleFlag] les plus utilisés sur auth / picker pays.
  Future<void> _runUiPhase() async {
    await Future.wait<void>([
      GoogleFonts.pendingFonts(_interWarmupStyles),
      CircleFlag.preload(_warmupCountryIsoCodes),
    ]);
  }

  /// Réchauffe le chemin Keychain pour [SessionService.readLastLoginEmail] (LoginPhone).
  Future<void> _runStoragePhase() async {
    try {
      await SessionService.instance
          .readLastLoginEmail()
          .timeout(_storageReadTimeout, onTimeout: () => null);
    } catch (_) {}
  }

  static const Duration _storageReadTimeout = Duration(milliseconds: 450);
}

/// ISO2 — EU fréquents + US/CA + MA (aligné picker / registration).
const _warmupCountryIsoCodes = [
  'fr', 'de', 'gb', 'es', 'it', 'be', 'nl', 'ch', 'pt', 'us',
  'ca', 'pl', 'se', 'at', 'ma',
];

/// Combinaisons Inter : login, titres, boutons, sous-titres, feuilles recherche.
final List<TextStyle> _interWarmupStyles = [
  GoogleFonts.inter(fontWeight: FontWeight.w800, fontSize: 34),
  GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 34),
  GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 20),
  GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 18),
  GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 17),
  GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 16, height: 1.25, letterSpacing: -0.3),
  GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 15),
  GoogleFonts.inter(fontWeight: FontWeight.w500, fontSize: 16),
  GoogleFonts.inter(fontWeight: FontWeight.w400, fontSize: 15),
  GoogleFonts.inter(fontWeight: FontWeight.w400, fontSize: 13),
  // AppTextInput (registration) : champ + label flottant
  GoogleFonts.inter(
    fontSize: 17,
    fontWeight: FontWeight.w600,
    height: 1.0,
    letterSpacing: -0.43,
  ),
  GoogleFonts.inter(
    fontSize: 17,
    fontWeight: FontWeight.w600,
    height: 22 / 17,
    letterSpacing: -0.43,
  ),
  GoogleFonts.inter(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 13 / 11,
    letterSpacing: 0.06,
  ),
];
