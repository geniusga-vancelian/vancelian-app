import 'package:flutter/material.dart';

import '../../wallet/data/cash_api.dart';
import '../../wallet/data/crypto_positions_api.dart';
import '../../wallet/presentation/trading_flow_session_guard.dart';
import '../../wallet/presentation/screens/bundle_invest_flow/bundle_invest_flow_controller.dart';
import '../../wallet/presentation/screens/bundle_invest_flow/bundle_amount_entry_screen.dart';
import '../../wallet/presentation/screens/buy_flow/buy_flow_amount_screen.dart';
import '../../wallet/presentation/screens/buy_flow/buy_flow_controller.dart';
import '../../markets/data/product_catalog_api.dart';

/// Navigation déclenchée par les deep-links `vancelian://app/invest/…`
/// (widgets assistant — liste de comptes sources, confirmation draft).
class InvestFlowFromAssistance {
  InvestFlowFromAssistance._();

  static String? _resolveLogoUrl(String? iconKey, String asset) {
    if (iconKey != null && iconKey.isNotEmpty) {
      return iconKey;
    }
    return null;
  }

  /// `vancelian://app/invest/bundle_amount?bundle_id=&account_key=[&amount=&ccy=]`
  static Future<bool> openBundleAmount(
    BuildContext context,
    Uri uri,
  ) async {
    if (!await CustomerAccountSessionGuard.ensureActiveAccountOrPrompt(context)) {
      return false;
    }
    if (!context.mounted) return false;

    final q = uri.queryParameters;
    final bundleId = q['bundle_id'];
    final accountKey = q['account_key'];
    if (bundleId == null || bundleId.isEmpty || accountKey == null) {
      return false;
    }
    final amountRaw = q['amount'];
    double? prefill;
    if (amountRaw != null && amountRaw.isNotEmpty) {
      prefill = double.tryParse(amountRaw.replaceAll(',', '.'));
    }

    if (!context.mounted) return false;

    final api = ProductCatalogApi();
    ProductCatalogItem? match;
    try {
      final list = await api.getBundleCatalog();
      for (final item in list) {
        if (item.id == bundleId) {
          match = item;
          break;
        }
      }
    } catch (_) {
      return false;
    }
    if (match == null) return false;
    final portfolioId = match.portfolioId;
    if (portfolioId == null || portfolioId.isEmpty) return false;

    final bundle = BundleItem(
      portfolioId: portfolioId,
      productId: match.id,
      name: match.name,
      description: match.description ?? match.allocationsSummary,
      entryAssetDefault: match.entryAssetDefault ?? 'USDC',
      entryAssetsAllowed: match.entryAssetsAllowed ?? const ['USDC'],
      allocations: match.allocations
          .map(
            (a) => BundleAllocationTarget(
              asset: a.assetSymbol,
              weight: a.targetWeight,
            ),
          )
          .toList(growable: false),
    );

    final source = await _bundleSourceForKey(
      bundle: bundle,
      accountKey: Uri.decodeComponent(accountKey),
    );
    if (source == null || !context.mounted) return false;

    await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BundleAmountEntryScreen(
          bundle: bundle,
          sourceAccount: source,
          prefillAmount: prefill,
        ),
      ),
    );
    return true;
  }

  /// `vancelian://app/invest/crypto_buy_amount?symbol=BTC&account_key=…`
  static Future<bool> openCryptoBuyAmount(
    BuildContext context,
    Uri uri,
  ) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return false;
    }
    if (!context.mounted) return false;

    final q = uri.queryParameters;
    final symbol = q['symbol'];
    final accountKey = q['account_key'];
    if (symbol == null || symbol.isEmpty || accountKey == null) {
      return false;
    }
    final amountRaw = q['amount'];
    final ccy = (q['ccy'] ?? 'EUR').toUpperCase();
    double? prefillFiat;
    if (amountRaw != null &&
        amountRaw.isNotEmpty &&
        (ccy == 'EUR' || ccy == 'USD')) {
      prefillFiat = double.tryParse(amountRaw.replaceAll(',', '.'));
    }

    if (!context.mounted) return false;

    final source = await _buySourceForKey(
      assetSymbol: symbol.toUpperCase(),
      accountKey: Uri.decodeComponent(accountKey),
    );
    if (source == null || !context.mounted) return false;

    await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BuyFlowAmountScreen(
          assetSymbol: symbol.toUpperCase(),
          assetName: symbol.toUpperCase(),
          sourceAccount: source,
          prefillFiatAmount: source.isFiat ? prefillFiat : null,
        ),
      ),
    );
    return true;
  }

  static Future<BundleSourceAccount?> _bundleSourceForKey({
    required BundleItem bundle,
    required String accountKey,
  }) async {
    final cashApi = const CashApi();
    final cryptoApi = const CryptoPositionsApi();
    final allowedUpper =
        bundle.entryAssetsAllowed.map((a) => a.toUpperCase()).toSet();

    if (accountKey == 'fiat') {
      try {
        final cashData = await cashApi.fetchCashData();
        final account = cashData.cashAccount;
        if (account == null) return null;
        return BundleSourceAccount(
          type: 'fiat',
          label: 'Compte Euro',
          balance: account.availableBalance,
          currency: account.currency,
          currencySymbol: account.currencySymbol,
          icon: Icons.euro_rounded,
          iconBackgroundColor: Colors.blue,
        );
      } catch (_) {
        return null;
      }
    }

    if (accountKey.startsWith('crypto:')) {
      final asset = accountKey.substring('crypto:'.length).trim().toUpperCase();
      if (!allowedUpper.contains(asset)) return null;
      try {
        final cryptoData = await cryptoApi.fetchPositions();
        for (final pos in cryptoData.positions) {
          if (pos.asset.toUpperCase() != asset) continue;
          if (pos.balance <= 0) continue;
          return BundleSourceAccount(
            type: 'crypto',
            label: 'Wallet ${pos.asset}',
            balance: pos.balance,
            currency: pos.asset,
            currencySymbol: pos.asset,
            icon: Icons.account_balance_wallet_rounded,
            iconBackgroundColor: Colors.orange,
            asset: pos.asset,
            logoUrl: _resolveLogoUrl(pos.iconKey, pos.asset),
          );
        }
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  static Future<BuyFlowSourceAccount?> _buySourceForKey({
    required String assetSymbol,
    required String accountKey,
  }) async {
    final targetUpper = assetSymbol.toUpperCase();
    final cashApi = const CashApi();
    final cryptoApi = const CryptoPositionsApi();

    if (accountKey == 'fiat') {
      try {
        final cashData = await cashApi.fetchCashData();
        final account = cashData.cashAccount;
        if (account == null) return null;
        return BuyFlowSourceAccount(
          type: 'fiat',
          label: 'Compte Euro',
          balance: account.availableBalance,
          currency: account.currency,
          currencySymbol: account.currencySymbol,
          icon: Icons.euro_rounded,
          iconBackgroundColor: Colors.blue,
        );
      } catch (_) {
        return null;
      }
    }

    if (accountKey.startsWith('crypto:')) {
      final asset = accountKey.substring('crypto:'.length).trim().toUpperCase();
      if (asset == targetUpper) return null;
      try {
        final cryptoData = await cryptoApi.fetchPositions();
        for (final pos in cryptoData.positions) {
          if (pos.asset.toUpperCase() != asset) continue;
          if (pos.balance <= 0) continue;
          return BuyFlowSourceAccount(
            type: 'crypto',
            label: pos.name,
            balance: pos.balance,
            currency: pos.asset,
            currencySymbol: pos.asset,
            icon: Icons.currency_bitcoin_rounded,
            iconBackgroundColor: Colors.deepPurple,
            asset: pos.asset,
            logoUrl: _resolveLogoUrl(pos.iconKey, pos.asset),
          );
        }
      } catch (_) {
        return null;
      }
    }
    return null;
  }
}
