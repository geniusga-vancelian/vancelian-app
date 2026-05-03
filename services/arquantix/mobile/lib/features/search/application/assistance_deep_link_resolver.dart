import 'dart:developer' as developer;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../deposit/presentation/screens/deposit_carte_screen.dart';
import '../../deposit/presentation/screens/deposit_crypto_screen.dart';
import '../../deposit/presentation/screens/deposit_virement_screen.dart';
import '../../markets/data/market_data_api.dart';
import '../../markets/presentation/screens/crypto_detail_screen.dart';
import '../../markets/presentation/widgets/top_crypto_assets_module.dart';
import '../../news/presentation/screens/article_detail_screen.dart';
import '../../profile/presentation/screens/account_info_screen.dart';
import '../../profile/presentation/screens/security_screen.dart';
import '../../registration/screens/registration_flow_launcher_screen.dart';
import '../../wallet/data/crypto_positions_api.dart';
import '../../wallet/data/transaction_operation_pdf_api.dart';
import '../../wallet/presentation/screens/buy_asset_modal_screen.dart';
import '../../wallet/presentation/screens/compte_euro_screen.dart';
import '../../wallet/presentation/screens/iban_screen.dart';
import '../../wallet/presentation/screens/sell_flow/sell_flow_controller.dart';
import '../../wallet/presentation/screens/transaction_screen.dart';

/// Résolveur de deep-links Assistance — Phase 2b.
///
/// Les agents IA peuvent attacher un `deep_link` (whitelisté côté
/// backend par `action_cta_catalog`) à une option de QCM. Quand
/// l'utilisateur tape sur cette option, ce résolveur interprète le
/// `deep_link` et déclenche la navigation native correspondante.
///
/// Schéma : `vancelian://app/<intent>[/<sub-intent>]`.
///
/// Cf. `docs/arquantix/COMPLIANCE_TOPICS.md` § 4 (catalogue) et
/// § 6 (resolver Flutter).
///
/// Conventions importantes :
///   - Defense-in-depth : seuls les deep-links whitelistés ici sont
///     exécutés. Tout URL non reconnu → snackbar "Action indisponible"
///     + log analytique (à brancher Phase 3+).
///   - Aucun screen ne reçoit de PII via le deep-link (les params sont
///     des IDs opaques résolus côté serveur).
///   - Tous les screens cibles supposent une session JWT déjà active.
class AssistanceDeepLinkResolver {
  AssistanceDeepLinkResolver._();

  /// Tente de résoudre un `deepLink` et de naviguer vers l'écran cible.
  ///
  /// Retourne `true` si la navigation a été déclenchée, `false` sinon
  /// (deep-link inconnu ou malformé). Dans le cas `false`, un snackbar
  /// "Action indisponible" est affiché.
  ///
  /// Best-effort : aucune exception ne sort. Toute erreur Navigator
  /// est capturée et tracée.
  static Future<bool> resolve(BuildContext context, String deepLink) async {
    final uri = _safeParse(deepLink);
    if (uri == null) {
      _showUnavailable(context, deepLink, reason: 'malformed');
      return false;
    }
    if (uri.scheme != 'vancelian') {
      _showUnavailable(context, deepLink, reason: 'wrong_scheme');
      return false;
    }
    if (uri.host != 'app') {
      _showUnavailable(context, deepLink, reason: 'wrong_host');
      return false;
    }

    final segments = uri.pathSegments;
    if (segments.isEmpty) {
      _showUnavailable(context, deepLink, reason: 'empty_path');
      return false;
    }

    final intent = segments.first;

    switch (intent) {
      case 'registration_resume':
        return _push(
          context,
          const RegistrationFlowLauncherScreen(),
        );

      case 'deposit':
        if (segments.length == 1) {
          return _openDepositModal(context);
        }
        return _resolveDepositSub(context, segments[1]);

      case 'wallet':
        if (segments.length < 2) {
          _showUnavailable(context, deepLink, reason: 'missing_wallet_target');
          return false;
        }
        return _resolveWalletSub(context, segments[1]);

      case 'transactions':
        // Phase 2c.2 — Trois sous-cas :
        //   1. /transactions             → liste (compte euro,
        //      contient l'historique récent — Phase 2c TODO :
        //      écran transactions standalone)
        //   2. /transactions/{id}        → détail d'une transaction
        //      ciblée (TransactionScreen.fromId)
        //   3. /transactions/{id}/statement → téléchargement PDF du
        //      relevé d'opération + partage natif
        if (segments.length >= 3 && segments[2] == 'statement') {
          final txId = segments[1];
          if (txId.isEmpty) {
            _showUnavailable(
              context,
              deepLink,
              reason: 'missing_transaction_id',
            );
            return false;
          }
          return _downloadTransactionStatement(context, txId);
        }
        if (segments.length >= 2 && segments[1].isNotEmpty) {
          return _push(
            context,
            TransactionScreen.fromId(segments[1]),
          );
        }
        // Fallback liste = compte euro (Phase 2b inchangé).
        return _push(context, const CompteEuroScreen());

      case 'profile':
        if (segments.length < 2) {
          _showUnavailable(context, deepLink, reason: 'missing_profile_target');
          return false;
        }
        return _resolveProfileSub(context, segments[1]);

      case 'instrument':
        // Phase 2c.6 — `vancelian://app/instrument/{id}/{buy|sell}`.
        // L'`id` est l'`instrument_id` interne ; le sous-segment décide
        // du flow (BuyAssetModalScreen vs SellFlowController).
        // Phase 2c.7 — `vancelian://app/instrument/{id}` (sans sub) →
        // ouvre la fiche `CryptoDetailScreen`.
        if (segments.length < 2 || segments[1].isEmpty) {
          _showUnavailable(
            context,
            deepLink,
            reason: 'missing_instrument_target',
          );
          return false;
        }
        final instrumentId = int.tryParse(segments[1]);
        if (instrumentId == null) {
          _showUnavailable(
            context,
            deepLink,
            reason: 'malformed_instrument_id',
          );
          return false;
        }
        if (segments.length == 2) {
          return _openInstrumentDetail(context, instrumentId);
        }
        if (segments[2].isEmpty) {
          _showUnavailable(
            context,
            deepLink,
            reason: 'missing_instrument_target',
          );
          return false;
        }
        return _resolveInstrumentSub(context, instrumentId, segments[2]);

      case 'article':
        // Phase 2c.7 — `vancelian://app/article/{slug}` → ouvre le
        // lecteur d'article (CMS news / analyses / research, gabarit
        // unifié `ArticleDetailScreen`).
        if (segments.length < 2 || segments[1].isEmpty) {
          _showUnavailable(
            context,
            deepLink,
            reason: 'missing_article_slug',
          );
          return false;
        }
        return _push(
          context,
          ArticleDetailScreen(slug: segments[1]),
        );

      default:
        _showUnavailable(context, deepLink, reason: 'unknown_intent');
        return false;
    }
  }

  /// Whitelist statique — utile pour tests unit Flutter et pour vérifier
  /// que côté mobile on accepte au moins toutes les intents que le
  /// backend expose dans `action_cta_catalog` Phase 2b/2c.
  static const Set<String> knownIntents = {
    'registration_resume',
    'deposit',
    'wallet',
    'transactions',
    'profile',
    'instrument',
    'article',
  };

  // ─────────────────────────────────────────────────────────────────
  // Helpers privés
  // ─────────────────────────────────────────────────────────────────

  static Uri? _safeParse(String value) {
    try {
      return Uri.parse(value);
    } catch (_) {
      return null;
    }
  }

  static Future<bool> _push(BuildContext context, Widget screen) async {
    if (!context.mounted) return false;
    try {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(builder: (_) => screen),
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> _resolveDepositSub(
    BuildContext context,
    String sub,
  ) async {
    switch (sub) {
      case 'virement':
        return _push(context, const DepositVirementScreen());
      case 'carte':
        return _push(context, const DepositCarteScreen());
      case 'crypto':
        return _push(context, const DepositCryptoScreen());
      default:
        _showUnavailable(
          context,
          'vancelian://app/deposit/$sub',
          reason: 'unknown_deposit_sub',
        );
        return false;
    }
  }

  static Future<bool> _resolveWalletSub(
    BuildContext context,
    String sub,
  ) async {
    switch (sub) {
      case 'euro':
        return _push(context, const CompteEuroScreen());
      case 'iban':
        return _push(context, const IbanScreen());
      default:
        _showUnavailable(
          context,
          'vancelian://app/wallet/$sub',
          reason: 'unknown_wallet_sub',
        );
        return false;
    }
  }

  static Future<bool> _resolveProfileSub(
    BuildContext context,
    String sub,
  ) async {
    switch (sub) {
      case 'account':
        return _push(context, const AccountInfoScreen());
      case 'security':
        return _push(context, const SecurityScreen());
      default:
        _showUnavailable(
          context,
          'vancelian://app/profile/$sub',
          reason: 'unknown_profile_sub',
        );
        return false;
    }
  }

  /// Reproduit la modale de dépôt de `home_screen.dart::_openDepositModal`
  /// en version simplifiée pour le contexte assistance. Évite la
  /// dépendance circulaire vers HomeScreen.
  static Future<bool> _openDepositModal(BuildContext context) async {
    if (!context.mounted) return false;
    final selected = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 4),
              const Text(
                "Comment souhaites-tu déposer de l'argent ?",
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.account_balance),
                title: const Text('Par virement bancaire'),
                onTap: () => Navigator.of(sheetContext).pop('virement'),
              ),
              ListTile(
                leading: const Icon(Icons.credit_card),
                title: const Text('Par carte bancaire'),
                onTap: () => Navigator.of(sheetContext).pop('carte'),
              ),
              ListTile(
                leading: const Icon(Icons.currency_bitcoin),
                title: const Text('En crypto-monnaie'),
                onTap: () => Navigator.of(sheetContext).pop('crypto'),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
    if (selected == null || !context.mounted) return false;
    return _resolveDepositSub(context, selected);
  }

  /// Phase 2c.6 — résout `vancelian://app/instrument/{id}/{buy|sell}`.
  ///
  /// 1. fetch la fiche market-summary via [MarketDataApi] pour
  ///    récupérer `symbol` (provider, ex. `BTCUSDT`), `priceEur`,
  ///    `logoUrl`, et le name visible côté mobile ;
  /// 2. **buy** → ouvre directement [BuyAssetModalScreen.show] avec
  ///    le short symbol (ex. `BTC`) et le prix unitaire ;
  /// 3. **sell** → fetch le détail de la position via
  ///    [CryptoPositionsApi.fetchDetail] (404 → snackbar « Tu ne
  ///    possèdes pas {asset} »), sinon ouvre
  ///    [SellFlowController.start] avec la balance réelle.
  ///
  /// Best-effort : toute erreur réseau / market-data → snackbar
  /// discret « Action indisponible » et false.
  static Future<bool> _resolveInstrumentSub(
    BuildContext context,
    int instrumentId,
    String sub,
  ) async {
    if (!context.mounted) return false;
    final messenger = ScaffoldMessenger.maybeOf(context);

    if (sub != 'buy' && sub != 'sell') {
      _showUnavailable(
        context,
        'vancelian://app/instrument/$instrumentId/$sub',
        reason: 'unknown_instrument_sub',
      );
      return false;
    }

    final marketApi = MarketDataApi();
    MarketSummaryItem? summary;
    try {
      final summaries = await marketApi.getMarketSummary(
        instrumentIds: [instrumentId],
      );
      if (summaries.isNotEmpty) {
        summary = summaries.first;
      }
    } catch (e) {
      developer.log(
        'AssistanceDeepLinkResolver.instrument.market_data_error '
        'id=$instrumentId err=$e',
        name: 'AssistanceDeepLinkResolver',
      );
    }

    if (summary == null) {
      messenger?.showSnackBar(
        const SnackBar(
          content: Text(
            'Cours indisponible pour le moment. Réessaie dans un instant.',
          ),
          duration: Duration(seconds: 3),
        ),
      );
      return false;
    }

    final shortSymbol = _stripQuoteSuffix(summary.symbol);
    if (shortSymbol.isEmpty) {
      messenger?.showSnackBar(
        const SnackBar(
          content: Text('Action indisponible.'),
          duration: Duration(seconds: 3),
        ),
      );
      return false;
    }
    // `MarketSummaryItem` n'expose pas le `name` métier (Bitcoin) —
    // on retombe sur le short symbol comme libellé visible. Les
    // écrans BuyAsset / SellFlow l'utilisent uniquement en titre.
    final displayName = shortSymbol;
    final unitPrice = summary.priceEur ?? summary.price;
    if (!context.mounted) return false;

    if (sub == 'buy') {
      await BuyAssetModalScreen.show(
        context,
        assetSymbol: shortSymbol,
        assetName: displayName,
        assetLogoUrl: summary.logoUrl,
        unitPrice: unitPrice,
      );
      return true;
    }

    // sell — il faut une balance réelle.
    const positionsApi = CryptoPositionsApi();
    double balance = 0;
    try {
      final detail = await positionsApi.fetchDetail(shortSymbol);
      balance = double.tryParse(detail.volume) ?? 0;
    } on CryptoPositionsApiException catch (e) {
      if (e.statusCode == 404) {
        messenger?.showSnackBar(
          SnackBar(
            content: Text(
              'Tu ne possèdes pas encore de $shortSymbol à vendre.',
            ),
            duration: const Duration(seconds: 3),
          ),
        );
        return false;
      }
      developer.log(
        'AssistanceDeepLinkResolver.instrument.sell_balance_error '
        'asset=$shortSymbol err=$e',
        name: 'AssistanceDeepLinkResolver',
      );
      messenger?.showSnackBar(
        const SnackBar(
          content: Text(
            'Impossible de récupérer le solde pour le moment.',
          ),
          duration: Duration(seconds: 3),
        ),
      );
      return false;
    } catch (e) {
      developer.log(
        'AssistanceDeepLinkResolver.instrument.sell_unknown_error '
        'asset=$shortSymbol err=$e',
        name: 'AssistanceDeepLinkResolver',
      );
      return false;
    }

    if (balance <= 0) {
      messenger?.showSnackBar(
        SnackBar(
          content: Text(
            'Tu ne possèdes pas encore de $shortSymbol à vendre.',
          ),
          duration: const Duration(seconds: 3),
        ),
      );
      return false;
    }

    if (!context.mounted) return false;
    await SellFlowController.start(
      context,
      assetSymbol: shortSymbol,
      assetName: displayName,
      assetLogoUrl: summary.logoUrl,
      cryptoBalance: balance,
    );
    return true;
  }

  /// Phase 2c.7 — ouvre `CryptoDetailScreen` pour un `instrument_id`.
  ///
  /// Pattern « view-only » : on fetch la `MarketSummaryItem` puis on
  /// instancie un [CryptoAssetItem] minimal pour passer à l'écran.
  /// Pas de flow buy/sell ici — l'utilisateur peut déclencher l'achat
  /// depuis les CTAs de la page elle-même.
  static Future<bool> _openInstrumentDetail(
    BuildContext context,
    int instrumentId,
  ) async {
    if (!context.mounted) return false;
    final messenger = ScaffoldMessenger.maybeOf(context);

    final marketApi = MarketDataApi();
    MarketSummaryItem? summary;
    try {
      final summaries = await marketApi.getMarketSummary(
        instrumentIds: [instrumentId],
      );
      if (summaries.isNotEmpty) {
        summary = summaries.first;
      }
    } catch (e) {
      developer.log(
        'AssistanceDeepLinkResolver.instrument_view.market_data_error '
        'id=$instrumentId err=$e',
        name: 'AssistanceDeepLinkResolver',
      );
    }

    if (summary == null) {
      messenger?.showSnackBar(
        const SnackBar(
          content: Text(
            'Cours indisponible pour le moment. Réessaie dans un instant.',
          ),
          duration: Duration(seconds: 3),
        ),
      );
      return false;
    }

    final shortSymbol = _stripQuoteSuffix(summary.symbol);
    final unitPrice = summary.priceEur ?? summary.price;
    final priceFmt = unitPrice > 0
        ? NumberFormat.currency(
            locale: 'fr_FR',
            symbol: '€',
            decimalDigits: unitPrice >= 1 ? 2 : 4,
          ).format(unitPrice)
        : '—';

    if (!context.mounted) return false;
    final asset = CryptoAssetItem(
      name: shortSymbol.isNotEmpty ? shortSymbol : summary.symbol,
      ticker: shortSymbol,
      price: priceFmt,
      variationPercent: 0,
      logoUrl: summary.logoUrl,
    );
    return _push(
      context,
      CryptoDetailScreen(asset: asset),
    );
  }

  /// Strip USDT/USDC/BUSD/USD suffix d'un provider symbol Binance.
  /// Aligné sur `_normalize_short_symbol` côté backend (tool
  /// `show_instrument_card`).
  static String _stripQuoteSuffix(String providerSymbol) {
    final raw = providerSymbol.trim().toUpperCase();
    if (raw.isEmpty) return '';
    for (final quote in const ['USDT', 'USDC', 'BUSD', 'USD']) {
      if (raw.endsWith(quote) && raw.length > quote.length) {
        return raw.substring(0, raw.length - quote.length);
      }
    }
    return raw;
  }

  /// Télécharge le PDF du relevé d'opération via
  /// [TransactionOperationPdfApi] puis ouvre la feuille de partage
  /// native. Best-effort : toute erreur (404 / réseau) est journalisée
  /// et un snackbar discret est affiché. Phase 2c.2.
  static Future<bool> _downloadTransactionStatement(
    BuildContext context,
    String transactionId,
  ) async {
    if (!context.mounted) return false;
    final messenger = ScaffoldMessenger.maybeOf(context);
    final pdfApi = TransactionOperationPdfApi();
    try {
      final bytes = await pdfApi.fetchOperationStatementPdf(transactionId);
      final fileName =
          'releve-operation-${DateFormat('yyyy-MM-dd').format(DateTime.now())}.pdf';
      final file = File('${Directory.systemTemp.path}/$fileName');
      await file.writeAsBytes(bytes, flush: true);
      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'application/pdf', name: fileName)],
        subject: 'Relevé d\'opération',
      );
      return true;
    } catch (e) {
      developer.log(
        'AssistanceDeepLinkResolver.statement_failed tx=$transactionId err=$e',
        name: 'AssistanceDeepLinkResolver',
      );
      messenger?.showSnackBar(
        const SnackBar(
          content: Text(
            'Impossible de télécharger le relevé pour le moment.',
          ),
          duration: Duration(seconds: 3),
        ),
      );
      return false;
    }
  }

  static void _showUnavailable(
    BuildContext context,
    String deepLink, {
    required String reason,
  }) {
    if (!context.mounted) return;
    debugPrint(
      'AssistanceDeepLinkResolver.unavailable deep_link=$deepLink reason=$reason',
    );
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      SnackBar(
        content: Text(
          reason == 'unknown_intent' ||
                  reason == 'unknown_deposit_sub' ||
                  reason == 'unknown_wallet_sub' ||
                  reason == 'unknown_profile_sub'
              ? "Cette action n'est pas encore disponible dans l'app."
              : 'Action indisponible.',
        ),
        duration: const Duration(seconds: 3),
      ),
    );
  }
}
