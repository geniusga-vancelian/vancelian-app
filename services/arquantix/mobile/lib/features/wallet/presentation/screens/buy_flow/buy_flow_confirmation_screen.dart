import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/exchange_api.dart';
import 'buy_flow_controller.dart';

/// STEP 3 — Confirmation screen for buying crypto.
///
/// Uses [ConfirmationPageLayout] for the shared page structure.
class BuyFlowConfirmationScreen extends StatefulWidget {
  const BuyFlowConfirmationScreen({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    this.assetLogoUrl,
    required this.sourceAccount,
    required this.amountFiat,
    required this.preview,
  });

  final String assetSymbol;
  final String assetName;
  final String? assetLogoUrl;
  final BuyFlowSourceAccount sourceAccount;
  final double amountFiat;
  final BuyPreviewResult preview;

  @override
  State<BuyFlowConfirmationScreen> createState() =>
      _BuyFlowConfirmationScreenState();
}

class _BuyFlowConfirmationScreenState extends State<BuyFlowConfirmationScreen> {
  final ExchangeApi _exchangeApi = const ExchangeApi();

  bool _executing = false;
  String? _error;

  TransactionStepState _step1State = TransactionStepState.pending;
  TransactionStepState _step2State = TransactionStepState.pending;

  static final _fiatFormatterEur = NumberFormat.currency(
    locale: 'fr_FR', symbol: '€', decimalDigits: 2,
  );
  static final _fiatFormatterUsd = NumberFormat.currency(
    locale: 'en_US', symbol: '\$', decimalDigits: 2,
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
    if (lc.contains('insufficient_funds')) return 'Solde insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('market_quote_unavailable') ||
        lc.contains('price_unavailable') ||
        lc.contains('fx_unavailable')) {
      return 'Prix indisponible';
    }
    if (lc.contains('unsupported_asset')) return 'Asset non supporté';
    if (lc.contains('duplicate')) return 'Ordre déjà traité';
    return 'Erreur lors de l\'achat';
  }

  Future<void> _executeBuy() async {
    if (_executing) return;
    setState(() {
      _executing = true;
      _error = null;
      _step1State = TransactionStepState.processing;
      _step2State = TransactionStepState.pending;
    });

    // Step 1: refresh price
    BuyPreviewResult freshPreview;
    try {
      freshPreview = await _exchangeApi.previewBuy(
        asset: widget.assetSymbol,
        amountFiat: widget.amountFiat,
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
      final result = await _exchangeApi.executeBuy(
        asset: widget.assetSymbol,
        amountFiat: widget.amountFiat,
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

      // Show success modal
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
        _error = 'Erreur lors de l\'achat';
      });
    }
  }

  Future<void> _showSuccessModal(BuyResult result) async {
    if (!mounted) return;

    final cryptoAmount = _formatCrypto(result.amountCrypto ?? 0);
    final fiatText = _fiatFormatter.format(result.amountFiat ?? widget.amountFiat);
    final priceText = result.price != null
        ? _fiatFormatter.format(result.price!)
        : null;

    await showTransactionSuccessOverlay(
      context: context,
      title: 'Achat effectué',
      amount: '+$cryptoAmount ${widget.assetSymbol}',
      subtitle: 'pour $fiatText',
      detail: priceText != null
          ? 'Execution price: $priceText / ${widget.assetSymbol}'
          : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.preview;
    final cryptoNet = _formatCrypto(p.estimatedCryptoNet);
    final priceText = _fiatFormatter.format(p.estimatedPrice);

    final feeLabel = p.feeAmount > 0
        ? '${_fiatFormatter.format(p.feeAmount)} (${p.feeBps} bps)'
        : 'Aucun';

    final sourceCcy = widget.sourceAccount.currency.toUpperCase();
    final targetCcy = widget.assetSymbol.toUpperCase();
    final involvesEur = _isEurLike(sourceCcy) || _isEurLike(targetCcy);

    return ConfirmationPageLayout(
      onBack: _executing ? () {} : () => Navigator.of(context).pop(),
      executing: _executing,
      directionIndicator: _buildExchangeDirection(),
      headline: 'Vous êtes sur le point d\'acheter',
      heroAmount: '$cryptoNet ${widget.assetSymbol}',
      priceLine: 'au prix de ${_fiatFormatter.format(widget.amountFiat)}',
      eurApproxValue: involvesEur
          ? null
          : '(= ${_fiatFormatter.format(widget.amountFiat)})',
      ctaLabel: 'Confirmer l\'achat',
      onConfirm: _executeBuy,
      bodyChildren: [
        TransactionStepsModule(
          title: 'Détail de votre achat',
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
              primaryWidget: _buildConversionRow(cryptoNet),
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
                  'En confirmant, vous acceptez que cet ordre d\'achat soit exécuté au prix de marché estimé. Le montant final peut varier légèrement. Consultez les ',
            ),
            LegalTextSegment(
              text: 'Conditions générales',
              url: 'https://arquantix.com/legal/trading',
            ),
            LegalTextSegment(
                text: ' applicables aux transactions sur crypto-actifs.'),
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
    if (widget.assetLogoUrl != null && widget.assetLogoUrl!.isNotEmpty) {
      return widget.assetLogoUrl;
    }
    final slug = widget.assetSymbol.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  String? get _resolvedSourceLogo {
    if (widget.sourceAccount.logoUrl != null &&
        widget.sourceAccount.logoUrl!.isNotEmpty) {
      return widget.sourceAccount.logoUrl;
    }
    final slug = widget.sourceAccount.currency.trim().toLowerCase();
    if (slug.isEmpty || slug == 'eur') return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  Widget _buildExchangeDirection() {
    return CryptoExchangeWidget(
      fromTicker: widget.sourceAccount.currency,
      toTicker: widget.assetSymbol,
      fromLogoUrl: _resolvedSourceLogo,
      toLogoUrl: _resolvedTargetLogo,
      fromIcon: widget.sourceAccount.icon,
    );
  }

  Widget _buildPriceRow(String priceText) {
    final asset = widget.assetSymbol.toUpperCase();
    final currency = widget.preview.currency.toUpperCase();
    final s = TransactionStepStyles.body;
    return Text.rich(
      TextSpan(children: [
        TextSpan(text: '$asset  →  $currency ', style: s),
        TextSpan(
          text: 'Price: $priceText',
          style: s.copyWith(color: AppColors.indigo),
        ),
      ]),
    );
  }

  Widget _buildConversionRow(String cryptoNet) {
    return Text(
      '${_fiatFormatter.format(widget.amountFiat)}  →  $cryptoNet ${widget.assetSymbol}',
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

