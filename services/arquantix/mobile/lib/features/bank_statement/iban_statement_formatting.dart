import 'package:intl/intl.dart';

/// Deterministic FR formatting for amounts (matches Figma `Intl.NumberFormat('fr-FR')`).
String formatStatementAmount(double value) {
  return NumberFormat('#,##0.00', 'fr_FR').format(value);
}
