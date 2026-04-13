import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import 'nav_item.dart';

/// Constantes de la barre principale (pill 4 items).
class _BarConstants {
  _BarConstants._();

  static const double height = 56;
  static const double horizontalMargin = 16;
  /// Marge au-dessus de la safe area : 8pt pour que la barre ne soit pas collée au bord.
  static const double bottomMargin = 8;
  /// 100 % arrondi = pill (borderRadius = moitié de la hauteur).
  static const double borderRadius = height / 2;
  /// Base blanche sous le blur.
  static const double whiteBaseOpacity = 0.72;
  static const double blurOverlayOpacity = 0.28;
  static const double blurSigmaX = 24;
  static const double blurSigmaY = 24;
  static const double paddingHorizontal = 16;
  static const double paddingVertical = 4;
  static const double outerBorderOpacity = 0.58;
  static const double innerBorderOpacity = 0.14;
  static const double glossOpacity = 0.30;
}

/// Constantes du bouton Search (disque blur).
class _SearchConstants {
  _SearchConstants._();

  /// Même hauteur que la barre (pill) pour alignement visuel.
  static const double size = _BarConstants.height;
  static const double whiteBaseOpacity = 0.72;
  static const double blurOverlayOpacity = 0.28;
  static const double blurSigmaX = 20;
  static const double blurSigmaY = 20;
  static const double iconSize = 24;
  static const double gapFromBar = 10;
  static const double outerBorderOpacity = 0.58;
  static const double innerBorderOpacity = 0.14;
  static const double glossOpacity = 0.30;
}

/// Barre de navigation flottante : pill (4 items) + Search en disque séparé.
/// Blur sur base blanche ; barre 100 % arrondie ; Search sans texte, dans un disque blur.
class AppBottomNav extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const AppBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  static const List<_NavItemData> _mainItems = [
    _NavItemData(label: 'Accueil', icon: Icons.home_rounded),
    _NavItemData(label: 'Investir', icon: Icons.trending_up_rounded),
    _NavItemData(label: 'Markets', icon: Icons.currency_bitcoin),
    _NavItemData(label: 'Design', icon: Icons.radio_rounded),
  ];

  static const int _searchIndex = 4;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;
    final bottom = _BarConstants.bottomMargin + bottomInset;

    return Positioned(
      left: _BarConstants.horizontalMargin,
      right: _BarConstants.horizontalMargin,
      bottom: bottom,
      height: _BarConstants.height,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Barre principale : 4 items, pill 100 % rounded, blur sur base blanche
          Expanded(
            child: _buildMainBar(),
          ),
          const SizedBox(width: _SearchConstants.gapFromBar),
          // Search : icône seule dans un disque blur blanc
          _buildSearchButton(),
        ],
      ),
    );
  }

  Widget _buildMainBar() {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(_BarConstants.borderRadius),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.22),
            blurRadius: 12,
            offset: const Offset(0, 5),
          ),
          BoxShadow(
            color: Colors.white.withValues(alpha: 0.12),
            blurRadius: 2,
            offset: const Offset(0, -1),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(_BarConstants.borderRadius),
        child: Stack(
          fit: StackFit.expand,
          children: [
            BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: _BarConstants.blurSigmaX,
                sigmaY: _BarConstants.blurSigmaY,
              ),
              child: Container(
                color: AppColors.navBarBackground
                    .withValues(alpha: _BarConstants.whiteBaseOpacity),
              ),
            ),
            DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(_BarConstants.borderRadius),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Colors.white.withValues(alpha: _BarConstants.blurOverlayOpacity + 0.08),
                    Colors.white.withValues(alpha: _BarConstants.blurOverlayOpacity - 0.06),
                  ],
                ),
                border: Border.all(
                  color: Colors.white.withValues(alpha: _BarConstants.outerBorderOpacity),
                  width: 1.4,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(1.6),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(_BarConstants.borderRadius - 1.6),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: _BarConstants.innerBorderOpacity),
                    width: 1,
                  ),
                ),
              ),
            ),
            Align(
              alignment: Alignment.topCenter,
              child: Container(
                height: _BarConstants.height * 0.45,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(_BarConstants.borderRadius),
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.white.withValues(alpha: _BarConstants.glossOpacity),
                      Colors.white.withValues(alpha: 0),
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: _BarConstants.paddingHorizontal,
                vertical: _BarConstants.paddingVertical,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: List.generate(_mainItems.length, (index) {
                  final item = _mainItems[index];
                  return Expanded(
                    child: NavItem(
                      icon: item.icon,
                      label: item.label,
                      selected: index == currentIndex,
                      onTap: () => onTap(index),
                    ),
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchButton() {
    final selected = currentIndex == _searchIndex;
    final color = selected ? AppColors.navSelected : AppColors.navUnselected;

    return SizedBox(
      width: _SearchConstants.size,
      height: _SearchConstants.size,
      child: DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.22),
              blurRadius: 12,
              offset: const Offset(0, 5),
            ),
            BoxShadow(
              color: Colors.white.withValues(alpha: 0.12),
              blurRadius: 2,
              offset: const Offset(0, -1),
            ),
          ],
        ),
        child: ClipOval(
          child: Stack(
            fit: StackFit.expand,
            children: [
              BackdropFilter(
                filter: ImageFilter.blur(
                  sigmaX: _SearchConstants.blurSigmaX,
                  sigmaY: _SearchConstants.blurSigmaY,
                ),
                child: Container(
                  color: AppColors.navBarBackground
                      .withValues(alpha: _SearchConstants.whiteBaseOpacity),
                ),
              ),
              DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.white.withValues(alpha: _SearchConstants.blurOverlayOpacity + 0.08),
                      Colors.white.withValues(alpha: _SearchConstants.blurOverlayOpacity - 0.06),
                    ],
                  ),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: _SearchConstants.outerBorderOpacity),
                    width: 1.4,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(1.6),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white.withValues(alpha: _SearchConstants.innerBorderOpacity),
                      width: 1,
                    ),
                  ),
                ),
              ),
              Align(
                alignment: Alignment.topCenter,
                child: Container(
                  height: _SearchConstants.size * 0.45,
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.white.withValues(alpha: _SearchConstants.glossOpacity),
                        Colors.white.withValues(alpha: 0),
                      ],
                    ),
                  ),
                ),
              ),
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => onTap(_searchIndex),
                  customBorder: const CircleBorder(),
                  splashColor: Colors.white.withValues(alpha: 0.18),
                  highlightColor: Colors.white.withValues(alpha: 0.08),
                  child: Center(
                    child: Icon(
                      Icons.search_rounded,
                      size: _SearchConstants.iconSize,
                      color: color,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItemData {
  final String label;
  final IconData icon;
  const _NavItemData({required this.label, required this.icon});
}
