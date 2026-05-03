import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/kalai_icons.dart';
import 'app_radio_button.dart';
import 'kalai_icon.dart';

/// Padding entre le bord du module blanc et les tuiles — minimal (2px) pour limiter l’anneau blanc.
const double kSelectionModuleInnerPadding = 2;

/// Espace vertical entre deux lignes dans le module (même valeur pour radio et checkbox).
const double kSelectionRowSpacing = 2;

/// Rayon des tuiles sélectionnées — identique à [AppSheetListItem] (`AppRadius.lg`).
const double kSelectionTileRadius = AppRadius.lg;

/// Fond état sélectionné — même token que [AppSheetListItem].
const Color kSelectionInsetSelectedBg = Color(0xFFEFEEFE);

/// Taille du slot leading (radio / checkbox) — identique pour [FormRadioRow] et [FormCheckboxRow].
const double kFormSelectionLeadingExtent = 24;

/// Tuile de sélection réutilisable : fond arrondi **inset** uniquement pour l’état
/// **selected** (persistant).
///
/// **Pas d’[AnimatedContainer]** : le lerp transparent ↔ lavande sur ~150 ms produit
/// des teintes intermédiaires **grises** (effet « pressed » fantôme). Pas d’[InkWell]
/// / [Material] autour de la ligne pour éviter toute encre Material.
///
/// Utilisé par [FormRadioRow] et [FormCheckboxRow] (onboarding / financial profile).
class SelectableInsetTile extends StatelessWidget {
  const SelectableInsetTile({
    super.key,
    required this.selected,
    required this.leading,
    required this.label,
    required this.onTap,
  });

  final bool selected;
  final Widget leading;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(kSelectionTileRadius);
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: selected ? kSelectionInsetSelectedBg : Colors.transparent,
          borderRadius: radius,
          // Même logique que [AppSheetListItem] : bordure 2px blanche si sélectionné,
          // transparente sinon — garde la même boîte quelle que soit la sélection.
          border: Border.all(
            color: selected ? Colors.white : Colors.transparent,
            width: 2,
          ),
        ),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            leading,
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(
                label,
                // Thème Inter déjà chargé par AppTheme — évite une nouvelle résolution
                // GoogleFonts au premier tap (latence typique du premier glyphe w600×16).
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.3,
                      height: 1.25,
                      color: AppColors.textPrimary,
                    ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Case à cocher **purement graphique** (pas de [Checkbox] Material) — même look que
/// l’ancien widget, sans ripple / overlay / pressed au changement d’état.
class _DsCheckboxLeadingVisual extends StatelessWidget {
  const _DsCheckboxLeadingVisual({required this.checked});

  final bool checked;

  static const _borderColor = Color(0xFFD1D1D6);
  static const _size = 20.0;
  static const _radius = 6.0;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: _size,
      height: _size,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: checked ? AppColors.indigo : Colors.transparent,
          borderRadius: BorderRadius.circular(_radius),
          border: Border.all(
            color: checked ? AppColors.indigo : _borderColor,
            width: 1.5,
          ),
        ),
        child: checked
            ? const Center(
                child: KalaiIcon(KalaiIcons.check, size: 14, color: Colors.white),
              )
            : null,
      ),
    );
  }
}

/// Ligne single-select : radio DS à gauche, tuile inset si sélection / press.
class FormRadioRow extends StatelessWidget {
  const FormRadioRow({
    super.key,
    required this.label,
    required this.selected,
    required this.onSelect,
  });

  final String label;
  final bool selected;
  final VoidCallback onSelect;

  @override
  Widget build(BuildContext context) {
    return SelectableInsetTile(
      selected: selected,
      label: label,
      onTap: onSelect,
      leading: IgnorePointer(
        child: SizedBox(
          width: kFormSelectionLeadingExtent,
          height: kFormSelectionLeadingExtent,
          child: Center(
            child: AppRadioButton(
              checked: selected,
              onChanged: (_) {},
              label: null,
            ),
          ),
        ),
      ),
    );
  }
}

/// Ligne multi-select : checkbox à gauche, tuile inset si coché / press.
class FormCheckboxRow extends StatelessWidget {
  const FormCheckboxRow({
    super.key,
    required this.label,
    required this.checked,
    required this.onToggle,
  });

  final String label;
  final bool checked;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return SelectableInsetTile(
      selected: checked,
      label: label,
      onTap: onToggle,
      leading: IgnorePointer(
        child: SizedBox(
          width: kFormSelectionLeadingExtent,
          height: kFormSelectionLeadingExtent,
          child: Center(
            child: _DsCheckboxLeadingVisual(checked: checked),
          ),
        ),
      ),
    );
  }
}
