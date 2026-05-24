import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../design_system/design_system.dart';
import '../../data/privy_wallet_api.dart';
import '../../widgets/transaction_template.dart';

/// Détail d’un dépôt Privy (tx on-chain, montant, statut).
class PrivyWalletDepositDetailScreen extends StatefulWidget {
  const PrivyWalletDepositDetailScreen({super.key, required this.depositId});

  final String depositId;

  @override
  State<PrivyWalletDepositDetailScreen> createState() =>
      _PrivyWalletDepositDetailScreenState();
}

class _PrivyWalletDepositDetailScreenState extends State<PrivyWalletDepositDetailScreen> {
  final PrivyWalletApi _api = const PrivyWalletApi();
  PrivyWalletDepositItem? _deposit;
  bool _loading = true;
  String? _error;

  static const _frenchMonths = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final item = await _api.fetchDepositDetail(widget.depositId);
      if (!mounted) return;
      setState(() {
        _deposit = item;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Impossible de charger ce dépôt.';
      });
    }
  }

  Future<void> _copy(String value, String label) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$label copié.')),
    );
  }

  String _formatDateTime(DateTime dt) {
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    return '${dt.day} ${_frenchMonths[dt.month - 1]} ${dt.year} · $hh:$mm';
  }

  @override
  Widget build(BuildContext context) {
    return TransactionTemplate(
      title: 'Dépôt reçu',
      child: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.indigo))
          : _error != null
              ? Text(
                  _error!,
                  style: AppTypography.bodyRegular.copyWith(color: AppColors.semanticDanger),
                )
              : _buildDetail(_deposit!),
    );
  }

  Widget _buildDetail(PrivyWalletDepositItem d) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '+${d.amount} ${d.asset}',
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.semanticPositive,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            _formatDateTime(d.createdAt),
            style: AppTypography.bodyRegular.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppSpacing.xxl),
          _row('Statut', d.status),
          _row('Réseau', '${d.chainType}${d.chainId != null ? ' (${d.chainId})' : ''}'),
          _row('Confirmations', '${d.confirmations}'),
          if (d.fromAddress != null) _copyRow('Expéditeur', d.fromAddress!),
          _copyRow('Destinataire', d.toAddress),
          _copyRow('Hash transaction', d.txHash),
          if (d.subtitle != null) ...[
            const SizedBox(height: AppSpacing.lg),
            Text(
              d.subtitle!,
              style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
            ),
          ],
        ],
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTypography.labelRegular.copyWith(color: AppColors.textMuted),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            value,
            style: AppTypography.bodyRegular.copyWith(color: AppColors.textPrimary),
          ),
        ],
      ),
    );
  }

  Widget _copyRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTypography.labelRegular.copyWith(color: AppColors.textMuted),
          ),
          const SizedBox(height: AppSpacing.xs),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: SelectionArea(
                  child: Text(
                    value,
                    style: AppTypography.bodySmRegular.copyWith(
                      color: AppColors.textPrimary,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.copy_rounded, size: 20),
                onPressed: () => _copy(value, label),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
