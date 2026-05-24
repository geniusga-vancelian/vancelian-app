import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'app.dart';
import 'core/app_info_service.dart';
import 'core/i18n/remote_strings_service.dart';
import 'core/locale_preference.dart';
import 'core/startup/arquantix_shader_warm_up.dart';

/// Initialisations lourdes (PackageInfo, données de locale pour `DateFormat`)
/// après le premier frame : le cold start affiche l’UI sans attendre le disque /
/// les assets intl, ce qui réduit le blanc perçu avant le premier rendu Flutter.
Future<void> _warmStartServices() async {
  await Future.wait<void>([
    AppInfoService.init(),
    initializeDateFormatting('fr_FR', null),
    initializeDateFormatting('en_US', null),
    LocalePreference.instance.bootstrap(),
  ]);
  /// Doit être bootstrappé **après** [LocalePreference] (souscrit à ses
  /// notifications). Best-effort — pas de blocage cold start.
  unawaited(RemoteStringsService.instance.bootstrap());
}

void main() async {
  // Pré-compile des shaders Skia courants avant init du binding (cf. perf/shader).
  if (!kIsWeb) {
    PaintingBinding.shaderWarmUp = const ArquantixShaderWarmUp();
  }
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      systemNavigationBarColor: Colors.white,
      systemNavigationBarIconBrightness: Brightness.dark,
    ),
  );
  runApp(const App());
  WidgetsBinding.instance.addPostFrameCallback((_) {
    unawaited(_warmStartServices());
  });
  // To run the floating bottom nav demo: runApp(const DemoNavApp());
}
