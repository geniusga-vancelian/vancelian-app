import 'package:flutter/material.dart';

import '../../../../../design_system/design_system.dart';
import '../../trading_flow_session_guard.dart';
import 'bundle_selection_screen.dart';
import 'bundle_source_selection_screen.dart';

/// Data carrier representing a bundle available for investment.
class BundleItem {
  const BundleItem({
    required this.portfolioId,
    required this.productId,
    required this.name,
    required this.description,
    this.entryAssetDefault = 'USDC',
    this.entryAssetsAllowed = const ['USDC'],
    this.allocations = const [],
  });

  final String portfolioId;
  final String productId;
  final String name;
  final String description;
  final String entryAssetDefault;
  final List<String> entryAssetsAllowed;
  final List<BundleAllocationTarget> allocations;
}

class BundleAllocationTarget {
  const BundleAllocationTarget({
    required this.asset,
    required this.weight,
  });

  final String asset;
  final double weight;

  String get percentLabel => '${(weight * 100).toStringAsFixed(0)}%';
}

/// Data carrier for the selected funding source.
class BundleSourceAccount {
  const BundleSourceAccount({
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

/// Orchestrates the multi-step bundle invest flow.
///
/// Two entry modes:
/// 1. **Bundle known** — call [start] → begins at STEP 1 (source selection).
/// 2. **Bundle unknown** — call [startWithoutTarget] → begins at STEP 0.
class BundleInvestFlowController {
  BundleInvestFlowController._();

  static Future<bool?> start(
    BuildContext context, {
    required BundleItem bundle,
  }) async {
    if (!await CustomerAccountSessionGuard.ensureActiveAccountOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BundleSourceSelectionScreen(bundle: bundle),
      ),
    );
  }

  static Future<bool?> startWithoutTarget(BuildContext context) async {
    if (!await CustomerAccountSessionGuard.ensureActiveAccountOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const BundleSelectionScreen(),
      ),
    );
  }
}

/// Shared header disk button used across all flow screens.
class BundleFlowHeaderDisk extends StatelessWidget {
  const BundleFlowHeaderDisk({super.key, required this.onTap, required this.child});
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
