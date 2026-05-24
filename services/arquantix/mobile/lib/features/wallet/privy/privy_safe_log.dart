import 'package:flutter/foundation.dart';

/// Journaux sûrs : **ne jamais** imprimer un JWT ou access token complet.
void privyLogTokenMeta(String label, String? token) {
  if (!kDebugMode) return;
  if (token == null || token.isEmpty) {
    debugPrint('[Privy] $label: <empty>');
    return;
  }
  final len = token.length;
  final suffix = len > 6 ? token.substring(len - 6) : '****';
  debugPrint('[Privy] $label: len=$len …$suffix');
}
