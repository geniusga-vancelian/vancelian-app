import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'app_small_button.dart';

/// Data for a single avatar in [CryptoAvatarGroup].
class CryptoAvatarData {
  const CryptoAvatarData({required this.ticker, this.backgroundColor});

  final String ticker;
  final Color? backgroundColor;

  Color get resolvedColor =>
      backgroundColor ?? AppColors.cryptoBrandColor(ticker);
}

/// Overlapping row of small crypto avatar circles with an optional "+N" pill.
///
/// Figma: 24×24 circles, 6px overlap, remaining count in gray circle.
class CryptoAvatarGroup extends StatelessWidget {
  const CryptoAvatarGroup({
    super.key,
    required this.avatars,
    this.remainingCount = 0,
    this.size = 24,
    this.overlap = 6,
  });

  final List<CryptoAvatarData> avatars;
  final int remainingCount;
  final double size;
  final double overlap;

  @override
  Widget build(BuildContext context) {
    final total = avatars.length + (remainingCount > 0 ? 1 : 0);
    final width = total * size - (total - 1) * overlap;

    return SizedBox(
      width: width,
      height: size,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          for (int i = 0; i < avatars.length; i++)
            Positioned(
              left: i * (size - overlap),
              child: _AvatarCircle(
                size: size,
                color: avatars[i].resolvedColor,
                label: avatars[i].ticker.substring(0, 1).toUpperCase(),
              ),
            ),
          if (remainingCount > 0)
            Positioned(
              left: avatars.length * (size - overlap),
              child: Container(
                width: size,
                height: size,
                decoration: const BoxDecoration(
                  color: AppColors.pageBackground,
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Text(
                  '+$remainingCount',
                  style: AppTypography.labelEmphasized.copyWith(
                    fontSize: size * 0.42,
                    height: 1,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _AvatarCircle extends StatelessWidget {
  const _AvatarCircle({
    required this.size,
    required this.color,
    required this.label,
  });

  final double size;
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        label,
        style: TextStyle(
          color: Colors.white,
          fontSize: size * 0.42,
          fontWeight: FontWeight.w700,
          height: 1,
        ),
      ),
    );
  }
}

/// Colored percentage label (green positive, red negative).
///
/// Figma: 12px bold, #34c759 / #ff3b30.
class PercentageLabel extends StatelessWidget {
  const PercentageLabel({
    super.key,
    required this.value,
    this.positive = true,
  });

  final String value;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    return Text(
      value,
      style: AppTypography.labelEmphasized.copyWith(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        height: 16 / 12,
        color: positive ? AppColors.green : AppColors.red,
      ),
    );
  }
}

/// Crypto basket/portfolio card.
///
/// Figma: white card, shadow 0 0 20 -10 rgba(0,0,0,0.12), radius 16,
/// padding 16. Left: avatar group + name + percentage. Right: invest button.
class BasketCard extends StatelessWidget {
  const BasketCard({
    super.key,
    required this.name,
    required this.percentage,
    this.percentagePositive = true,
    required this.avatars,
    this.remainingAvatarCount = 0,
    this.onInvest,
    this.onTap,
  });

  final String name;
  final String percentage;
  final bool percentagePositive;
  final List<CryptoAvatarData> avatars;
  final int remainingAvatarCount;
  final VoidCallback? onInvest;
  final VoidCallback? onTap;

  static const double _radius = 16;
  static const double _padding = 16;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(_padding),
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(_radius),
          boxShadow: const [
            BoxShadow(
              color: Color(0x1F000000),
              blurRadius: 20,
              spreadRadius: -10,
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  CryptoAvatarGroup(
                    avatars: avatars,
                    remainingCount: remainingAvatarCount,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    name,
                    style: AppTypography.bodyEmphasized.copyWith(
                      fontSize: 15,
                      height: 20 / 15,
                      letterSpacing: -0.23,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  PercentageLabel(
                    value: percentage,
                    positive: percentagePositive,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            AppSmallButton(label: 'Investir', onPressed: onInvest),
          ],
        ),
      ),
    );
  }
}
