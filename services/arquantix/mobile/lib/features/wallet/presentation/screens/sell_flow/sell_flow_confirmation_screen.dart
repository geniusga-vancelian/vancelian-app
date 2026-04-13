import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/exchange_api.dart';

/// STEP 3 — Confirmation screen for SELL.
///
/// Uses [ConfirmationPageLayout] for the shared page structure.
class SellFlowConfirmationScreen extends StatefulWidget {
  const SellFlowConfirmationScreen({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    this.assetLogoUrl,
    required this.amountCrypto,
    required this.destinationLabel,
    required this.preview,
  });

  final String assetSymbol;
  final String assetName;
  final String? assetLogoUrl;
  final double amountCrypto;
  final String destinationLabel;
  final SellPreviewResult preview;

  @override
  State<SellFlowConfirmationScreen> createState() =>
      _SellFlowConfirmationScreenState();
}

class _SellFlowConfirmationScreenState
    extends State<SellFlowConfirmationScreen> {
  final ExchangeApi _exchangeApi = const ExchangeApi();

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

  String _formatCrypto(double v) {
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
    if (lc.contains('insufficient_crypto')) return 'Solde crypto insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('price_unavailable') || lc.contains('fx_unavailable')) {
      return 'Prix indisponible';
    }
    if (lc.contains('unsupported_asset')) return 'Asset non supporté';
    if (lc.contains('duplicate')) return 'Ordre déjà traité';
    return 'Erreur lors de la vente';
  }

  Future<void> _executeSell() async {
    if (_executing) return;
    setState(() {
      _executing = true;
      _error = null;
      _step1State = TransactionStepState.processing;
      _step2State = TransactionStepState.pending;
    });

    // Step 1: refresh price
    SellPreviewResult freshPreview;
    try {
      freshPreview = await _exchangeApi.previewSell(
        asset: widget.assetSymbol,
        amountCrypto: widget.amountCrypto,
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

    // Step 2: execute trade
    try {
      final result = await _exchangeApi.executeSell(
        asset: widget.assetSymbol,
        amountCrypto: widget.amountCrypto,
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
        _error = 'Erreur lors de la vente';
      });
    }
  }

  Future<void> _showSuccessModal(SellResult result) async {
    if (!mounted) return;

    final cryptoAmount =
        _formatCrypto(result.amountCrypto ?? widget.amountCrypto);
    final fiatText = _fiatFormatter
        .format(result.amountFiat ?? widget.preview.estimatedFiatNet);
    final priceText = result.price != null
        ? _fiatFormatter.format(result.price!)
        : null;

    await showTransactionSuccessOverlay(
      context: context,
      title: 'Vente effectuée',
      amount: '+$fiatText',
      subtitle: 'pour $cryptoAmount ${widget.assetSymbol}',
      detail: priceText != null
          ? 'Execution price: $priceText / ${widget.assetSymbol}'
          : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.preview;
    final cryptoFormatted = _formatCrypto(widget.amountCrypto);
    final netFiat = _fiatFormatter.format(p.estimatedFiatNet);
    final priceText = _fiatFormatter.format(p.estimatedPrice);

    final feeLabel = p.feeAmount > 0
        ? '${_fiatFormatter.format(p.feeAmount)} (${p.feeBps} bps)'
        : 'Aucun';

    return ConfirmationPageLayout(
      onBack: _executing ? () {} : () => Navigator.of(context).pop(),
      executing: _executing,
      directionIndicator: _buildExchangeDirection(),
      headline: 'Vous êtes sur le point de vendre',
      heroAmount: '$cryptoFormatted ${widget.assetSymbol}',
      priceLine: 'au prix de $netFiat',
      ctaLabel: 'Confirmer la vente',
      onConfirm: _executeSell,
      bodyChildren: [
        TransactionStepsModule(
          title: 'Détail de votre vente',
          steps: [
            TransactionStepItem(
              number: 1,
              title: 'Analyse de prix',
              primaryWidget: _buildPriceRow(priceText),
              secondaryText:
                  'Prix estimé par analyse des meilleures offres du marché',
              state: _step1State,
            ),
            TransactionStepItem(
              number: 2,
              title: 'Conversion estimée',
              primaryWidget: _buildConversionRow(netFiat),
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
                  'En confirmant, vous acceptez que cet ordre de vente soit exécuté au prix de marché estimé. Le montant final peut varier légèrement. Consultez les ',
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

  String? get _resolvedLogo {
    if (widget.assetLogoUrl != null && widget.assetLogoUrl!.isNotEmpty) {
      return widget.assetLogoUrl;
    }
    final slug = widget.assetSymbol.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  Widget _buildExchangeDirection() {
    return CryptoExchangeWidget(
      fromTicker: widget.assetSymbol,
      toTicker: 'EUR',
      fromLogoUrl: _resolvedLogo,
      toIcon: Icons.account_balance_rounded,
    );
  }

  Widget _buildPriceRow(String priceText) {
    final asset = widget.assetSymbol.toUpperCase();
    final s = TransactionStepStyles.body;
    return Text.rich(
      TextSpan(children: [
        TextSpan(text: '$asset  →  ', style: s),
        TextSpan(
          text: 'Price: $priceText',
          style: s.copyWith(color: AppColors.indigo),
        ),
      ]),
    );
  }

  Widget _buildConversionRow(String netFiat) {
    return Text(
      '${_formatCrypto(widget.amountCrypto)} ${widget.assetSymbol}  →  ≈ $netFiat',
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
