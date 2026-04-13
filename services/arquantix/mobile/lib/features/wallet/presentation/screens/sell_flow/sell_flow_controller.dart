import 'package:flutter/material.dart';

import '../../../../../core/config.dart';
import '../../trading_flow_session_guard.dart';
import 'sell_flow_asset_selection_screen.dart';
import 'sell_flow_destination_selection_screen.dart';

/// Orchestrates the multi-step SELL flow.
///
/// Two entry modes:
///
/// 1. **Asset known** — call [start] with [assetSymbol] / [assetName].
///    The flow begins at STEP 1 (destination selection).
///
/// 2. **Asset unknown** — call [startWithoutSourceAsset].
///    The flow begins at STEP 0 (asset selection), then chains
///    into STEP 1 → 2 → 3 → 4.
class SellFlowController {
  SellFlowController._();

  /// Opens the multi-step SELL flow when the asset to sell is already known.
  /// Skips STEP 0 and starts directly at STEP 1.
  static Future<bool?> start(
    BuildContext context, {
    required String assetSymbol,
    required String assetName,
    String? assetLogoUrl,
    required double cryptoBalance,
  }) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => SellFlowDestinationSelectionScreen(
          assetSymbol: assetSymbol,
          assetName: assetName,
          assetLogoUrl: assetLogoUrl,
          cryptoBalance: cryptoBalance,
        ),
      ),
    );
  }

  /// Opens the multi-step SELL flow when NO source asset is pre-selected.
  /// Begins at STEP 0 (asset selection) then chains into the standard flow.
  static Future<bool?> startWithoutSourceAsset(BuildContext context) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const SellFlowAssetSelectionScreen(),
      ),
    );
  }

  /// Resolves a crypto logo URL using [Config.resolveLogoUrl].
  static String? resolveLogo(String? url) => Config.resolveLogoUrl(url);
}
