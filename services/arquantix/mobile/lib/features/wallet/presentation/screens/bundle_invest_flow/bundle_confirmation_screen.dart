import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/bundle_api.dart';
import '../../../data/exchange_api.dart';
import '../bundle_wallet_detail_screen.dart';
import 'bundle_invest_flow_controller.dart';
import 'bundle_processing_sheet.dart';

/// STEP 3 — Confirmation screen for bundle investment.
///
/// Uses [ConfirmationPageLayout] for the shared page structure.
class BundleConfirmationScreen extends StatefulWidget {
  const BundleConfirmationScreen({
    super.key,
    required this.bundle,
    required this.sourceAccount,
    required this.amount,
    this.preview,
  });

  final BundleItem bundle;
  final BundleSourceAccount sourceAccount;
  final double amount;
  final BundleInvestPreviewResult? preview;

  @override
  State<BundleConfirmationScreen> createState() =>
      _BundleConfirmationScreenState();
}

class _BundleConfirmationScreenState extends State<BundleConfirmationScreen> {
  final BundleApi _bundleApi = const BundleApi();

  bool _executing = false;
  String? _error;

  TransactionStepState _step1State = TransactionStepState.pending;
  TransactionStepState _step2State = TransactionStepState.pending;

  static final _fiatFormatterEur = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );
  static final _fiatFormatterUsd = NumberFormat.currency(
    locale: 'en_US',
    symbol: '\$',
    decimalDigits: 2,
  );

  NumberFormat get _fiatFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _fiatFormatterUsd
          : _fiatFormatterEur;

  String get _amountLabel => widget.sourceAccount.isFiat
      ? _fiatFormatter.format(widget.amount)
      : '${widget.amount.toStringAsFixed(2)} ${widget.sourceAccount.currency}';

  String get _fundingAsset =>
      widget.sourceAccount.isFiat ? 'EUR' : widget.sourceAccount.currency;

  String _humanError(String code) {
    final lc = code.toLowerCase();
    if (lc.contains('insufficient_funds')) return 'Solde insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('price_unavailable') || lc.contains('fx_unavailable')) {
      return 'Prix indisponible';
    }
    if (lc.contains('no_target_allocations')) {
      return 'Aucune allocation configurée';
    }
    if (lc.contains('portfolio_not_found')) return 'Bundle introuvable';
    if (lc.contains('funding_asset_not_allowed')) {
      return 'Source non autorisée';
    }
    return 'Erreur lors de l\'investissement';
  }

  static const _fiatAssets = {'EUR', 'USD', 'USDC', 'USDT'};

  String _fmtAmount(double v, String asset) {
    if (_fiatAssets.contains(asset.toUpperCase())) {
      return v.toStringAsFixed(2);
    }
    return _fmtCrypto(v);
  }

  String _fmtCrypto(double v) {
    if (v < 0.0001) return v.toStringAsExponential(2);
    String s;
    if (v < 1) {
      s = v.toStringAsFixed(8);
    } else {
      s = v.toStringAsFixed(6);
    }
    if (s.contains('.')) {
      s = s.replaceAll(RegExp(r'0+$'), '');
      s = s.replaceAll(RegExp(r'\.$'), '');
    }
    return s;
  }

  Future<void> _executeInvest() async {
    if (_executing) return;
    setState(() {
      _executing = true;
      _error = null;
      _step1State = TransactionStepState.processing;
      _step2State = TransactionStepState.pending;
    });

    // Step 1: preparation / validation
    await Future.delayed(const Duration(milliseconds: 400));
    if (!mounted) return;
    setState(() {
      _step1State = TransactionStepState.completed;
      _step2State = TransactionStepState.processing;
    });

    // Step 2: execute investment
    try {
      final result = await _bundleApi.investInBundle(
        portfolioId: widget.bundle.portfolioId,
        fundingAsset: _fundingAsset,
        fundingAmount: widget.amount,
      );
      if (!mounted) return;

      if (result.isCompleted) {
        setState(() {
          _step2State = TransactionStepState.completed;
        });

        final entryAsset =
            result.entryAsset ?? widget.bundle.entryAssetDefault;
        final hadConversion =
            _fundingAsset.toUpperCase() != entryAsset.toUpperCase();

        String overlayAmount;
        String overlaySubtitle;
        String? overlayDetail;

        if (hadConversion && result.totalEntryAssetReceived != null) {
          overlayAmount =
              '${_fmtAmount(result.totalEntryAssetReceived!, entryAsset)} $entryAsset';
          overlaySubtitle = 'pour $_amountLabel';

          if (widget.amount > 0 && result.totalEntryAssetReceived! > 0) {
            final rate =
                widget.amount / result.totalEntryAssetReceived!;
            overlayDetail =
                'Execution price: ${_fmtCrypto(rate)} $_fundingAsset / $entryAsset';
          }
        } else {
          overlayAmount = _amountLabel;
          overlaySubtitle = '${widget.bundle.name} · via $entryAsset';
          overlayDetail = result.legsSucceeded != null
              ? '${result.legsSucceeded} allocation${(result.legsSucceeded ?? 0) > 1 ? 's' : ''} réussie${(result.legsSucceeded ?? 0) > 1 ? 's' : ''}'
              : null;
        }

        final bundleSummary = MyBundleSummary(
          portfolioId: widget.bundle.portfolioId,
          portfolioName: widget.bundle.name,
          status: 'active',
          assetsCount: result.legsSucceeded ?? 0,
          totalCostBasis: widget.amount,
          totalMarketValue: widget.amount,
          hasHoldings: true,
          positions: const [],
        );

        await showTransactionSuccessOverlay(
          context: context,
          title: 'Investissement réussi',
          amount: overlayAmount,
          subtitle: overlaySubtitle,
          detail: overlayDetail,
          onNavigateAway: (nav) {
            nav.popUntil((route) => route.isFirst);
            nav.push(MaterialPageRoute(
              builder: (_) => BundleWalletDetailScreen(bundle: bundleSummary),
            ));
          },
        );
        return;
      }

      // Partial or failed — fall back to processing sheet for detailed view
      if (!mounted) return;
      setState(() {
        _step2State = TransactionStepState.pending;
      });

      final didInvest = await showModalBottomSheet<bool>(
        context: context,
        isDismissible: false,
        enableDrag: false,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        barrierColor: Colors.black.withValues(alpha: 0.5),
        builder: (_) => BundleProcessingSheet(
          bundle: widget.bundle,
          sourceAccount: widget.sourceAccount,
          amount: widget.amount,
          fundingAsset: _fundingAsset,
          fiatFormatter: _fiatFormatter,
          preloadedResult: result,
        ),
      );

      if (!mounted) return;
      if (didInvest == true) {
        Navigator.of(context).pop(true);
      } else {
        setState(() => _executing = false);
      }
    } on ExchangeApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _executing = false;
        _step1State = TransactionStepState.pending;
        _step2State = TransactionStepState.pending;
        _error = _humanError(e.errorCode ?? e.message);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _executing = false;
        _step1State = TransactionStepState.pending;
        _step2State = TransactionStepState.pending;
        _error = _humanError('unknown');
      });
    }
  }

  BundleInvestPreviewResult? get _preview => widget.preview;

  String get _entryAsset =>
      _preview?.entryAssetUsed ?? widget.bundle.entryAssetDefault;

  String get _estimatedEntryLabel {
    if (_preview == null || !_preview!.isUsable) return '—';
    return '${_preview!.entryAssetAmountDouble.toStringAsFixed(2)} $_entryAsset';
  }

  @override
  Widget build(BuildContext context) {
    final hasPreview = _preview != null && _preview!.isUsable;
    final isFiat = widget.sourceAccount.isFiat;

    return ConfirmationPageLayout(
      onBack: _executing ? () {} : () => Navigator.of(context).pop(),
      executing: _executing,
      directionIndicator: _buildExchangeDirection(),
      headline: 'Vous êtes sur le point d\'investir',
      heroAmount: _amountLabel,
      subtitle: 'dans ${widget.bundle.name}',
      ctaLabel: 'Confirmer l\'investissement',
      onConfirm: _executeInvest,
      bodyChildren: [
        _buildStepsModule(hasPreview, isFiat),
        if (hasPreview && _preview!.allocations.any((a) => a.isOk)) ...[
          const SizedBox(height: 20),
          _buildAllocationBreakdown(),
        ],
        if (hasPreview && _preview!.isPartial) ...[
          const SizedBox(height: 16),
          _buildPartialWarning(),
        ],
        if (_error != null) ...[
          const SizedBox(height: 16),
          _buildErrorBanner(),
        ],
        const SizedBox(height: 16),
        LegalFooterNote(
          segments: [
            LegalTextSegment(
              text: isFiat
                  ? 'En confirmant, vous reconnaissez que votre montant sera converti en ${widget.bundle.entryAssetDefault} puis alloué dans le bundle. Consultez les '
                  : 'En confirmant, vous reconnaissez que votre ${widget.sourceAccount.currency} sera alloué dans le bundle. Consultez les ',
            ),
            const LegalTextSegment(
              text: 'Conditions générales',
              url: 'https://arquantix.com/legal/bundles',
            ),
            const LegalTextSegment(text: ' avant de confirmer.'),
          ],
        ),
      ],
    );
  }

  String? get _sourceLogoUrl {
    final logo = widget.sourceAccount.logoUrl;
    if (logo != null && logo.isNotEmpty) return logo;
    if (widget.sourceAccount.isFiat) return null;
    final slug = widget.sourceAccount.currency.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  Widget _buildExchangeDirection() {
    return CryptoExchangeWidget(
      fromTicker: widget.sourceAccount.currency,
      toTicker: widget.bundle.entryAssetDefault,
      fromLogoUrl: _sourceLogoUrl,
      fromIcon: widget.sourceAccount.icon,
      toIcon: Icons.auto_awesome_mosaic_rounded,
    );
  }

  Widget _buildStepsModule(bool hasPreview, bool isFiat) {
    final TransactionStepItem step1;

    if (isFiat) {
      step1 = TransactionStepItem(
        number: 1,
        title: 'Conversion',
        primaryWidget: hasPreview
            ? _buildConversionRichText(
                _amountLabel,
                '≈ $_estimatedEntryLabel',
              )
            : Text(
                '$_amountLabel → ${widget.bundle.entryAssetDefault}',
                style: TransactionStepStyles.body,
              ),
        secondaryText: 'Montant estimé selon le prix de marché',
        approximate: true,
        state: _step1State,
      );
    } else {
      step1 = TransactionStepItem(
        number: 1,
        title: 'Transfert',
        primaryText:
            'Depuis votre wallet ${widget.sourceAccount.currency}',
        secondaryText: 'Aucun frais de transfert',
        state: _step1State,
      );
    }

    final allocStr = hasPreview ? '≈ $_estimatedEntryLabel' : _amountLabel;

    return TransactionStepsModule(
      title: 'Étapes de votre investissement',
      steps: [
        step1,
        TransactionStepItem(
          number: 2,
          title: 'Allocation dans le bundle',
          primaryWidget: Text(
            '$allocStr répartis selon la stratégie du bundle',
            style: TransactionStepStyles.body,
          ),
          secondaryText:
              'Allocation automatique entre les assets du bundle',
          approximate: isFiat,
          state: _step2State,
        ),
      ],
    );
  }

  Widget _buildConversionRichText(String fromStr, String toStr) {
    final s = TransactionStepStyles.body;
    return Text('$fromStr  →  $toStr', style: s);
  }

  Widget _buildAllocationBreakdown() {
    final legs = _preview!.allocations.where((a) => a.isOk).toList();
    if (legs.isEmpty) return const SizedBox.shrink();

    final slices = legs
        .map((a) => PortfolioAllocationSlice(
              label: a.asset,
              percentage: a.weightDouble * 100,
            ))
        .toList();

    final colors = legs
        .map((a) =>
            AppColors.cryptoAssetBrand[a.asset] ?? const Color(0xFF6B7280))
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'Détail de l\'allocation estimée',
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        PortfolioAllocationModule(
          slices: slices,
          sliceColors: colors,
        ),
      ],
    );
  }

  Widget _buildPartialWarning() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF3CD),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.warning_amber_rounded,
              size: 18, color: Color(0xFF856404)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Certains assets ne sont pas disponibles pour la cotation. '
              'L\'allocation sera partielle.',
              style: AppTypography.bodySmall.copyWith(
                color: const Color(0xFF856404),
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.errorBackground,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded,
              size: 18, color: AppColors.errorText),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _error ?? '',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.errorText,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
