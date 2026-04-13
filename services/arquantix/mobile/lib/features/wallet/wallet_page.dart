import 'package:flutter/material.dart';

import '../../design_system/design_system.dart';
import '../../ui/components/buttons/action_button_row.dart';
import 'widgets/wallet_header.dart';
import 'widgets/wallet_overlapping_sheet.dart';

const double _expandedHeight = 360;
const double _toolbarHeight = 56;

/// Page Wallet type Revolut : hero qui collapse, barre blanche, feuille qui chevauche.
/// CustomScrollView avec SliverAppBar (pinned), ActionButtonRow, WalletOverlappingSheet, SliverList.
class WalletPage extends StatelessWidget {
  const WalletPage({
    super.key,
    this.balanceAmount = '£0',
    this.balanceTitle = 'Main · GBP',
  });

  final String balanceAmount;
  final String balanceTitle;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: _expandedHeight,
            pinned: true,
            toolbarHeight: _toolbarHeight,
            elevation: 0,
            backgroundColor: Colors.white,
            flexibleSpace: LayoutBuilder(
              builder: (context, constraints) {
                final h = constraints.maxHeight.clamp(_toolbarHeight, _expandedHeight);
                final progress = 1.0 - (h - _toolbarHeight) / (_expandedHeight - _toolbarHeight);
                return SizedBox(
                  height: constraints.maxHeight,
                  child: WalletHeader(
                    progress: progress,
                    balanceTitle: balanceTitle,
                    balanceAmount: balanceAmount,
                  ),
                );
              },
            ),
          ),
          SliverToBoxAdapter(
            child: ActionButtonModule(
              child: ActionButtonRow.defaultActions(
                depositLabel: 'Add money',
                sendLabel: 'Exchange',
                buyLabel: 'Details',
                moreLabel: 'More',
                onDeposit: () {},
                onSend: () {},
                onBuy: () {},
                onMore: () {},
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: WalletOverlappingSheet(
              overlapOffset: -32,
              child: _SheetContent(),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: PortfolioAllocationModule(
                introText:
                    'Votre portefeuille génère des intérêts grâce à une allocation dynamique. '
                    'L’objectif est de diversifier les sources de rendement tout en équilibrant performance et risque. '
                    'Un comité de gestion ajuste les expositions au sein des thématiques d’investissement. '
                    'Votre exposition est ainsi ajustée au sein des thématiques d\'investissement stratégiques ci-dessous :',
                slices: const [
                  PortfolioAllocationSlice(label: 'Energy', percentage: 52.51),
                  PortfolioAllocationSlice(label: 'Real estate', percentage: 33.83),
                  PortfolioAllocationSlice(label: 'Crypto', percentage: 12.46),
                  PortfolioAllocationSlice(label: 'Stablecoins', percentage: 1.19),
                ],
              ),
            ),
          ),
          SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) => ListTile(
                title: Text('Placeholder item ${index + 1}'),
                subtitle: const Text('Wallet content'),
              ),
              childCount: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _SheetContent extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              CircleAvatar(
                backgroundColor: Colors.blue.shade700,
                child: const Text('J', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Chat with Julia', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                    Text(
                      'Today, 3:57 AM · In progress',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {},
                  child: const Text('End'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton(
                  onPressed: () {},
                  style: FilledButton.styleFrom(backgroundColor: Colors.indigo),
                  child: const Text('Continue'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
