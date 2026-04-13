import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import 'portfolio_allocation_module.dart';

/// Slice pour les modules Donuts Chart.
class DonutsChartSlice {
  const DonutsChartSlice({
    required this.label,
    required this.percentage,
    this.colorHex,
  });

  final String label;
  final double percentage;
  /// Couleur optionnelle par part (format #RRGGBB ou #AARRGGBB).
  final String? colorHex;
}

/// Version "big" :
/// donut en haut, liste des éléments en dessous (2 colonnes).
class DonutsChartBig extends StatelessWidget {
  const DonutsChartBig({
    super.key,
    required this.slices,
    this.introText,
    this.sliceColors,
  });

  final List<DonutsChartSlice> slices;
  final String? introText;
  final List<Color>? sliceColors;

  Color? _colorFromHex(String? hex) {
    if (hex == null || hex.trim().isEmpty) return null;
    var value = hex.trim().replaceAll('#', '');
    if (value.length == 6) value = 'FF$value';
    if (value.length != 8) return null;
    final colorInt = int.tryParse(value, radix: 16);
    if (colorInt == null) return null;
    return Color(colorInt);
  }

  @override
  Widget build(BuildContext context) {
    final mapped = slices
        .map(
          (s) => PortfolioAllocationSlice(
            label: s.label,
            percentage: s.percentage,
          ),
        )
        .toList();
    final resolvedColors = slices
        .map((s) =>
            _colorFromHex(s.colorHex) ??
            AppColors.cryptoAssetBrand[s.label.toUpperCase()])
        .toList();
    final hasAllColors = resolvedColors.every((c) => c != null);

    return PortfolioAllocationModule(
      slices: mapped,
      introText: introText,
      sliceColors: hasAllColors
          ? resolvedColors.whereType<Color>().toList()
          : sliceColors,
    );
  }
}

/// Version "small" :
/// donut à gauche, éléments à droite (maximum 4 éléments).
class DonutsChartSmall extends StatelessWidget {
  const DonutsChartSmall({
    super.key,
    required this.slices,
    this.sliceColors,
  });

  final List<DonutsChartSlice> slices;
  final List<Color>? sliceColors;

  Color? _colorFromHex(String? hex) {
    if (hex == null || hex.trim().isEmpty) return null;
    var value = hex.trim().replaceAll('#', '');
    if (value.length == 6) value = 'FF$value';
    if (value.length != 8) return null;
    final colorInt = int.tryParse(value, radix: 16);
    if (colorInt == null) return null;
    return Color(colorInt);
  }

  @override
  Widget build(BuildContext context) {
    final mapped = slices
        .take(4)
        .map(
          (s) => PortfolioAllocationSlice(
            label: s.label,
            percentage: s.percentage,
          ),
        )
        .toList();
    final resolvedColors = slices
        .take(4)
        .map((s) =>
            _colorFromHex(s.colorHex) ??
            AppColors.cryptoAssetBrand[s.label.toUpperCase()])
        .toList();
    final hasAllColors = resolvedColors.every((c) => c != null);

    return PortfolioAllocationCompactModule(
      slices: mapped,
      sliceColors: hasAllColors
          ? resolvedColors.whereType<Color>().toList()
          : sliceColors,
    );
  }
}
