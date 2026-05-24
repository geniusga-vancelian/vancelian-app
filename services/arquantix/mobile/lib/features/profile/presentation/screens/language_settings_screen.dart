import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../core/locale_preference.dart';
import '../../../../design_system/design_system.dart';

/// Sélection de la langue d’affichage de l’app.
///
/// - Liste les locales activées côté admin (`/api/site/i18n-policy`,
///   alimenté par `app_settings.supportedLocales` — page Translation Settings
///   du CMS).
/// - La locale active est persistée par [LocalePreference] et utilisée par tous
///   les services API (`?locale=…`) ainsi que par `MaterialApp.locale`.
/// - Si l’admin n’expose qu’une seule langue, on affiche un message d’info.
class LanguageSettingsScreen extends StatefulWidget {
  const LanguageSettingsScreen({super.key});

  @override
  State<LanguageSettingsScreen> createState() => _LanguageSettingsScreenState();
}

class _LanguageSettingsScreenState extends State<LanguageSettingsScreen> {
  final LocalePreference _pref = LocalePreference.instance;
  // Refresh `/api/site/i18n-policy` au mount, puis fire-and-forget : on évite
  // tout `setState(_refreshing = …)` qui retriggerait le shell de la page et
  // ferait clignoter la nav-bar.
  @override
  void initState() {
    super.initState();
    unawaited(_pref.loadFromServer());
  }

  void _select(String code) {
    if (code == _pref.locale) return;
    // `setLocale` notifie l'UI synchronement (avant le `await` de l'écriture
    // disque) → la coche bascule immédiatement, sans flag `_saving` ni spinner.
    unawaited(_pref.setLocale(code));
  }

  @override
  Widget build(BuildContext context) {
    // Volontairement **hors** ListenableBuilder : la nav-bar et la structure
    // de la page ne dépendent pas de la locale, on évite donc qu'elles soient
    // reconstruites à chaque changement (cause du clignotement perçu).
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Langue',
      content: [
        _HeaderCard(pref: _pref),
        const SizedBox(height: AppSpacing.xxl),
        const AppSectionTitle('Choisir la langue'),
        const SizedBox(height: AppSpacing.md),
        _LanguageList(pref: _pref, onSelect: _select),
        const SizedBox(height: AppSpacing.xxl),
      ],
    );
  }
}

/// Carte d'introduction (résumé des locales activées). Reconstruite uniquement
/// quand `LocalePreference.supportedLocales` change.
class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.pref});

  final LocalePreference pref;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: pref,
      builder: (context, _) {
        final summary = pref.supportedLocales.isEmpty
            ? 'Mise à jour des langues disponibles…'
            : 'Langues activées dans l’admin du projet : '
                '${pref.supportedLocales.map(_languageLabel).join(', ')}.';
        return SettingsCard(
          children: [
            Text(
              summary,
              style: AppTypography.itemSupporting
                  .copyWith(color: const Color(0xFF8E8E93)),
            ),
          ],
        );
      },
    );
  }
}

/// Liste cliquable des locales. Reconstruite uniquement à la sélection ou à un
/// changement de `supportedLocales`. La transition de la coche est animée
/// (`AnimatedSwitcher`) → fade in/out plutôt qu'apparition brutale.
class _LanguageList extends StatelessWidget {
  const _LanguageList({required this.pref, required this.onSelect});

  final LocalePreference pref;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: pref,
      builder: (context, _) {
        final locales = pref.supportedLocales;
        if (locales.isEmpty) {
          return SettingsCard(
            children: [
              Text(
                'Aucune langue n’est activée côté admin pour ce projet.',
                style: AppTypography.itemSupporting
                    .copyWith(color: const Color(0xFF8E8E93)),
              ),
            ],
          );
        }
        return SettingsCard(
          children: [
            for (final code in locales)
              _LanguageRow(
                key: ValueKey('lang.$code'),
                code: code,
                isDefault: code == pref.defaultLocale,
                isSelected: code == pref.locale,
                onTap: () => onSelect(code),
              ),
          ],
        );
      },
    );
  }
}

class _LanguageRow extends StatelessWidget {
  const _LanguageRow({
    super.key,
    required this.code,
    required this.isDefault,
    required this.isSelected,
    required this.onTap,
  });

  final String code;
  final bool isDefault;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final subtitleParts = <String>[code.toUpperCase()];
    if (isDefault) subtitleParts.add('langue canonique');
    return SettingsListItem(
      leading: _LanguageBadge(code: code),
      title: _languageLabel(code),
      subtitle: subtitleParts.join(' • '),
      // Trailing **toujours présent** (taille fixe 22x22) pour éviter tout
      // recalcul de hauteur de la ligne quand la coche apparaît / disparaît.
      // L'opacité passe en cross-fade via AnimatedSwitcher → pas de flash.
      trailing: SizedBox(
        width: 22,
        height: 22,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 160),
          transitionBuilder: (child, anim) =>
              FadeTransition(opacity: anim, child: child),
          child: isSelected
              ? const Icon(
                  Icons.check_rounded,
                  key: ValueKey('on'),
                  color: AppColors.textPrimary,
                  size: 22,
                )
              : const SizedBox.shrink(key: ValueKey('off')),
        ),
      ),
      onTap: onTap,
    );
  }
}

class _LanguageBadge extends StatelessWidget {
  const _LanguageBadge({required this.code});

  final String code;

  @override
  Widget build(BuildContext context) {
    return IconContainer(
      size: IconContainerSize.md,
      borderRadius: 100,
      backgroundColor: const Color(0xFFE5E5EA),
      child: Text(
        code.toUpperCase().substring(0, code.length >= 2 ? 2 : code.length),
        style: AppTypography.itemSupporting.copyWith(
          fontWeight: FontWeight.w700,
          fontSize: 11,
          color: const Color(0xFF3C3C43),
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

/// Libellé humain pour les locales connues. Pour les autres : code en majuscules.
String _languageLabel(String code) {
  switch (code.toLowerCase()) {
    case 'en':
      return 'English';
    case 'fr':
      return 'Français';
    case 'it':
      return 'Italiano';
    case 'es':
      return 'Español';
    case 'de':
      return 'Deutsch';
    case 'pt':
      return 'Português';
    case 'nl':
      return 'Nederlands';
    default:
      return code.toUpperCase();
  }
}

