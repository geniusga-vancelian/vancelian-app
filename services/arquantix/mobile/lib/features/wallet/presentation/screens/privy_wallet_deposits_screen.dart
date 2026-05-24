import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../data/privy_wallet_api.dart';
import 'privy_wallet_deposit_detail_screen.dart';

/// Historique complet des dépôts reçus sur le wallet Privy.
class PrivyWalletDepositsScreen extends StatefulWidget {
  const PrivyWalletDepositsScreen({super.key, this.assetFilter});

  final String? assetFilter;

  @override
  State<PrivyWalletDepositsScreen> createState() => _PrivyWalletDepositsScreenState();
}

class _PrivyWalletDepositsScreenState extends State<PrivyWalletDepositsScreen> {
  final PrivyWalletApi _api = const PrivyWalletApi();
  List<PrivyWalletDepositItem>? _deposits;
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
      final list = await _api.fetchDeposits(asset: widget.assetFilter);
      if (!mounted) return;
      setState(() {
        _deposits = list;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Impossible de charger les dépôts.';
      });
    }
  }

  String _dayLabel(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final txDay = DateTime(dt.year, dt.month, dt.day);
    final diff = today.difference(txDay).inDays;
    if (diff == 0) return "Aujourd'hui";
    if (diff == 1) return 'Hier';
    return '${dt.day} ${_frenchMonths[dt.month - 1]} ${dt.year}';
  }

  List<(String, List<PrivyWalletDepositItem>)> _groupByDay(List<PrivyWalletDepositItem> txs) {
    final groups = <String, List<PrivyWalletDepositItem>>{};
    for (final tx in txs) {
      final label = _dayLabel(tx.createdAt);
      (groups[label] ??= []).add(tx);
    }
    return groups.entries.map((e) => (e.key, e.value)).toList();
  }

  void _openDetail(PrivyWalletDepositItem item) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => PrivyWalletDepositDetailScreen(depositId: item.id),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.assetFilter != null
        ? 'Dépôts ${widget.assetFilter!.toUpperCase()}'
        : 'Dépôts reçus';

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: Text(title),
        titleTextStyle: AppTypography.sectionTitle,
        backgroundColor: AppColors.cardBackground,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: _loading
              ? ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: const [
                    SizedBox(height: 120),
                    Center(child: CircularProgressIndicator(color: AppColors.indigo)),
                  ],
                )
              : _error != null
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(AppSpacing.xl),
                      children: [
                        Text(
                          _error!,
                          style: AppTypography.bodyRegular.copyWith(
                            color: AppColors.semanticDanger,
                          ),
                        ),
                      ],
                    )
                  : _buildContent(),
        ),
      ),
    );
  }

  Widget _buildContent() {
    final deposits = _deposits ?? [];
    if (deposits.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.xl),
        children: [
          Text(
            'Aucun dépôt reçu pour le moment.',
            style: AppTypography.bodyRegular.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Les transferts entrants sur votre adresse Privy apparaîtront ici '
            'dès confirmation par le réseau.',
            style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
          ),
        ],
      );
    }

    final groups = _groupByDay(deposits);
    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.xl,
        vertical: AppSpacing.lg,
      ),
      itemCount: groups.length,
      itemBuilder: (context, index) {
        final (day, items) = groups[index];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (index > 0) const SizedBox(height: AppSpacing.lg),
            Text(
              day,
              style: AppTypography.labelRegular.copyWith(color: AppColors.textMuted),
            ),
            const SizedBox(height: AppSpacing.sm),
            ...items.map((item) => _DepositTile(item: item, onTap: () => _openDetail(item))),
          ],
        );
      },
    );
  }
}

class _DepositTile extends StatelessWidget {
  const _DepositTile({required this.item, required this.onTap});

  final PrivyWalletDepositItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hh = item.createdAt.hour.toString().padLeft(2, '0');
    final mm = item.createdAt.minute.toString().padLeft(2, '0');
    final amountLabel = '+${item.amount} ${item.asset}';
    final logoUrl = Config.resolveLogoUrl(
      '/media/crypto_logos/${item.asset.toLowerCase()}.png',
    );

    return Material(
      color: AppColors.cardBackground,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.md,
          ),
          child: Row(
            children: [
              CircleAvatar(
                radius: 20,
                backgroundColor: AppColors.semanticPositiveLight,
                backgroundImage: logoUrl != null ? NetworkImage(logoUrl) : null,
                onBackgroundImageError: logoUrl != null ? (_, __) {} : null,
                child: logoUrl == null
                    ? const Icon(Icons.arrow_downward_rounded, size: 18)
                    : null,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
                    ),
                    Text(
                      '$hh:$mm · ${item.status}',
                      style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              Text(
                amountLabel,
                style: AppTypography.itemSecondary.copyWith(
                  color: AppColors.semanticPositive,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
