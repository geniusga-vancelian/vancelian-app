import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/bundle_api.dart';
import '../bundle_invest_flow/bundle_invest_flow_controller.dart';
import 'rebalance_processing_sheet.dart';

/// Rebalance confirmation screen — shows the preview plan and lets the user confirm.
class RebalanceConfirmationScreen extends StatefulWidget {
  const RebalanceConfirmationScreen({
    super.key,
    required this.portfolioId,
    required this.bundleName,
    required this.preview,
  });

  final String portfolioId;
  final String bundleName;
  final RebalancePreviewResult preview;

  @override
  State<RebalanceConfirmationScreen> createState() =>
      _RebalanceConfirmationScreenState();
}

class _RebalanceConfirmationScreenState
    extends State<RebalanceConfirmationScreen> {
  bool _executing = false;

  static final _eurFmt = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );
  static final _usdFmt = NumberFormat.currency(
    locale: 'en_US',
    symbol: '\$',
    decimalDigits: 2,
  );

  NumberFormat get _fmt =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _usdFmt
          : _eurFmt;

  RebalancePreviewResult get _p => widget.preview;

  Future<void> _confirmRebalance() async {
    if (_executing) return;
    setState(() => _executing = true);

    if (!mounted) return;

    final didRebalance = await showModalBottomSheet<bool>(
      context: context,
      isDismissible: false,
      enableDrag: false,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      builder: (_) => RebalanceProcessingSheet(
        portfolioId: widget.portfolioId,
        bundleName: widget.bundleName,
      ),
    );

    if (!mounted) return;

    if (didRebalance == true) {
      Navigator.of(context).pop(true);
    } else {
      setState(() => _executing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SizedBox(height: 32),
                    Text(
                      'Rééquilibrer',
                      textAlign: TextAlign.center,
                      style: AppTypography.titleLarge.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.bundleName,
                      textAlign: TextAlign.center,
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Valeur totale : ${_fmt.format(_p.baseValueEur)}',
                      textAlign: TextAlign.center,
                      style: AppTypography.heroAmount.copyWith(
                        color: AppColors.textPrimary,
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 32),
                    _buildSummaryTable(),
                    if (_p.sellPlan.isNotEmpty) ...[
                      const SizedBox(height: 20),
                      _buildTradeSection(
                        'Ventes prévues',
                        _p.sellPlan,
                        isSell: true,
                      ),
                    ],
                    if (_p.buyPlan.isNotEmpty) ...[
                      const SizedBox(height: 20),
                      _buildTradeSection(
                        'Achats prévus',
                        _p.buyPlan,
                        isSell: false,
                      ),
                    ],
                    if (_p.warnings.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      _buildWarnings(),
                    ],
                    const SizedBox(height: 20),
                    _buildInfoBox(),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
            _buildBottomBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      child: SizedBox(
        height: kToolbarHeight,
        child: Row(
          children: [
            BundleFlowHeaderDisk(
              onTap: _executing ? () {} : () => Navigator.of(context).pop(),
              child: const Icon(Icons.arrow_back_rounded,
                  size: 20, color: AppColors.textPrimary),
            ),
            const Spacer(),
            Text(
              'Confirmation',
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.indigo.withValues(alpha: 0.12),
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.tune_rounded,
                size: 18,
                color: AppColors.indigo,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryTable() {
    final rows = <TableInformationRowData>[
      TableInformationRowData(
        left: 'Valeur du bundle',
        right: _fmt.format(_p.baseValueEur),
      ),
      if (_p.cashLegValueEur > 0.01)
        TableInformationRowData(
          left: 'Cash leg disponible',
          right: _fmt.format(_p.cashLegValueEur),
        ),
      TableInformationRowData(
        left: 'Ventes',
        right: '${_p.sellPlan.length} trade${_p.sellPlan.length > 1 ? 's' : ''}',
      ),
      TableInformationRowData(
        left: 'Achats',
        right: '${_p.buyPlan.length} trade${_p.buyPlan.length > 1 ? 's' : ''}',
      ),
      TableInformationRowData(
        left: 'Cash leg estimé après',
        right: _fmt.format(_p.estimatedResidualCashLeg),
      ),
    ];
    return TableInformationModule(rows: rows);
  }

  Widget _buildTradeSection(
    String title,
    List<RebalanceTradePlan> trades, {
    required bool isSell,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            title,
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: trades.map((t) {
                  final icon = isSell
                      ? Icons.remove_rounded
                      : Icons.add_rounded;
                  final color = isSell
                      ? const Color(0xFFDC2626)
                      : const Color(0xFF059669);
                  return ListTile(
                    dense: true,
                    leading: Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: color.withValues(alpha: 0.12),
                      ),
                      alignment: Alignment.center,
                      child: Icon(icon, size: 18, color: color),
                    ),
                    title: Text(
                      t.asset,
                      style: AppTypography.bodyMedium.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    trailing: Text(
                      '≈ ${_fmt.format(t.estimatedValueEur)}',
                      style: AppTypography.bodyMedium.copyWith(
                        color: color,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildWarnings() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF3CD),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.warning_amber_rounded,
              size: 18, color: Color(0xFF856404)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _p.warnings.join('\n'),
              style: AppTypography.bodySmall.copyWith(
                color: const Color(0xFF856404),
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoBox() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.indigo.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.info_outline_rounded,
            size: 18,
            color: AppColors.indigo.withValues(alpha: 0.7),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Les assets surpondérés seront vendus puis le produit sera réinvesti dans les assets sous-pondérés pour réaligner l\'allocation cible.',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textPrimary.withValues(alpha: 0.7),
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomBar() {
    return Container(
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewPadding.bottom > 0 ? 8 : 16,
        top: 12,
      ),
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        border: Border(
          top: BorderSide(
              color: AppColors.textPrimary.withValues(alpha: 0.06)),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cardBackground,
              boxShadow: [
                BoxShadow(
                  color: AppColors.textPrimary.withValues(alpha: 0.06),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            alignment: Alignment.center,
            child: IconButton(
              icon: const Icon(Icons.arrow_back_rounded,
                  size: 22, color: AppColors.textSecondary),
              onPressed:
                  _executing ? null : () => Navigator.of(context).pop(),
              padding: EdgeInsets.zero,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SizedBox(
              height: 52,
              child: ElevatedButton(
                onPressed: _executing ? null : _confirmRebalance,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.indigo,
                  foregroundColor: Colors.white,
                  disabledBackgroundColor: AppColors.indigo,
                  disabledForegroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 4,
                  shadowColor: AppColors.indigo.withValues(alpha: 0.35),
                ),
                child: _executing
                    ? Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            'Exécution…',
                            style: AppTypography.bodyMedium.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      )
                    : Text(
                        'Confirmer le rééquilibrage',
                        style: AppTypography.titleMedium.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
