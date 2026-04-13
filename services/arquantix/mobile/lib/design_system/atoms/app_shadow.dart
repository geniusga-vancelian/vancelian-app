import 'package:flutter/material.dart';

/// Atome : ombres du design system.
class AppShadow {
  AppShadow._();

  /// Default shadow: 0px 0px 20px -10px rgba(0,0,0,0.16)
  static const BoxShadow defaultShadow = BoxShadow(
    offset: Offset.zero,
    blurRadius: 20,
    spreadRadius: -10,
    color: Color(0x29000000),
  );

  static const List<BoxShadow> defaultShadowList = [defaultShadow];
}
