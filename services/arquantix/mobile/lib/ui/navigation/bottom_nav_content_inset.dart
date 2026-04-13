import 'package:flutter/widgets.dart';

class BottomNavContentInset {
  BottomNavContentInset._();

  static const double navBarHeight = 56;
  static const double navBarBottomMargin = 8;
  static const double safetySpacing = 12;

  static double level1(BuildContext context) {
    return MediaQuery.paddingOf(context).bottom +
        navBarHeight +
        navBarBottomMargin +
        safetySpacing;
  }
}
