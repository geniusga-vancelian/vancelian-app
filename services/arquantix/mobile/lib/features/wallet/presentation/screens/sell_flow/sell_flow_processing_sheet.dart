import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../design_system/design_system.dart';
import '../../../data/exchange_api.dart';

/// STEP 4 — Processing + Success bottom sheet for SELL.
class SellFlowProcessingSheet extends StatefulWidget {
  const SellFlowProcessingSheet({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    required this.amountCrypto,
    required this.preview,
    required this.fiatFormatter,
    required this.formatCrypto,
  });

  final String assetSymbol;
  final String assetName;
  final double amountCrypto;
  final SellPreviewResult preview;
  final NumberFormat fiatFormatter;
  final String Function(double) formatCrypto;

  @override
  State<SellFlowProcessingSheet> createState() =>
      _SellFlowProcessingSheetState();
}

enum _SheetPhase { processing, success, error }

class _SellFlowProcessingSheetState extends State<SellFlowProcessingSheet> {
  final ExchangeApi _exchangeApi = const ExchangeApi();

  _SheetPhase _phase = _SheetPhase.processing;
  SellResult? _result;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _execute();
  }

  Future<void> _execute() async {
    try {
      final result = await _exchangeApi.executeSell(
        asset: widget.assetSymbol,
        amountCrypto: widget.amountCrypto,
      );
      if (!mounted) return;

      if (result.isSuccess) {
        setState(() {
          _phase = _SheetPhase.success;
          _result = result;
        });
        await Future.delayed(const Duration(milliseconds: 2000));
        if (mounted) Navigator.of(context).pop(true);
      } else {
        setState(() {
          _phase = _SheetPhase.error;
          _errorMessage = _humanError(result.errorCode ?? 'unknown');
        });
      }
    } on ExchangeApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _SheetPhase.error;
        _errorMessage = _humanError(e.errorCode ?? e.message);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _SheetPhase.error;
        _errorMessage = 'Erreur lors de la vente';
      });
    }
  }

  String _humanError(String code) {
    final lc = code.toLowerCase();
    if (lc.contains('insufficient_crypto')) return 'Solde crypto insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('price_unavailable') || lc.contains('fx_unavailable')) {
      return 'Prix indisponible';
    }
    if (lc.contains('duplicate')) return 'Ordre déjà traité';
    return 'Erreur lors de la vente';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.xl,
            AppSpacing.md,
            AppSpacing.xl,
            AppSpacing.xxl,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.placeholderIcon.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              _buildContent(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    switch (_phase) {
      case _SheetPhase.processing:
        return _buildProcessing();
      case _SheetPhase.success:
        return _buildSuccess();
      case _SheetPhase.error:
        return _buildError();
    }
  }

  Widget _buildProcessing() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: AppColors.textPrimary,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const SizedBox(
            width: 28,
            height: 28,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Nous traitons votre vente',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Cela ne prend que quelques secondes',
          textAlign: TextAlign.center,
          style: AppTypography.meta.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildSuccess() {
    final r = _result!;
    final cryptoAmount = widget.formatCrypto(r.amountCrypto ?? widget.amountCrypto);
    final fiatText = widget.fiatFormatter.format(
      r.amountFiat ?? widget.preview.estimatedFiatNet,
    );
    final priceText = r.price != null
        ? widget.fiatFormatter.format(r.price!)
        : widget.fiatFormatter.format(widget.preview.estimatedPrice);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: AppColors.textPrimary,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.check_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Vente effectuée',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          '-$cryptoAmount ${widget.assetSymbol}',
          textAlign: TextAlign.center,
          style: AppTypography.heroAmount.copyWith(
            color: AppColors.textPrimary,
            fontSize: 28,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '+ $fiatText reçus',
          textAlign: TextAlign.center,
          style: AppTypography.meta.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Prix : $priceText / ${widget.assetSymbol}',
          textAlign: TextAlign.center,
          style: AppTypography.meta.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildError() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: AppColors.textPrimary,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.close_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          _errorMessage ?? 'Erreur',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => Navigator.of(context).pop(false),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.placeholderBg,
              foregroundColor: AppColors.textPrimary,
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppRadius.button),
              ),
              textStyle: AppTypography.paragraph.copyWith(
                fontWeight: FontWeight.w600,
              ),
              elevation: 0,
            ),
            child: const Text('Fermer'),
          ),
        ),
      ],
    );
  }
}
