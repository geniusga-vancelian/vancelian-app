import 'package:flutter/material.dart';

import '../../../../../design_system/design_system.dart';
import '../../../data/lifi_swap_api.dart';
import '../../../privy/privy_auth_provider.dart';
import 'lifi_swap_flow_format.dart';

enum _LifiSwapPhase { preparing, signing, bridging, completed, failed }

/// Bottom sheet de traitement — signature Privy + polling LI.FI.
class LifiSwapProcessingSheet extends StatefulWidget {
  const LifiSwapProcessingSheet({
    super.key,
    required this.fromAsset,
    required this.toAsset,
    required this.quote,
  });

  final String fromAsset;
  final String toAsset;
  final LifiSwapQuote quote;

  @override
  State<LifiSwapProcessingSheet> createState() => _LifiSwapProcessingSheetState();
}

class _LifiSwapProcessingSheetState extends State<LifiSwapProcessingSheet> {
  final _api = const LifiSwapApi();
  final _privy = createPrivyAuthProvider();

  _LifiSwapPhase _phase = _LifiSwapPhase.preparing;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _execute();
  }

  Future<void> _execute() async {
    try {
      setState(() => _phase = _LifiSwapPhase.preparing);
      final exec = await _api.prepareExecute(widget.quote.swapId);
      final tx = exec.transaction;
      if (tx == null) {
        throw LifiSwapApiException('Payload transaction manquant.');
      }

      if (!mounted) return;
      setState(() => _phase = _LifiSwapPhase.signing);

      final txHash = await _privy.sendEthereumTransaction(
        chainId: tx.chainIdInt,
        to: tx.to,
        data: tx.data,
        value: tx.value,
        gasLimit: tx.gasLimit,
      );

      if (!mounted) return;
      setState(() => _phase = _LifiSwapPhase.bridging);

      await _api.submitTx(widget.quote.swapId, txHash);
      final status = await _api.pollUntilTerminal(widget.quote.swapId);

      if (!mounted) return;
      if (status.status == 'FAILED' || status.status == 'EXPIRED') {
        throw LifiSwapApiException(status.errorMessage ?? 'Swap échoué');
      }

      setState(() => _phase = _LifiSwapPhase.completed);
      await Future<void>.delayed(const Duration(milliseconds: 1800));
      if (mounted) Navigator.of(context).pop(true);
    } on LifiSwapApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _LifiSwapPhase.failed;
        _errorMessage = e.message;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _LifiSwapPhase.failed;
        _errorMessage = 'Exécution impossible';
      });
    }
  }

  TransactionStepState _routeStepState() {
    switch (_phase) {
      case _LifiSwapPhase.preparing:
      case _LifiSwapPhase.signing:
        return TransactionStepState.processing;
      case _LifiSwapPhase.bridging:
      case _LifiSwapPhase.completed:
        return TransactionStepState.completed;
      case _LifiSwapPhase.failed:
        return TransactionStepState.pending;
    }
  }

  TransactionStepState _conversionStepState() {
    switch (_phase) {
      case _LifiSwapPhase.preparing:
      case _LifiSwapPhase.signing:
        return TransactionStepState.pending;
      case _LifiSwapPhase.bridging:
        return TransactionStepState.processing;
      case _LifiSwapPhase.completed:
        return TransactionStepState.completed;
      case _LifiSwapPhase.failed:
        return TransactionStepState.pending;
    }
  }

  String get _phaseLabel {
    switch (_phase) {
      case _LifiSwapPhase.preparing:
        return 'Préparation de la route...';
      case _LifiSwapPhase.signing:
        return 'Signature dans votre wallet...';
      case _LifiSwapPhase.bridging:
        return 'Finalisation sur la blockchain...';
      case _LifiSwapPhase.completed:
        return 'Conversion effectuée';
      case _LifiSwapPhase.failed:
        return 'Conversion échouée';
    }
  }

  String get _routeLabel {
    if (widget.quote.routeSteps.isNotEmpty) {
      return widget.quote.routeSteps.join(' → ');
    }
    return 'Route LI.FI';
  }

  @override
  Widget build(BuildContext context) {
    final isFailed = _phase == _LifiSwapPhase.failed;
    final isSuccess = _phase == _LifiSwapPhase.completed;
    final isProcessing = !isFailed && !isSuccess;

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
              _StatusIcon(phase: _phase),
              const SizedBox(height: AppSpacing.lg),
              Text(
                isSuccess
                    ? 'Conversion effectuée'
                    : isFailed
                        ? 'Conversion échouée'
                        : 'Nous traitons votre swap',
                textAlign: TextAlign.center,
                style: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                isSuccess
                    ? '+${LifiSwapFlowFormat.formatCryptoString(widget.quote.estimatedReceive)} ${widget.toAsset}'
                    : isFailed
                        ? (_errorMessage ?? 'Erreur')
                        : _phaseLabel,
                textAlign: TextAlign.center,
                style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
              ),
              if (isSuccess) ...[
                const SizedBox(height: 4),
                Text(
                  'pour ${LifiSwapFlowFormat.formatCryptoString(widget.quote.amountIn)} ${widget.fromAsset}',
                  textAlign: TextAlign.center,
                  style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
                ),
              ],
              if (isProcessing) ...[
                const SizedBox(height: AppSpacing.lg),
                TransactionStepsModule(
                  title: 'Étapes en cours',
                  steps: [
                    TransactionStepItem(
                      number: 1,
                      title: 'Préparation de la route',
                      primaryText: _routeLabel,
                      state: _routeStepState(),
                    ),
                    TransactionStepItem(
                      number: 2,
                      title: 'Conversion estimée',
                      primaryText:
                          '${LifiSwapFlowFormat.formatCryptoString(widget.quote.amountIn)} ${widget.fromAsset} → ≈ ${LifiSwapFlowFormat.formatCryptoString(widget.quote.estimatedReceive)} ${widget.toAsset}',
                      approximate: true,
                      state: _conversionStepState(),
                    ),
                  ],
                ),
              ],
              if (isFailed) ...[
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
                      elevation: 0,
                    ),
                    child: const Text('Fermer'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusIcon extends StatelessWidget {
  const _StatusIcon({required this.phase});
  final _LifiSwapPhase phase;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 64,
      height: 64,
      decoration: const BoxDecoration(
        color: AppColors.textPrimary,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: switch (phase) {
        _LifiSwapPhase.completed => const Icon(Icons.check_rounded, size: 32, color: Colors.white),
        _LifiSwapPhase.failed => const Icon(Icons.close_rounded, size: 32, color: Colors.white),
        _ => const SizedBox(
            width: 28,
            height: 28,
            child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
          ),
      },
    );
  }
}
