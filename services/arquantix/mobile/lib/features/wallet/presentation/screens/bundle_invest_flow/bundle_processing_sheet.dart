import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../design_system/design_system.dart';
import '../../../data/bundle_api.dart';
import '../../../data/exchange_api.dart';
import 'bundle_invest_flow_controller.dart';

/// STEP 4 — Processing + Success / Error bottom sheet.
class BundleProcessingSheet extends StatefulWidget {
  const BundleProcessingSheet({
    super.key,
    required this.bundle,
    required this.sourceAccount,
    required this.amount,
    required this.fundingAsset,
    required this.fiatFormatter,
    this.preloadedResult,
  });

  final BundleItem bundle;
  final BundleSourceAccount sourceAccount;
  final double amount;
  final String fundingAsset;
  final NumberFormat fiatFormatter;

  /// When non-null, skip execution and display this result directly.
  final BundleInvestResult? preloadedResult;

  @override
  State<BundleProcessingSheet> createState() => _BundleProcessingSheetState();
}

enum _SheetPhase { processing, success, partial, error }

class _BundleProcessingSheetState extends State<BundleProcessingSheet> {
  final BundleApi _bundleApi = const BundleApi();

  late _SheetPhase _phase;
  BundleInvestResult? _result;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    final preloaded = widget.preloadedResult;
    if (preloaded != null) {
      _result = preloaded;
      if (preloaded.isCompleted) {
        _phase = _SheetPhase.success;
      } else if (preloaded.isPartial) {
        _phase = _SheetPhase.partial;
      } else {
        _phase = _SheetPhase.error;
        _errorMessage = _humanError(preloaded.errorCode ?? 'unknown');
      }
    } else {
      _phase = _SheetPhase.processing;
      _execute();
    }
  }

  Future<void> _execute() async {
    try {
      final result = await _bundleApi.investInBundle(
        portfolioId: widget.bundle.portfolioId,
        fundingAsset: widget.fundingAsset,
        fundingAmount: widget.amount,
      );
      if (!mounted) return;

      if (result.isCompleted) {
        setState(() {
          _phase = _SheetPhase.success;
          _result = result;
        });
        await Future.delayed(const Duration(milliseconds: 2500));
        if (mounted) Navigator.of(context).pop(true);
      } else if (result.isPartial) {
        setState(() {
          _phase = _SheetPhase.partial;
          _result = result;
        });
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
        _errorMessage = 'Erreur lors de l\'investissement';
      });
    }
  }

  String _humanError(String code) {
    final lc = code.toLowerCase();
    if (lc.contains('insufficient_funds')) return 'Solde insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('price_unavailable') || lc.contains('fx_unavailable')) {
      return 'Prix indisponible';
    }
    if (lc.contains('no_target_allocations')) return 'Aucune allocation configurée';
    if (lc.contains('portfolio_not_found')) return 'Bundle introuvable';
    if (lc.contains('funding_asset_not_allowed')) return 'Source non autorisée';
    return 'Erreur lors de l\'investissement';
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
      case _SheetPhase.partial:
        return _buildPartial();
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
          decoration: const BoxDecoration(
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
          'Nous investissons dans votre bundle…',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Cela peut prendre quelques secondes',
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
    final entryAsset = r.entryAsset ?? widget.bundle.entryAssetDefault;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: const BoxDecoration(
            color: AppColors.textPrimary,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.check_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Investissement réussi',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          widget.sourceAccount.isFiat
              ? widget.fiatFormatter.format(widget.amount)
              : '${widget.amount.toStringAsFixed(2)} ${widget.sourceAccount.currency}',
          textAlign: TextAlign.center,
          style: AppTypography.heroAmount.copyWith(
            color: AppColors.textPrimary,
            fontSize: 28,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${widget.bundle.name} · via $entryAsset',
          textAlign: TextAlign.center,
          style: AppTypography.meta.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        if (r.legsSucceeded != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${r.legsSucceeded} allocation${(r.legsSucceeded ?? 0) > 1 ? 's' : ''} réussie${(r.legsSucceeded ?? 0) > 1 ? 's' : ''}',
            textAlign: TextAlign.center,
            style: AppTypography.meta.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildPartial() {
    final r = _result!;
    final cashRemaining = r.cashLegRemaining ?? 0;
    final entryAsset = r.entryAsset ?? widget.bundle.entryAssetDefault;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: Colors.amber.shade700,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.warning_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Investissement partiel',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          '${r.legsSucceeded ?? 0} sur ${(r.legsSucceeded ?? 0) + (r.legsFailed ?? 0)} allocations réussies',
          textAlign: TextAlign.center,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        if (cashRemaining > 0) ...[
          const SizedBox(height: 4),
          Text(
            'Reliquat : ${cashRemaining.toStringAsFixed(2)} $entryAsset dans le cash leg',
            textAlign: TextAlign.center,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.xxl),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.indigo,
              foregroundColor: Colors.white,
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

  Widget _buildError() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: const BoxDecoration(
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
