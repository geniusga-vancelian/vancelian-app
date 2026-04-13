import 'package:flutter/material.dart';

import '../../../../../design_system/design_system.dart';
import '../../../data/lending_invest_api.dart';
import '../../../domain/models/offer_project.dart';
import '../../../../placements/presentation/screens/placements_screen.dart';

enum _Phase { processing, success, error }

class LendingInvestProcessingSheet extends StatefulWidget {
  const LendingInvestProcessingSheet({
    super.key,
    required this.project,
    required this.fundingAsset,
    required this.fundingAmount,
  });

  final OfferProject project;
  final String fundingAsset;
  final double fundingAmount;

  @override
  State<LendingInvestProcessingSheet> createState() =>
      _LendingInvestProcessingSheetState();
}

class _LendingInvestProcessingSheetState
    extends State<LendingInvestProcessingSheet> {
  final LendingInvestApi _api = const LendingInvestApi();
  _Phase _phase = _Phase.processing;
  LendingInvestResult? _result;
  String _errorMessage = '';
  String _stepLabel = 'Préparation de l\'investissement…';

  @override
  void initState() {
    super.initState();
    _execute();
  }

  Future<void> _execute() async {
    try {
      final productId = widget.project.lendingProductId;
      if (productId == null || productId.isEmpty) {
        setState(() {
          _phase = _Phase.error;
          _errorMessage = 'Identifiant produit manquant';
        });
        return;
      }

      final requiresConversion = widget.fundingAsset.toUpperCase() !=
          (widget.project.lendingAsset ?? '').toUpperCase();

      if (requiresConversion) {
        setState(() => _stepLabel =
            'Conversion ${widget.fundingAsset} → ${widget.project.lendingAsset}…');
        await Future<void>.delayed(const Duration(milliseconds: 800));
      }

      setState(() => _stepLabel = 'Allocation dans l\'offre…');

      final result = await _api.executeInvest(
        productId: productId,
        fundingAsset: widget.fundingAsset,
        fundingAmount: widget.fundingAmount,
      );

      if (!mounted) return;

      if (result.isCompleted) {
        setState(() {
          _phase = _Phase.success;
          _result = result;
          _stepLabel = 'Investissement confirmé';
        });
      } else {
        setState(() {
          _phase = _Phase.error;
          _errorMessage = 'Statut inattendu : ${result.status}';
        });
      }
    } on LendingInvestApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _Phase.error;
        _errorMessage = e.message;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _Phase.error;
        _errorMessage = 'Erreur de connexion';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
              AppSpacing.xl, AppSpacing.sm, AppSpacing.xl, AppSpacing.xxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.placeholderIcon.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(2),
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
      case _Phase.processing:
        return _buildProcessing();
      case _Phase.success:
        return _buildSuccess();
      case _Phase.error:
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
            shape: BoxShape.circle,
            color: AppColors.textPrimary,
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
          _stepLabel,
          style: AppTypography.sectionTitle,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Veuillez patienter…',
          style: AppTypography.meta,
        ),
        const SizedBox(height: AppSpacing.lg),
      ],
    );
  }

  Widget _buildSuccess() {
    final result = _result!;
    final poolAsset = widget.project.lendingAsset ?? result.entryAssetUsed;
    final suppliedLabel =
        '${result.amountSupplied.toStringAsFixed(2)} $poolAsset';

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.textPrimary,
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.check_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Investissement réussi', style: AppTypography.sectionTitle),
        const SizedBox(height: AppSpacing.sm),
        Text(
          suppliedLabel,
          style: AppTypography.heroAmount
              .copyWith(fontSize: 28, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          '${widget.project.title} · via ${widget.fundingAsset}',
          style: AppTypography.meta,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.xxl),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () {
              Navigator.of(context).pop(true);
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const PlacementsScreen(),
                ),
              );
            },
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.indigo,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button)),
            ),
            child: const Text('Voir dans Placements'),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.placeholderBg,
              foregroundColor: AppColors.textPrimary,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button)),
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
            shape: BoxShape.circle,
            color: AppColors.textPrimary,
          ),
          alignment: Alignment.center,
          child:
              const Icon(Icons.close_rounded, size: 32, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(_errorMessage, style: AppTypography.sectionTitle,
            textAlign: TextAlign.center),
        const SizedBox(height: AppSpacing.xxl),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => Navigator.of(context).pop(false),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.placeholderBg,
              foregroundColor: AppColors.textPrimary,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button)),
            ),
            child: const Text('Fermer'),
          ),
        ),
      ],
    );
  }
}
