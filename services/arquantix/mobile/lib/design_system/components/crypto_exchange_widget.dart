import 'package:flutter/material.dart';

import '../atoms/kalai_icons.dart';
import 'crypto_avatar.dart';
import 'kalai_icon.dart';

/// Capsule affichant deux crypto-avatars superposés avec une icône d'échange.
///
/// Figma spec :
///   - Dimensions : 123×48px
///   - Background : blanc
///   - Border radius : 50px (capsule)
///   - Avatar gauche : 40×40 à (5, 4)
///   - Avatar droit : 40×40 à (77, 4)
///   - Icône échange : 24×24 centrée
class CryptoExchangeWidget extends StatelessWidget {
  const CryptoExchangeWidget({
    super.key,
    required this.fromTicker,
    required this.toTicker,
    this.fromLogoUrl,
    this.toLogoUrl,
    this.fromIcon = Icons.token_outlined,
    this.toIcon = Icons.token_outlined,
  });

  final String fromTicker;
  final String toTicker;
  final String? fromLogoUrl;
  final String? toLogoUrl;
  final IconData fromIcon;
  final IconData toIcon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 123,
      height: 48,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(50),
      ),
      child: Stack(
        children: [
          Positioned(
            left: 5,
            top: 4,
            child: CryptoAvatar(
              ticker: fromTicker,
              logoUrl: fromLogoUrl,
              fallbackIcon: fromIcon,
              size: CryptoAvatarSize.large,
            ),
          ),
          Positioned(
            left: 77,
            top: 4,
            child: CryptoAvatar(
              ticker: toTicker,
              logoUrl: toLogoUrl,
              fallbackIcon: toIcon,
              size: CryptoAvatarSize.large,
            ),
          ),
          const Positioned(
            left: 49,
            top: 12,
            child: KalaiIcon(KalaiIcons.exchange, size: 24, color: Colors.black),
          ),
        ],
      ),
    );
  }
}
