import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../assets/crypto_instrument_svgs.dart';
import '../atoms/app_colors.dart';

/// Deux avatars crypto **circulaires** superposés (swap / échange), alignés Figma / [CryptoAvatar] petit cercle.
///
/// Layout : première pièce en haut-gauche, seconde en bas-droite avec décalage diagonal.
///   - [coinSize] : diamètre de chaque cercle (défaut 24, comme [CryptoAvatarSize.small]).
///   - [xOffset] : décalage horizontal de la seconde pièce (défaut 14).
///   - [yOffset] : décalage vertical de la seconde pièce (défaut 10).
///   - Contenu dimensionné à (xOffset + coinSize) × (yOffset + coinSize).
///
/// Logos : **SVG packagé** en priorité, sinon URL réseau, sinon initiale.
class TransactionSwapAvatar extends StatelessWidget {
  const TransactionSwapAvatar({
    super.key,
    required this.fromTicker,
    required this.toTicker,
    this.fromLogoUrl,
    this.toLogoUrl,
    this.fromIcon,
    this.toIcon,
    this.coinSize = 24,
    this.xOffset = 14,
    this.yOffset = 10,
  });

  final String fromTicker;
  final String toTicker;
  final String? fromLogoUrl;
  final String? toLogoUrl;
  final IconData? fromIcon;
  final IconData? toIcon;
  final double coinSize;
  final double xOffset;
  final double yOffset;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: xOffset + coinSize,
      height: yOffset + coinSize,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: _buildCoin(
              ticker: fromTicker,
              logoUrl: fromLogoUrl,
              icon: fromIcon,
            ),
          ),
          Positioned(
            left: xOffset,
            top: yOffset,
            child: _buildCoin(
              ticker: toTicker,
              logoUrl: toLogoUrl,
              icon: toIcon,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCoin({
    required String ticker,
    String? logoUrl,
    IconData? icon,
  }) {
    final bgColor = AppColors.cryptoAssetBrand[ticker.toUpperCase()] ??
        AppColors.textPrimary.withValues(alpha: 0.15);
    final svgPath = cryptoInstrumentSvgAssetPath(ticker);

    Widget fallbackLetter() => Center(child: _buildFallback(ticker, icon));

    Widget? networkOrSvg() {
      final url = logoUrl;
      final hasUrl = url != null && url.isNotEmpty;

      if (svgPath != null) {
        return SvgPicture.asset(
          svgPath,
          width: coinSize,
          height: coinSize,
          fit: BoxFit.cover,
          allowDrawingOutsideViewBox: true,
          errorBuilder: (_, __, ___) {
            if (hasUrl) {
              return Image.network(
                url,
                width: coinSize,
                height: coinSize,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => fallbackLetter(),
              );
            }
            return fallbackLetter();
          },
        );
      }
      if (hasUrl) {
        return Image.network(
          url,
          width: coinSize,
          height: coinSize,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => fallbackLetter(),
        );
      }
      return null;
    }

    final inner = networkOrSvg();
    return Container(
      width: coinSize,
      height: coinSize,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.white, width: 1.5),
      ),
      clipBehavior: Clip.antiAlias,
      child: ClipOval(
        child: ColoredBox(
          color: bgColor,
          child: inner ?? fallbackLetter(),
        ),
      ),
    );
  }

  Widget _buildFallback(String ticker, IconData? icon) {
    final iconSize = coinSize * 0.4;
    if (icon != null) {
      return Icon(icon, size: iconSize, color: Colors.white);
    }
    final letter = ticker.isNotEmpty ? ticker[0].toUpperCase() : '?';
    return Text(
      letter,
      style: TextStyle(
        fontSize: coinSize * 0.35,
        fontWeight: FontWeight.w700,
        color: Colors.white,
      ),
    );
  }
}
