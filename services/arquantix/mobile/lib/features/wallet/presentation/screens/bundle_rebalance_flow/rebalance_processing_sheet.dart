import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../design_system/design_system.dart';
import '../../../data/bundle_api.dart';
import '../../../data/exchange_api.dart';

/// Bottom sheet for rebalance execution: processing → success / partial / error.
class RebalanceProcessingSheet extends StatefulWidget {
  const RebalanceProcessingSheet({
    super.key,
    required this.portfolioId,
    required this.bundleName,
  });

  final String portfolioId;
  final String bundleName;

  @override
  State<RebalanceProcessingSheet> createState() =>
      _RebalanceProcessingSheetState();
}

enum _SheetPhase { processing, success, partial, error }

class _RebalanceProcessingSheetState extends State<RebalanceProcessingSheet> {
  final BundleApi _api = const BundleApi();

  _SheetPhase _phase = _SheetPhase.processing;
  RebalanceExecuteResult? _result;
  String? _errorMessage;

  static final _eurFmt = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    _execute();
  }

  Future<void> _execute() async {
    try {
      final result = await _api.executeRebalance(
        portfolioId: widget.portfolioId,
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
      } else if (result.isNoAction) {
        setState(() {
          _phase = _SheetPhase.success;
          _result = result;
        });
        await Future.delayed(const Duration(milliseconds: 2000));
        if (mounted) Navigator.of(context).pop(true);
      } else {
        setState(() {
          _phase = _SheetPhase.error;
          _errorMessage = result.message ?? 'Échec du rééquilibrage';
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
        _errorMessage = 'Erreur lors du rééquilibrage';
      });
    }
  }

  String _humanError(String code) {
    final lc = code.toLowerCase();
    if (lc.contains('insufficient')) return 'Solde insuffisant';
    if (lc.contains('stale') || lc.contains('quote')) return 'Prix du marché expiré';
    if (lc.contains('price_unavailable')) return 'Prix indisponible';
    if (lc.contains('portfolio_not_found')) return 'Bundle introuvable';
    return 'Erreur lors du rééquilibrage';
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
          'Rééquilibrage en cours…',
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
    final r = _result;
    final isNoAction = r != null && r.isNoAction;

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
          isNoAction ? 'Déjà équilibré' : 'Rééquilibrage réussi',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          widget.bundleName,
          textAlign: TextAlign.center,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        if (r != null && !isNoAction) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${r.totalCompleted} trade${r.totalCompleted > 1 ? 's' : ''} exécuté${r.totalCompleted > 1 ? 's' : ''}',
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
          child:
              const Icon(Icons.warning_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Rééquilibrage partiel',
          textAlign: TextAlign.center,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          '${r.totalCompleted} sur ${r.totalTrades} trades réussis',
          textAlign: TextAlign.center,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        if (r.cashLegAfter > 0.01) ...[
          const SizedBox(height: 4),
          Text(
            'Cash leg restant : ${_eurFmt.format(r.cashLegAfter)}',
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
          child:
              const Icon(Icons.close_rounded, size: 32, color: Colors.white),
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
