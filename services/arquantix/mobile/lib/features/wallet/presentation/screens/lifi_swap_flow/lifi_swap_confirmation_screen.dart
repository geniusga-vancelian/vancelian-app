import 'package:flutter/material.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/lifi_swap_api.dart';
import 'lifi_swap_flow_format.dart';
import 'lifi_swap_processing_sheet.dart';

/// Étape 4 — confirmation avec détail et case à cocher.
class LifiSwapConfirmationScreen extends StatefulWidget {
  const LifiSwapConfirmationScreen({
    super.key,
    required this.fromAsset,
    required this.fromAssetName,
    required this.fromChain,
    this.fromLogoUrl,
    required this.toAsset,
    required this.toAssetName,
    required this.toChain,
    required this.amountFrom,
    required this.quote,
  });

  final String fromAsset;
  final String fromAssetName;
  final String fromChain;
  final String? fromLogoUrl;
  final String toAsset;
  final String toAssetName;
  final String toChain;
  final double amountFrom;
  final LifiSwapQuote quote;

  @override
  State<LifiSwapConfirmationScreen> createState() =>
      _LifiSwapConfirmationScreenState();
}

class _LifiSwapConfirmationScreenState extends State<LifiSwapConfirmationScreen> {
  bool _acknowledged = false;
  bool _executing = false;

  String? get _resolvedFromLogo {
    if (widget.fromLogoUrl != null && widget.fromLogoUrl!.isNotEmpty) {
      return widget.fromLogoUrl;
    }
    final slug = widget.fromAsset.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  String? get _resolvedToLogo {
    final slug = widget.toAsset.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  String get _feeLabel {
    final parts = <String>[];
    final vFee = double.tryParse(widget.quote.vancelianFee) ?? 0;
    final nFee = double.tryParse(widget.quote.networkFee) ?? 0;
    if (vFee > 0) {
      parts.add(
        '${LifiSwapFlowFormat.formatCryptoAmount(vFee)} ${widget.fromAsset} (Vancelian)',
      );
    }
    if (nFee > 0) {
      final asset = widget.quote.networkFeeAsset ?? widget.fromAsset;
      parts.add('${LifiSwapFlowFormat.formatCryptoAmount(nFee)} $asset (réseau)');
    }
    return parts.isEmpty ? 'Aucun' : parts.join(' · ');
  }

  String get _routeLabel {
    if (widget.quote.routeSteps.isNotEmpty) {
      return widget.quote.routeSteps.join(' → ');
    }
    return 'Route ${LifiSwapFlowFormat.chainLabel(widget.fromChain)} → ${LifiSwapFlowFormat.chainLabel(widget.toChain)}';
  }

  Future<void> _confirm() async {
    if (!_acknowledged || _executing) return;
    setState(() => _executing = true);

    final didSwap = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      enableDrag: false,
      backgroundColor: Colors.transparent,
      builder: (_) => LifiSwapProcessingSheet(
        fromAsset: widget.fromAsset,
        toAsset: widget.toAsset,
        quote: widget.quote,
      ),
    );

    if (!mounted) return;
    setState(() => _executing = false);
    if (didSwap == true) {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final fromAmount = LifiSwapFlowFormat.formatCryptoAmount(widget.amountFrom);
    final toAmount = LifiSwapFlowFormat.formatCryptoString(widget.quote.estimatedReceive);
    final minReceive = LifiSwapFlowFormat.formatCryptoString(widget.quote.estimatedReceiveMin);

    return ConfirmationPageLayout(
      onBack: _executing ? () {} : () => Navigator.of(context).pop(),
      executing: _executing,
      directionIndicator: CryptoExchangeWidget(
        fromTicker: widget.fromAsset,
        toTicker: widget.toAsset,
        fromLogoUrl: _resolvedFromLogo,
        toLogoUrl: _resolvedToLogo,
      ),
      headline: 'Vous êtes sur le point de convertir',
      heroAmount: '$fromAmount ${widget.fromAsset}',
      approximateValue: '≈ $toAmount ${widget.toAsset}',
      ctaLabel: 'Confirmer la conversion',
      onConfirm: _acknowledged && !_executing ? _confirm : null,
      bodyChildren: [
        TransactionStepsModule(
          title: 'Détail de votre conversion',
          steps: [
            TransactionStepItem(
              number: 1,
              title: 'Préparation de la route',
              primaryText: _routeLabel,
              secondaryText: widget.quote.exchangeRate != null
                  ? 'Taux estimé : 1 ${widget.fromAsset} ≈ ${LifiSwapFlowFormat.formatCryptoString(widget.quote.exchangeRate!)} ${widget.toAsset}'
                  : 'Route optimisée via LI.FI',
              state: TransactionStepState.pending,
            ),
            TransactionStepItem(
              number: 2,
              title: 'Conversion estimée',
              primaryText:
                  '$fromAmount ${widget.fromAsset}  →  ≈ $toAmount ${widget.toAsset}',
              secondaryText: 'Minimum garanti : $minReceive ${widget.toAsset}',
              approximate: true,
              state: TransactionStepState.pending,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        SettingsCard(
          children: [
            SettingsListItem(title: 'Frais', value: _feeLabel),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        _AckCheckbox(
          value: _acknowledged,
          enabled: !_executing,
          onChanged: (v) => setState(() => _acknowledged = v),
        ),
      ],
    );
  }
}

class _AckCheckbox extends StatelessWidget {
  const _AckCheckbox({
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  final bool value;
  final bool enabled;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.cardBackground,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: enabled ? () => onChanged(!value) : null,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Checkbox(
                value: value,
                onChanged: enabled ? (v) => onChanged(v ?? false) : null,
                activeColor: AppColors.indigo,
              ),
              Expanded(
                child: Text(
                  'En confirmant, j\'accepte que cette conversion soit exécutée au prix estimé. Le montant final peut varier légèrement.',
                  style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
