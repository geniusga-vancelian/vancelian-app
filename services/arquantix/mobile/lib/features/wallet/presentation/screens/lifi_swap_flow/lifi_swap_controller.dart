import 'package:flutter/material.dart';

import '../../trading_flow_session_guard.dart';
import 'lifi_swap_to_selection_screen.dart';

/// Orchestrateur du flow swap LI.FI multi-étapes :
/// TO → FROM → montant → confirmation → traitement.
class LifiSwapController {
  LifiSwapController._();

  static Future<bool?> start(BuildContext context) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const LifiSwapToSelectionScreen(),
      ),
    );
  }
}
