import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'app_small_button.dart';
import 'ds_address_list_item.dart';

/// Entrée pour [DsAddressSelector].
class DsAddressEntry {
  const DsAddressEntry({
    required this.id,
    required this.title,
    required this.subtitle,
  });

  final String id;
  final String title;
  final String subtitle;
}

/// Liste d’adresses + lien « pas dans la liste » + CTA saisie manuelle (Figma ZIP 5).
class DsAddressSelector extends StatelessWidget {
  const DsAddressSelector({
    super.key,
    required this.addresses,
    this.onAddressSelect,
    this.onManualInput,
    this.onAddressNotHere,
    this.notHereLabel = 'My address is not here',
    this.manualInputLabel = 'Manual input',
  });

  final List<DsAddressEntry> addresses;
  final void Function(String id)? onAddressSelect;
  final VoidCallback? onManualInput;
  final VoidCallback? onAddressNotHere;

  /// Texte du lien (Figma : « My address is not here »).
  final String notHereLabel;

  /// Libellé du bouton pill (Figma : « Manual input »).
  final String manualInputLabel;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.iosChromeBackground,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        foregroundColor: AppColors.indigo,
                      ),
                      onPressed: onAddressNotHere,
                      child: Text(
                        notHereLabel,
                        style: AppTypography.itemPrimary
                            .copyWith(color: AppColors.indigo),
                        textAlign: TextAlign.start,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                AppSmallButton(
                  label: manualInputLabel,
                  onPressed: onManualInput,
                ),
              ],
            ),
            for (final a in addresses) ...[
              const SizedBox(height: AppSpacing.xxl),
              DsAddressListItem(
                title: a.title,
                subtitle: a.subtitle,
                onTap: onAddressSelect != null
                    ? () => onAddressSelect!(a.id)
                    : null,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
