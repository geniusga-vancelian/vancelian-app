import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'crypto_avatar.dart';

/// Bandeau d’avatars crypto superposés (même gabarit que le header détail bundle :
/// cercles 24 px, chevauchement 14 px, anneau blanc, [CryptoAvatar] en priorité).
///
/// [orderedSymbols] : ordre d’affichage (gauche → droite), déjà trié par l’appelant si besoin.
/// Si [maxDisplayed] est non null et [orderedSymbols.length] est supérieur, les symboles
/// au‑delà sont comptés dans le badge **+N** (même principe que l’ancien [CryptoAvatarGroup]).
class BundleTickerAvatarRow extends StatelessWidget {
  const BundleTickerAvatarRow({
    super.key,
    required this.orderedSymbols,
    this.maxDisplayed,
  });

  final List<String> orderedSymbols;
  final int? maxDisplayed;

  static const double _diameter = 24;
  static const double _overlap = 14;
  static const double _step = _diameter - _overlap;

  @override
  Widget build(BuildContext context) {
    final raw = orderedSymbols
        .map((s) => s.trim().toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
    if (raw.isEmpty) return const SizedBox.shrink();

    final total = raw.length;
    final cap = maxDisplayed == null ? total : math.min(maxDisplayed!, total);
    final shown = raw.take(cap).toList();
    final remainder = total - cap;

    final stackItems = shown.length + (remainder > 0 ? 1 : 0);
    final width = stackItems * _diameter - (stackItems - 1) * _overlap;

    return SizedBox(
      width: width,
      height: _diameter,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          for (var i = 0; i < shown.length; i++)
            Positioned(
              left: i * _step,
              child: _BundleAvatarRing(ticker: shown[i]),
            ),
          if (remainder > 0)
            Positioned(
              left: shown.length * _step,
              child: _BundlePlusBadge(count: remainder),
            ),
        ],
      ),
    );
  }
}

class _BundleAvatarRing extends StatelessWidget {
  const _BundleAvatarRing({required this.ticker});

  final String ticker;

  @override
  Widget build(BuildContext context) {
    final t = ticker.trim().toUpperCase();

    return SizedBox(
      width: BundleTickerAvatarRow._diameter,
      height: BundleTickerAvatarRow._diameter,
      child: DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 1),
        ),
        child: Padding(
          padding: const EdgeInsets.all(1),
          child: ClipOval(
            child: FittedBox(
              fit: BoxFit.cover,
              alignment: Alignment.center,
              child: SizedBox(
                width: BundleTickerAvatarRow._diameter,
                height: BundleTickerAvatarRow._diameter,
                child: CryptoAvatar(
                  ticker: t,
                  size: CryptoAvatarSize.small,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BundlePlusBadge extends StatelessWidget {
  const _BundlePlusBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    const size = BundleTickerAvatarRow._diameter;
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(
        color: AppColors.pageBackground,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        '+$count',
        style: AppTypography.labelEmphasized.copyWith(
          fontSize: size * 0.42,
          height: 1,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }
}
