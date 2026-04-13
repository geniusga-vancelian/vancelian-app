import 'package:flutter/material.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../trading_flow_session_guard.dart';
import 'buy_flow_asset_selection_screen.dart';
import 'buy_flow_source_selection_screen.dart';

/// Orchestrates the multi-step BUY flow.
///
/// Two entry modes:
///
/// 1. **Asset known** — call [start] with [assetSymbol] / [assetName].
///    The flow begins at STEP 1 (source account selection).
///
/// 2. **Asset unknown** — call [startWithoutTarget].
///    The flow begins at STEP 0 (asset target selection), then chains
///    into STEP 1 → 2 → 3 → 4.
///
/// Each step pushes the next; the final result (`true` = buy executed)
/// pops back through all intermediary routes to the caller.
class BuyFlowController {
  BuyFlowController._();

  /// Opens the multi-step BUY flow when the target asset is already known.
  /// Skips STEP 0 and starts directly at STEP 1.
  static Future<bool?> start(
    BuildContext context, {
    required String assetSymbol,
    required String assetName,
    String? assetLogoUrl,
  }) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BuyFlowSourceSelectionScreen(
          assetSymbol: assetSymbol,
          assetName: assetName,
          assetLogoUrl: assetLogoUrl,
        ),
      ),
    );
  }

  /// Opens the multi-step BUY flow when NO target asset is pre-selected.
  /// Begins at STEP 0 (asset selection) then chains into the standard flow.
  static Future<bool?> startWithoutTarget(BuildContext context) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const BuyFlowAssetSelectionScreen(),
      ),
    );
  }

  /// Resolves a crypto logo URL using [Config.resolveLogoUrl].
  static String? resolveLogo(String? url) => Config.resolveLogoUrl(url);
}

/// Shared header disk button (close / back) used across all flow screens.
class BuyFlowHeaderDisk extends StatelessWidget {
  const BuyFlowHeaderDisk({super.key, required this.onTap, required this.child});
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        customBorder: const CircleBorder(),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.cardBackground,
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.12),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          alignment: Alignment.center,
          child: child,
        ),
      ),
    );
  }
}

/// Data carrier passed between flow steps.
class BuyFlowSourceAccount {
  const BuyFlowSourceAccount({
    required this.type,
    required this.label,
    required this.balance,
    required this.currency,
    required this.currencySymbol,
    required this.icon,
    required this.iconBackgroundColor,
    this.asset,
    this.logoUrl,
  });

  /// `fiat` or `crypto`
  final String type;
  final String label;
  final double balance;
  final String currency;
  final String currencySymbol;
  final IconData icon;
  final Color iconBackgroundColor;
  final String? asset;
  final String? logoUrl;

  bool get isFiat => type == 'fiat';
  bool get isCrypto => type == 'crypto';
}
