import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../assets/crypto_instrument_svgs.dart';
import '../atoms/app_colors.dart';
import 'list_card.dart';

/// Avatar crypto-monnaie.
///
/// Figma spec :
///   - **Par défaut : cercle** — Circle 40px (large), 36 (medium), Small Circle 24px (small / overlap).
///   - Variante : carré arrondi [CryptoAvatarShape.rounded] (rayons 8–12 px selon taille).
///   - Couleur de fond : [AppColors.cryptoAssetBrand] ou fallback gris 15%
///   - Affichage : **SVG packagé** ([cryptoInstrumentSvgAssetPath], export Figma) en priorité ;
///     si pas de SVG ou erreur de rendu, **logo réseau** [logoUrl] ; sinon icône.
class CryptoAvatar extends StatelessWidget {
  const CryptoAvatar({
    super.key,
    required this.ticker,
    this.logoUrl,
    this.fallbackIcon = Icons.token_outlined,
    this.size = CryptoAvatarSize.medium,
    this.shape = CryptoAvatarShape.circle,
  });

  final String ticker;
  final String? logoUrl;
  final IconData fallbackIcon;
  final CryptoAvatarSize size;
  final CryptoAvatarShape shape;

  double get _size => switch (size) {
        CryptoAvatarSize.small => 24,
        CryptoAvatarSize.medium => 36,
        CryptoAvatarSize.large => 40,
      };

  double get _iconSize => switch (size) {
        CryptoAvatarSize.small => 14,
        CryptoAvatarSize.medium => 20,
        CryptoAvatarSize.large => 22,
      };

  double get _borderRadius => switch (shape) {
        CryptoAvatarShape.rounded => switch (size) {
            CryptoAvatarSize.small => 8,
            CryptoAvatarSize.medium => 10,
            CryptoAvatarSize.large => 12,
          },
        CryptoAvatarShape.circle => _size / 2,
      };

  Color get _bgColor {
    return AppColors.cryptoAssetBrand[ticker.toUpperCase()] ??
        AppColors.textPrimary.withValues(alpha: 0.15);
  }

  Widget _buildBundledSvg(String svgPath, {required bool hasUrl}) {
    final s = _size;
    return ColoredBox(
      color: _bgColor,
      child: SvgPicture.asset(
        svgPath,
        width: s,
        height: s,
        fit: BoxFit.cover,
        allowDrawingOutsideViewBox: true,
        errorBuilder: (_, __, ___) {
          if (hasUrl) {
            return Image.network(
              logoUrl!,
              width: s,
              height: s,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => _buildFallbackIcon(),
            );
          }
          return _buildFallbackIcon();
        },
      ),
    );
  }

  Widget _buildFallbackIcon() {
    final s = _size;
    final iconSize = _iconSize;
    if (shape == CryptoAvatarShape.circle) {
      return Container(
        width: s,
        height: s,
        decoration: BoxDecoration(
          color: _bgColor,
          shape: BoxShape.circle,
        ),
        child: Center(
          child: Icon(fallbackIcon, size: iconSize, color: Colors.white),
        ),
      );
    }
    return IconContainer(
      size: size == CryptoAvatarSize.small
          ? IconContainerSize.sm
          : IconContainerSize.md,
      borderRadius: _borderRadius,
      backgroundColor: _bgColor,
      child: Icon(fallbackIcon, size: iconSize, color: Colors.white),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = _size;
    final r = _borderRadius;
    final svgPath = cryptoInstrumentSvgAssetPath(ticker);
    final hasUrl = logoUrl != null && logoUrl!.isNotEmpty;

    Widget networkOrBundled() {
      if (svgPath != null) {
        return _buildBundledSvg(svgPath, hasUrl: hasUrl);
      }
      if (hasUrl) {
        return Image.network(
          logoUrl!,
          width: s,
          height: s,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _buildFallbackIcon(),
        );
      }
      return _buildFallbackIcon();
    }

    final content = networkOrBundled();
    return SizedBox(
      width: s,
      height: s,
      child: shape == CryptoAvatarShape.circle
          ? ClipOval(child: content)
          : ClipRRect(
              borderRadius: BorderRadius.circular(r),
              child: content,
            ),
    );
  }
}

enum CryptoAvatarSize { small, medium, large }

enum CryptoAvatarShape { rounded, circle }
