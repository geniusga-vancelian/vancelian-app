import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../design_system/design_system.dart';
import '../../../data/exchange_api.dart';

class SellAllProcessingSheet extends StatefulWidget {
  const SellAllProcessingSheet({
    super.key,
    required this.preview,
    required this.exchangeApi,
    this.preloadedResult,
    this.preloadedError,
  });

  final SellAllPreviewResult preview;
  final ExchangeApi exchangeApi;

  /// When non-null, skip execution and display this result directly.
  final SellAllResult? preloadedResult;

  /// When non-null, skip execution and display this error directly.
  final String? preloadedError;

  @override
  State<SellAllProcessingSheet> createState() => _SellAllProcessingSheetState();
}

enum _SheetState { processing, success, error }

class _SellAllProcessingSheetState extends State<SellAllProcessingSheet> {
  late _SheetState _state;
  SellAllResult? _result;
  String? _errorMessage;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    if (widget.preloadedResult != null) {
      _result = widget.preloadedResult;
      _state = _SheetState.success;
    } else if (widget.preloadedError != null) {
      _errorMessage = widget.preloadedError;
      _state = _SheetState.error;
    } else {
      _state = _SheetState.processing;
      _execute();
    }
  }

  Future<void> _execute() async {
    try {
      final result = await widget.exchangeApi.executeSellAll();
      if (!mounted) return;
      setState(() {
        _result = result;
        _state = _SheetState.success;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e is ExchangeApiException ? e.message : e.toString();
        _state = _SheetState.error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.textSecondary.withValues(alpha: 0.25),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 24),
          if (_state == _SheetState.processing) _buildProcessing(),
          if (_state == _SheetState.success) _buildSuccess(),
          if (_state == _SheetState.error) _buildError(),
        ],
      ),
    );
  }

  Widget _buildProcessing() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(
          width: 52,
          height: 52,
          child: CircularProgressIndicator(
            color: AppColors.indigo,
            strokeWidth: 3,
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Liquidation en cours...',
          style: AppTypography.titleLarge.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Nous vendons vos positions crypto une par une. Veuillez patienter.',
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildSuccess() {
    final r = _result!;
    final allSuccess = r.totalAssetsFailed == 0;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: allSuccess
                ? const Color(0xFF059669).withValues(alpha: 0.12)
                : const Color(0xFFF59E0B).withValues(alpha: 0.12),
          ),
          child: Icon(
            allSuccess ? Icons.check_rounded : Icons.warning_amber_rounded,
            color: allSuccess ? const Color(0xFF059669) : const Color(0xFFF59E0B),
            size: 32,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          allSuccess ? 'Liquidation terminée' : 'Liquidation partielle',
          style: AppTypography.titleLarge.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.pageBackground,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              _resultRow('Total reçu', _eurFormatter.format(r.actualTotalEurReceived),
                  isBold: true),
              _resultRow('Positions vendues', '${r.totalAssetsSold}'),
              if (r.totalAssetsFailed > 0)
                _resultRow('Positions échouées', '${r.totalAssetsFailed}',
                    valueColor: const Color(0xFFDC2626)),
            ],
          ),
        ),
        if (r.results.isNotEmpty) ...[
          const SizedBox(height: 16),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 200),
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: r.results.length,
              separatorBuilder: (_, __) => Divider(
                height: 1,
                color: AppColors.textSecondary.withValues(alpha: 0.12),
              ),
              itemBuilder: (_, i) {
                final item = r.results[i];
                final isOk = item.isCompleted;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Row(
                    children: [
                      Icon(
                        isOk ? Icons.check_circle_outline : Icons.error_outline,
                        color: isOk ? const Color(0xFF059669) : const Color(0xFFDC2626),
                        size: 20,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          item.asset,
                          style: AppTypography.bodyMedium.copyWith(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Text(
                        isOk
                            ? _eurFormatter.format(
                                double.tryParse(item.eurReceived ?? '0') ?? 0)
                            : item.errorCode ?? 'Erreur',
                        style: AppTypography.bodySmall.copyWith(
                          color: isOk ? AppColors.textPrimary : const Color(0xFFDC2626),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.indigo,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            child: const Text('Fermer', style: TextStyle(fontWeight: FontWeight.w700)),
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
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: const Color(0xFFDC2626).withValues(alpha: 0.12),
          ),
          child: const Icon(Icons.close_rounded, color: Color(0xFFDC2626), size: 32),
        ),
        const SizedBox(height: 16),
        Text(
          'Erreur',
          style: AppTypography.titleLarge.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          _errorMessage ?? 'Une erreur est survenue',
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: () => Navigator.of(context).pop(false),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.indigo,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            child: const Text('Fermer', style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ),
      ],
    );
  }

  Widget _resultRow(String label, String value,
      {bool isBold = false, Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
          ),
          Text(
            value,
            style: AppTypography.bodyMedium.copyWith(
              color: valueColor ?? AppColors.textPrimary,
              fontWeight: isBold ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
