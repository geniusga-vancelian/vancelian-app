import 'package:flutter/material.dart';

/// Reusable circular avatar with icon or network image for transaction / list tiles (Revolut-style).
/// Use as the [leading] widget in [TransactionTile].
/// If [imageUrl] is set, shows the image; otherwise shows [icon] on [backgroundColor].
///
/// Example:
/// ```dart
/// TransactionAvatar(
///   icon: Icons.savings,
///   backgroundColor: Colors.orange,
/// )
/// TransactionAvatar(icon: Icons.currency_bitcoin, imageUrl: 'https://.../btc.png')
/// ```
class TransactionAvatar extends StatelessWidget {
  const TransactionAvatar({
    super.key,
    required this.icon,
    this.backgroundColor = Colors.transparent,
    this.iconColor = Colors.white,
    this.size = 44,
    this.showBackground = true,
    this.imageUrl,
  })  : assert(size > 0, 'size must be positive'),
        _iconSize = size * 0.5;

  final IconData icon;
  final Color backgroundColor;
  final Color iconColor;
  final double size;
  final bool showBackground;
  /// When set, display this image instead of the icon (e.g. crypto logo).
  final String? imageUrl;
  final double _iconSize;

  /// Compact size for dense tiles (40px).
  static const double sizeDense = 40;

  /// Icon size when using [sizeDense] (20px).
  static const double iconSizeDense = 20;

  @override
  Widget build(BuildContext context) {
    final hasImage = imageUrl != null && imageUrl!.trim().isNotEmpty;
    if (hasImage) {
      return SizedBox(
        width: size,
        height: size,
        child: CircleAvatar(
          radius: size / 2,
          backgroundImage: NetworkImage(imageUrl!),
          onBackgroundImageError: (_, __) {},
        ),
      );
    }

    final iconWidget = Icon(
      this.icon,
      size: _iconSize,
      color: iconColor,
    );

    if (!showBackground) {
      return SizedBox(
        width: size,
        height: size,
        child: Center(child: iconWidget),
      );
    }

    return SizedBox(
      width: size,
      height: size,
      child: Container(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: backgroundColor,
        ),
        child: iconWidget,
      ),
    );
  }
}
