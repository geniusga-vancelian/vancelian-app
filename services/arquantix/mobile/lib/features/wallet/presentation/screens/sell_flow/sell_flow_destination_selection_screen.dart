import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../../../ui/components/transaction/transaction_avatar.dart';
import '../../../../../ui/components/transaction/transaction_tile.dart';
import '../../../data/cash_api.dart';
import 'sell_flow_amount_screen.dart';
import 'sell_flow_controller.dart';

/// STEP 1 — Destination account selection.
///
/// For v1: only Compte Euro as destination for the fiat proceeds.
class SellFlowDestinationSelectionScreen extends StatefulWidget {
  const SellFlowDestinationSelectionScreen({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    this.assetLogoUrl,
    required this.cryptoBalance,
  });

  final String assetSymbol;
  final String assetName;
  final String? assetLogoUrl;
  final double cryptoBalance;

  @override
  State<SellFlowDestinationSelectionScreen> createState() =>
      _SellFlowDestinationSelectionScreenState();
}

class _SellFlowDestinationSelectionScreenState
    extends State<SellFlowDestinationSelectionScreen> {
  final CashApi _cashApi = const CashApi();

  bool _loading = true;
  double _eurBalance = 0;

  static final _fiatFormatter = NumberFormat.currency(
    locale: 'fr_FR', symbol: '€', decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    _loadBalance();
  }

  Future<void> _loadBalance() async {
    try {
      final cashData = await _cashApi.fetchCashData();
      final account = cashData.cashAccount;
      if (!mounted) return;
      setState(() {
        _eurBalance = account?.availableBalance ?? 0;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  void _selectEuroAccount() {
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => SellFlowAmountScreen(
          assetSymbol: widget.assetSymbol,
          assetName: widget.assetName,
          assetLogoUrl: widget.assetLogoUrl,
          cryptoBalance: widget.cryptoBalance,
          destinationLabel: 'Compte Euro',
          destinationBalance: _eurBalance,
        ),
      ),
    ).then((didSell) {
      if (didSell == true && mounted) {
        Navigator.of(context).pop(true);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).pop(false),
        actions: const [],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(
                color: AppColors.indigo,
                strokeWidth: 2,
              ),
            )
          : _buildBody(),
    );
  }

  Widget _buildBody() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        const SizedBox(height: AppSpacing.md),
        AppPageTitle('Vendre du ${widget.assetName}'),
        const SizedBox(height: 8),
        Text(
          'Vers quel compte souhaitez-vous recevoir le produit de la vente ?',
          style: AppTypography.titleLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 28),
        _buildDestinationsCard(),
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildDestinationsCard() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TransactionTile(
              avatar: const TransactionAvatar(
                icon: Icons.euro_rounded,
                backgroundColor: Colors.blue,
                iconColor: Colors.white,
              ),
              title: 'Compte Euro',
              subtitle: null,
              rightPrimary: _fiatFormatter.format(_eurBalance),
              onTap: _selectEuroAccount,
            ),
          ],
        ),
      ),
    );
  }
}
