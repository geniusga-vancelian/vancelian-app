import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../../markets/presentation/screens/crypto_detail_screen.dart';
import '../../../data/exchange_api.dart';
import '../buy_flow/buy_flow_controller.dart';

/// Confirmation screen for crypto-to-crypto swap.
///
/// Uses [ConfirmationPageLayout] for the shared page structure.
class SwapFlowConfirmationScreen extends StatefulWidget {
  const SwapFlowConfirmationScreen({
    super.key,
    required this.fromAsset,
    required this.fromAssetName,
    required this.toAsset,
    required this.toAssetName,
    this.toAssetLogoUrl,
    this.fromAssetLogoUrl,
    required this.sourceAccount,
    required this.amountFrom,
    required this.preview,
  });

  final String fromAsset;
  final String fromAssetName;
  final String toAsset;
  final String toAssetName;
  final String? toAssetLogoUrl;
  final String? fromAssetLogoUrl;
  final BuyFlowSourceAccount sourceAccount;
  final double amountFrom;
  final SwapPreviewResult preview;

  @override
  State<SwapFlowConfirmationScreen> createState() =>
      _SwapFlowConfirmationScreenState();
}

class _SwapFlowConfirmationScreenState
    extends State<SwapFlowConfirmationScreen> {
  final ExchangeApi _exchangeApi = const ExchangeApi();

  bool _executing = false;
  String? _error;

  TransactionStepState _step1State = TransactionStepState.pending;
  TransactionStepState _step2State = TransactionStepState.pending;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR', symbol: '€', decimalDigits: 2,
  );
  static final _usdFormatter = NumberFormat.currency(
    locale: 'en_US', symbol: '\$', decimalDigits: 2,
  );

  NumberFormat get _fiatFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _usdFormatter
          : _eurFormatter;

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

  String _humanError(String code) {
    final lc = code.toLowerCase();
    if (lc.contains('insufficient')) return 'Solde insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('price_unavailable') || lc.contains('fx_unavailable')) {
      return 'Prix indisponible';
    }
    if (lc.contains('duplicate')) return 'Ordre déjà traité';
    return 'Erreur lors du swap';
  }

  Future<void> _executeSwap() async {
    if (_executing) return;
    setState(() {
      _executing = true;
      _error = null;
      _step1State = TransactionStepState.processing;
      _step2State = TransactionStepState.pending;
    });

    // Step 1: refresh price
    SwapPreviewResult freshPreview;
    try {
      freshPreview = await _exchangeApi.previewSwap(
        fromAsset: widget.fromAsset,
        toAsset: widget.toAsset,
        amountFrom: widget.amountFrom,
      );
      if (!mounted) return;
      if (freshPreview.hasError) {
        setState(() {
          _executing = false;
          _step1State = TransactionStepState.pending;
          _error = _humanError(freshPreview.error ?? '');
        });
        return;
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _executing = false;
        _step1State = TransactionStepState.pending;
        _error = 'Impossible d\'actualiser le prix';
      });
      return;
    }

    if (!mounted) return;
    setState(() {
      _step1State = TransactionStepState.completed;
      _step2State = TransactionStepState.processing;
    });

    // Step 2: execute swap
    try {
      final result = await _exchangeApi.executeSwap(
        fromAsset: widget.fromAsset,
        toAsset: widget.toAsset,
        amountFrom: widget.amountFrom,
      );
      if (!mounted) return;

      if (!result.isSuccess) {
        setState(() {
          _executing = false;
          _step1State = TransactionStepState.pending;
          _step2State = TransactionStepState.pending;
          _error = _humanError(result.errorCode ?? 'unknown');
        });
        return;
      }

      setState(() {
        _step2State = TransactionStepState.completed;
      });

      await _showSuccessModal(result);
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
        _error = 'Erreur lors du swap';
      });
    }
  }

  Future<void> _showSuccessModal(SwapResult result) async {
    if (!mounted) return;

    final toAmount = result.amountTo ?? 0.0;
    final fromAmount = result.amountFrom ?? widget.amountFrom;

    String? detail;
    if (fromAmount > 0 && toAmount > 0) {
      final rate = fromAmount / toAmount;
      detail =
          'Execution price: ${_fmtCrypto(rate)} ${widget.fromAsset} / ${widget.toAsset}';
    }

    final destAsset = widget.toAsset;
    await showTransactionSuccessOverlay(
      context: context,
      title: 'Conversion effectuée',
      amount: '+${_fmtCrypto(toAmount)} $destAsset',
      subtitle: 'pour ${_fmtCrypto(fromAmount)} ${widget.fromAsset}',
      detail: detail,
      onNavigateAway: (nav) {
        nav.popUntil((route) => route.isFirst);
        nav.push(MaterialPageRoute(
          builder: (_) => CryptoDetailScreen(
            asset: CryptoDetailScreen.assetFromSlug(destAsset),
          ),
        ));
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.preview;
    final fromAmount = _fmtCrypto(widget.amountFrom);
    final toAmount = _fmtCrypto(p.estimatedToAmount);
    final fromPriceText = _fiatFormatter.format(p.fromPrice);
    final toPriceText = _fiatFormatter.format(p.toPrice);

    final feeLabel = p.feeInRefCurrency > 0
        ? _fiatFormatter.format(p.feeInRefCurrency)
        : 'Aucun';

    final fromCcy = widget.fromAsset.toUpperCase();
    final toCcy = widget.toAsset.toUpperCase();
    final involvesEur = _isEurLike(fromCcy) || _isEurLike(toCcy);
    final refCcy = p.referenceCurrency.toUpperCase();
    final refSymbol = (refCcy == 'USD' || refCcy == 'USDC') ? '\$' : '€';
    final refAmount = NumberFormat('#,##0.00', 'fr_FR').format(p.estimatedRefValueGross);

    return ConfirmationPageLayout(
      onBack: _executing ? () {} : () => Navigator.of(context).pop(),
      executing: _executing,
      directionIndicator: _buildExchangeDirection(),
      headline: 'Vous êtes sur le point de convertir',
      heroAmount: '$fromAmount ${widget.fromAsset}',
      approximateValue: involvesEur
          ? null
          : '≈ ${_fmtCrypto(p.estimatedToAmount)} ${widget.toAsset}',
      eurApproxValue: involvesEur
          ? null
          : '($refAmount $refSymbol)',
      ctaLabel: 'Confirmer la conversion',
      onConfirm: _executeSwap,
      bodyChildren: [
        TransactionStepsModule(
          title: 'Détail de votre conversion',
          steps: [
            TransactionStepItem(
              number: 1,
              title: 'Analyse de prix',
              primaryWidget: _buildPriceRow(fromPriceText, toPriceText),
              secondaryText:
                  'Prix estimé par analyse des meilleures offres du marché',
              state: _step1State,
            ),
            TransactionStepItem(
              number: 2,
              title: 'Conversion estimée',
              primaryWidget: _buildConversionRow(fromAmount, toAmount),
              secondaryText: 'Montant estimé selon le prix de marché',
              approximate: true,
              state: _step2State,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        _buildFeesRow(feeLabel),
        const SizedBox(height: AppSpacing.lg),
        const LegalFooterNote(
          segments: [
            LegalTextSegment(
              text:
                  'En confirmant, vous acceptez que cette conversion soit exécutée au prix de marché estimé. Le montant final peut varier légèrement. Consultez les ',
            ),
            LegalTextSegment(
              text: 'Conditions générales',
              url: 'https://arquantix.com/legal/trading',
            ),
            LegalTextSegment(
              text: ' applicables aux transactions sur crypto-actifs.',
            ),
          ],
        ),
        if (_error != null) ...[
          const SizedBox(height: AppSpacing.lg),
          _buildErrorBanner(),
        ],
      ],
    );
  }

  static bool _isEurLike(String ccy) =>
      ccy == 'EUR' || ccy == 'EURC' || ccy == 'EURT';

  String? get _resolvedTargetLogo {
    if (widget.toAssetLogoUrl != null && widget.toAssetLogoUrl!.isNotEmpty) {
      return widget.toAssetLogoUrl;
    }
    final slug = widget.toAsset.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  String? get _resolvedFromLogo {
    if (widget.fromAssetLogoUrl != null && widget.fromAssetLogoUrl!.isNotEmpty) {
      return widget.fromAssetLogoUrl;
    }
    final slug = widget.fromAsset.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  Widget _buildExchangeDirection() {
    return CryptoExchangeWidget(
      fromTicker: widget.fromAsset,
      toTicker: widget.toAsset,
      fromLogoUrl: _resolvedFromLogo,
      toLogoUrl: _resolvedTargetLogo,
    );
  }

  Widget _buildPriceRow(String fromPriceText, String toPriceText) {
    final from = widget.fromAsset.toUpperCase();
    final to = widget.toAsset.toUpperCase();
    final refCurrency = widget.preview.referenceCurrency.toUpperCase();
    final s = TransactionStepStyles.body;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text.rich(
          TextSpan(children: [
            TextSpan(text: '$from  →  $refCurrency ', style: s),
            TextSpan(
              text: 'Price: $fromPriceText',
              style: s.copyWith(color: AppColors.indigo),
            ),
          ]),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text.rich(
          TextSpan(children: [
            TextSpan(text: '$to  →  $refCurrency ', style: s),
            TextSpan(
              text: 'Price: $toPriceText',
              style: s.copyWith(color: AppColors.indigo),
            ),
          ]),
        ),
      ],
    );
  }

  Widget _buildConversionRow(String fromAmount, String toAmount) {
    return Text(
      '$fromAmount ${widget.fromAsset}  →  ≈ $toAmount ${widget.toAsset}',
      style: TransactionStepStyles.body,
    );
  }

  Widget _buildFeesRow(String feeLabel) {
    return SettingsCard(
      children: [
        SettingsListItem(title: 'Fees', value: feeLabel),
      ],
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

