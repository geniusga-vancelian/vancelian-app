import 'package:flutter/material.dart';

import '../../../../design_system/components/bundle_ticker_avatar_row.dart';
import '../../data/product_catalog_api.dart';

/// Avatars des actifs du bundle (header détail produit), empilés de gauche à droite.
///
/// Tri par [ProductAllocationSummary.targetWeight] **croissant** : plus faible poids à gauche
/// (arrière-plan), plus forte allocation à droite au premier plan — aligné maquettes bundle.
/// Rendu : [BundleTickerAvatarRow] (cercles 24 px, chevauchement 14 px, [CryptoAvatar]).
class BundleAllocationAvatarStack extends StatelessWidget {
  const BundleAllocationAvatarStack({
    super.key,
    required this.allocations,
  });

  final List<ProductAllocationSummary> allocations;

  @override
  Widget build(BuildContext context) {
    if (allocations.isEmpty) return const SizedBox.shrink();

    final sorted = List<ProductAllocationSummary>.from(allocations)
      ..sort((a, b) => a.targetWeight.compareTo(b.targetWeight));

    final ordered = sorted
        .map((a) => a.assetSymbol.trim().toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();

    return BundleTickerAvatarRow(
      orderedSymbols: ordered,
      maxDisplayed: null,
    );
  }
}
