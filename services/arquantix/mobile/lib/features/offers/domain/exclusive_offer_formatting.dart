import 'dart:ui' as ui;

import 'package:intl/intl.dart';

/// Formate un pourcentage APR pour affichage (ex. `10,5 %` en FR, `10.5%` en EN).
String formatExclusiveOfferAprPercent(double apy) {
  if (!apy.isFinite) return '';
  final locale = ui.PlatformDispatcher.instance.locale;
  final fmt = NumberFormat('#0.00', locale.toLanguageTag());
  return '${fmt.format(apy)}%';
}
